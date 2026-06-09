from __future__ import annotations
import os
import time

from dotenv import load_dotenv
from flask import Flask, render_template, request
import flask_monitoringdashboard as dashboard
import mlflow

import flask_monitoringdashboard.core.telemetry as fmd_telemetry

def _disable_fmd_telemetry(*args, **kwargs):
    return None

load_dotenv()

if os.getenv("FMD_DISABLE_TELEMETRY", "true").lower() in ("true", "1", "yes"):
    fmd_telemetry.post_to_back_if_telemetry_enabled = _disable_fmd_telemetry

from src.get_data import get_clean_data
from src.utils import create_figure, prediction_from_model
from src.logging_config import setup_logging
from src.monitoring import setup_mlflow
from src.model_service import load_model

logger = setup_logging()
setup_mlflow()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

model = load_model()


@app.route("/", methods=["GET"])
def index():
    start = time.perf_counter()
    try:
        data = get_clean_data()
        fig = create_figure(data)
        graph_json = fig.to_json()
        hours = list(range(24))

        elapsed = time.perf_counter() - start

        with mlflow.start_run(run_name="page_index", nested=True, log_system_metrics=True):
            mlflow.log_metric("response_time_index", elapsed)
            mlflow.log_metric("nb_points_loaded", len(data))

        return render_template("index.html", graph_json=graph_json, hours=hours)

    except Exception as e:
        logger.error("Erreur sur la route / : %s", e, exc_info=True)
        return render_template(
            "index.html",
            graph_json="{}",
            hours=list(range(24)),
            error_message="Une erreur est survenue lors du chargement des données."
        ), 500


@app.route("/predict", methods=["POST"])
def predict():
    start = time.perf_counter()
    try:
        hour = int(request.form.get("hour", 0))

        data = get_clean_data()
        fig = create_figure(data)
        graph_json = fig.to_json()

        cat_predict, color_info = prediction_from_model(model, hour)
        text_pred, color_pred = color_info

        elapsed = time.perf_counter() - start

        with mlflow.start_run(run_name="prediction", nested=True, log_system_metrics=True):
            mlflow.log_param("hour", hour)
            mlflow.log_metric("prediction_class", cat_predict)
            mlflow.log_metric("response_time_predict", elapsed)
            mlflow.log_metric("nb_points_loaded", len(data))

        return render_template(
            "index.html",
            graph_json=graph_json,
            hours=list(range(24)),
            text_pred=text_pred,
            color_pred=color_pred,
            selected_hour=hour
        )

    except Exception as e:
        logger.error("Erreur sur la route /predict : %s", e, exc_info=True)
        return render_template(
            "index.html",
            graph_json="{}",
            hours=list(range(24)),
            error_message="La prédiction a échoué."
        ), 500


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


@app.route("/ping", methods=["GET"])
def ping():
    return {"ping": "ok"}, 200


# IMPORTANT : à la fin, après toutes les routes
dashboard.config.init_from(file="config.cfg")
dashboard.bind(app)

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)