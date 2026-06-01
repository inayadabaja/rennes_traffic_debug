import pandas as pd
import numpy as np

from src.get_data import processing_one_point, get_clean_data
from src.model_service import DummyTrafficModel
from src.utils import prediction_from_model, create_figure


def test_processing_one_point_extracts_rennes_fields():
    record = {
        "geo_point_2d": {"lat": 48.11, "lon": -1.67},
        "trafficStatus": "freeFlow",
        "predefinedLocationRerefence": "RM_001_D",
        "datetime": "2026-06-01T11:55:00+02:00",
        "averageVehicleSpeed": 42,
    }
    row = processing_one_point(record)
    assert row["lat"] == 48.11
    assert row["lon"] == -1.67
    assert row["traffic_label"] == "Fluide"
    assert row["road_name"] == "RM_001_D"


def test_prediction_valid_hours():
    model = DummyTrafficModel()
    pred, (label, _color) = prediction_from_model(model, 17)
    assert pred == 2
    assert label == "Trafic saturé"


def test_prediction_rejects_invalid_hour():
    model = DummyTrafficModel()
    try:
        prediction_from_model(model, 24)
        assert False, "Une heure invalide doit déclencher une exception"
    except ValueError:
        assert True


def test_create_figure_contains_interactive_map_layout():
    df = pd.DataFrame([
        {"lat": 48.11, "lon": -1.67, "traffic_label": "Fluide", "traffic": "freeFlow", "road_name": "A", "datetime": "t"},
        {"lat": 48.12, "lon": -1.68, "traffic_label": "Congestionné", "traffic": "congested", "road_name": "B", "datetime": "t"},
    ])
    fig = create_figure(df)
    layout = fig.to_dict()["layout"]
    assert layout["dragmode"] == "pan"
    assert layout["mapbox"]["style"] == "open-street-map"
