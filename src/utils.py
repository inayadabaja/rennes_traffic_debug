from __future__ import annotations
import numpy as np
import plotly.express as px


COLOR_PRED_MAP = {
    0: ("Trafic fluide", "#2ecc71"),
    1: ("Trafic dense", "#f39c12"),
    2: ("Trafic saturé", "#e74c3c"),
}


def prediction_from_model(model, hour_to_predict: int):
    """
    Corrigé :
    - la fonction prend bien 2 arguments
    - le vecteur horaire fait 24 cases et non 25
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
    """
    Corrigé :
    - syntaxe propre
    - visualisation exploitable
    """
    if data.empty:
        fig = px.scatter_mapbox(
            lat=[48.1173],
            lon=[-1.6778],
            zoom=10,
            height=550,
            title="Aucune donnée trafic disponible"
        )
        fig.update_layout(mapbox_style="open-street-map")
        return fig

    fig = px.scatter_mapbox(
        data,
        lat="lat",
        lon="lon",
        color="traffic",
        hover_name="road_name",
        hover_data=["traffic", "datetime"],
        zoom=10,
        height=550,
        title="Trafic routier – Rennes Métropole"
    )
    fig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=50, b=0))
    return fig