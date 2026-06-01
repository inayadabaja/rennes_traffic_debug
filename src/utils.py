from __future__ import annotations

import numpy as np
import plotly.express as px

COLOR_PRED_MAP = {
    0: ("Trafic fluide", "#2ecc71"),
    1: ("Trafic dense", "#f39c12"),
    2: ("Trafic saturé", "#e74c3c"),
}

TRAFFIC_COLOR_MAP = {
    "Fluide": "#2ecc71",
    "Chargé": "#f39c12",
    "Congestionné": "#e74c3c",
    "Impossible": "#7f1d1d",
    "Inconnu": "#64748b",
}


def prediction_from_model(model, hour_to_predict: int):
    """
    Prédiction déterministe à partir d'une heure.

    Corrections conservées :
    - la fonction reçoit explicitement le modèle et l'heure ;
    - le vecteur horaire contient 24 positions ;
    - l'heure est validée dans l'intervalle 0-23.
    """
    if not isinstance(hour_to_predict, int):
        raise TypeError("hour_to_predict doit être un entier")
    if hour_to_predict < 0 or hour_to_predict > 23:
        raise ValueError("hour_to_predict doit être compris entre 0 et 23")

    input_pred = np.zeros((1, 24), dtype=int)
    input_pred[0, hour_to_predict] = 1

    pred = model.predict(input_pred)[0]
    return int(pred), COLOR_PRED_MAP[int(pred)]


def create_figure(data):
    """Crée une carte Plotly réellement interactive et robuste au redimensionnement."""
    if data.empty:
        fig = px.scatter_mapbox(
            lat=[48.1173],
            lon=[-1.6778],
            zoom=10,
            height=600,
            title="Aucune donnée trafic disponible",
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            dragmode="pan",
            uirevision="traffic-map",
            margin=dict(l=0, r=0, t=50, b=0),
        )
        return fig

    available_hover = [
        c
        for c in [
            "traffic",
            "traffic_label",
            "datetime",
            "average_vehicle_speed",
            "travel_time",
            "travel_time_reliability",
            "lat",
            "lon",
        ]
        if c in data.columns
    ]

    fig = px.scatter_mapbox(
        data,
        lat="lat",
        lon="lon",
        color="traffic_label",
        color_discrete_map=TRAFFIC_COLOR_MAP,
        category_orders={"traffic_label": ["Fluide", "Chargé", "Congestionné", "Impossible", "Inconnu"]},
        hover_name="road_name",
        hover_data=available_hover,
        zoom=10,
        height=600,
        title="Trafic routier – Rennes Métropole",
    )

    fig.update_traces(marker=dict(size=10, opacity=0.9))
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(
            center={"lat": float(data["lat"].mean()), "lon": float(data["lon"].mean())},
            zoom=10,
            uirevision="traffic-map",
        ),
        dragmode="pan",
        uirevision="traffic-map",
        legend_title_text="État du trafic",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def get_plotly_config() -> dict:
    """Configuration côté client : zoom molette, responsive et barre d'outils utile."""
    return {
        "responsive": True,
        "scrollZoom": True,
        "displayModeBar": True,
        "doubleClick": "reset",
        "displaylogo": False,
        "modeBarButtonsToRemove": ["select2d", "lasso2d"],
    }
