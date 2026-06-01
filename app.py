from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import flask_monitoringdashboard as dashboard
import mlflow

import flask_monitoringdashboard.core.telemetry as fmd_telemetry


def _disable_fmd_telemetry(*args, **kwargs):
    return None


load_dotenv()

if os.getenv("FMD_DISABLE_TELEMETRY", "true").lower() in ("true", "1", "yes"):
    fmd_telemetry.post_to_back_if_telemetry_enabled = _disable_fmd_telemetry

from src.get_data import get_clean_data  # noqa: E402
from src.logging_config import setup_logging  # noqa: E402
from src.model_service import load_model  # noqa: E402
from src.monitoring import setup_mlflow  # noqa: E402
from src.utils import create_figure, get_plotly_config, prediction_from_model  # noqa: E402

logger = setup_logging()
setup_mlflow()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

model = load_model()


def _build_graph_payload() -> dict:
    data = get_clean_data()
    fig = create_figure(data)
    status_counts = {}
    if not data.empty and "traffic_label" in data.columns:
        status_counts = data["traffic_label"].value_counts().to_dict()

    return {
        "graph_json": fig.to_json(),
        "nb_points": int(len(data)),
        "status_counts": status_counts,
        "last_datetime": "" if data.empty else str(data["datetime"].max()),
    }


def _log_common_metrics(prefix: str, elapsed: float, payload: dict) -> None:
    with mlflow.start_run(run_name=prefix, nested=True, log_system_metrics=True):
        mlflow.log_metric(f"response_time_{prefix}", elapsed)
        mlflow.log_metric("nb_points_loaded", payload.get("nb_points", 0))
        for status, count in payload.get("status_counts", {}).items():
            safe_status = str(status).lower().replace(" ", "_").replace("é", "e")
            mlflow.log_metric(f"traffic_status_{safe_status}", int(count))


@app.route("/", methods=["GET"])
def index():
    start = time.perf_counter()
    try:
        payload = _build_graph_payload()
        elapsed = time.perf_counter() - start
        _log_common_metrics("index", elapsed, payload)

        return render_template(
            "index.html",
            graph_json=payload["graph_json"],
            plotly_config=get_plotly_config(),
            hours=list(range(24)),
            nb_points=payload["nb_points"],
            status_counts=payload["status_counts"],
            last_datetime=payload["last_datetime"],
        )

    except Exception as e:
        logger.error("Erreur sur la route / : %s", e, exc_info=True)
        return render_template(
            "index.html",
            graph_json="{}",
            plotly_config=get_plotly_config(),
            hours=list(range(24)),
            nb_points=0,
            status_counts={},
            last_datetime="",
            error_message="Une erreur est survenue lors du chargement des données.",
        ), 500


@app.route("/predict", methods=["POST"])
def predict():
    start = time.perf_counter()
    try:
        hour = int(request.form.get("hour", 0))

        payload = _build_graph_payload()
        cat_predict, color_info = prediction_from_model(model, hour)
        text_pred, color_pred = color_info

        elapsed = time.perf_counter() - start
        with mlflow.start_run(run_name="prediction", nested=True, log_system_metrics=True):
            mlflow.log_param("hour", hour)
            mlflow.log_metric("prediction_class", cat_predict)
            mlflow.log_metric("response_time_predict", elapsed)
            mlflow.log_metric("nb_points_loaded", payload.get("nb_points", 0))

        return render_template(
            "index.html",
            graph_json=payload["graph_json"],
            plotly_config=get_plotly_config(),
            hours=list(range(24)),
            text_pred=text_pred,
            color_pred=color_pred,
            selected_hour=hour,
            nb_points=payload["nb_points"],
            status_counts=payload["status_counts"],
            last_datetime=payload["last_datetime"],
        )

    except Exception as e:
        logger.error("Erreur sur la route /predict : %s", e, exc_info=True)
        return render_template(
            "index.html",
            graph_json="{}",
            plotly_config=get_plotly_config(),
            hours=list(range(24)),
            nb_points=0,
            status_counts={},
            last_datetime="",
            error_message="La prédiction a échoué.",
        ), 500


@app.route("/api/traffic-map", methods=["GET"])
def traffic_map_api():
    """Endpoint JSON utilisé par le frontend pour rafraîchir la carte sans recharger la page."""
    start = time.perf_counter()
    try:
        payload = _build_graph_payload()
        elapsed = time.perf_counter() - start
        _log_common_metrics("traffic_map_api", elapsed, payload)
        return jsonify(payload), 200
    except Exception as e:
        logger.error("Erreur sur la route /api/traffic-map : %s", e, exc_info=True)
        return jsonify({"error": "traffic_map_unavailable"}), 500


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


@app.route("/ping", methods=["GET"])
def ping():
    return {"ping": "ok"}, 200


# IMPORTANT : à la fin, après toutes les routes
# nosec B106 - identifiants de démonstration déplacés dans config.cfg pour l'exercice E5 local.
dashboard.config.init_from(file="config.cfg")
dashboard.bind(app)

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
