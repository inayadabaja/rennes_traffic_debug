from __future__ import annotations

import numpy as np
import plotly.express as px


COLOR_PRED_MAP = {
    0: ("Trafic fluide", "#2ecc71"),
    1: ("Trafic dense", "#f39c12"),
    2: ("Trafic saturé", "#e74c3c"),
}

TRAFFIC_COLOR_MAP = {
    "freeFlow": "green",
    "heavy": "orange",
    "congested": "red",
}


def prediction_from_model(model, hour_to_predict: int):
    """
    Prédit une classe de trafic à partir de l'heure sélectionnée.
    Le modèle attend un vecteur one-hot de 24 valeurs : 0h à 23h.
    """
    if not isinstance(hour_to_predict, int):
        raise TypeError("hour_to_predict doit être un entier")
    if hour_to_predict < 0 or hour_to_predict > 23:
        raise ValueError("hour_to_predict doit être compris entre 0 et 23")

    input_pred = np.zeros((1, 24), dtype=int)
    input_pred[0, hour_to_predict] = 1

    pred = model.predict(input_pred)[0]
    cat = int(pred)
    return cat, COLOR_PRED_MAP.get(cat, ("Trafic inconnu", "gray"))


def create_figure(data):
    """Construit la carte interactive Plotly des points de trafic."""
    if data.empty:
        fig = px.scatter_mapbox(
            lat=[48.1173],
            lon=[-1.6778],
            zoom=10,
            height=550,
            title="Aucune donnée trafic disponible",
        )
        fig.update_layout(mapbox_style="carto-positron", margin=dict(l=0, r=0, t=50, b=0))
        return fig

    fig = px.scatter_mapbox(
        data,
        lat="lat",
        lon="lon",
        color="traffic",
        color_discrete_map=TRAFFIC_COLOR_MAP,
        hover_name="road_name",
        hover_data=["traffic", "datetime"],
        zoom=10,
        height=550,
        title="Trafic routier – Rennes Métropole",
    )
    fig.update_layout(mapbox_style="carto-positron", margin=dict(l=0, r=0, t=50, b=0))
    return fig
