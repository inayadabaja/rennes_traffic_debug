from __future__ import annotations
import os
import requests
import pandas as pd


def fetch_data() -> dict:
    url = os.getenv(
        "RENNES_API_URL",
        "https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/etat-du-trafic-en-temps-reel/records"
    )

    headers = {}
    api_key = os.getenv("RENNES_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Apikey {api_key}"

    params = {"limit": 100}

    response = requests.get(url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def processing_one_point(record: dict) -> dict:
    geo = record.get("geo_point_2d") or {}

    lat = None
    lon = None

    if isinstance(geo, dict):
        lat = geo.get("lat") or geo.get("latitude")
        lon = geo.get("lon") or geo.get("lng") or geo.get("longitude")
    elif isinstance(geo, list) and len(geo) >= 2:
        lat = geo[0]
        lon = geo[1]

    traffic = (
        record.get("trafficStatus")     # clé officielle actuelle
        or record.get("traffic")
        or record.get("traffic_status")
        or record.get("etat_trafic")
        or record.get("etat_du_trafic")
        or record.get("status")
        or "unknown"
    )

    road_name = (
        record.get("road_name")
        or record.get("nom_axe")
        or record.get("libelle")
        or "Inconnu"
    )

    dt = (
        record.get("datetime")
        or record.get("date")
        or record.get("timestamp")
        or ""
    )

    return {
        "road_name": road_name,
        "traffic": str(traffic),
        "lat": lat,
        "lon": lon,
        "datetime": dt,
    }


def get_clean_data() -> pd.DataFrame:
    payload = fetch_data()
    records = payload.get("results", [])
    rows = [processing_one_point(r) for r in records]

    res_df = pd.DataFrame(rows)

    if res_df.empty:
        return pd.DataFrame(columns=["road_name", "traffic", "lat", "lon", "datetime"])

    for col in ["road_name", "traffic", "lat", "lon", "datetime"]:
        if col not in res_df.columns:
            res_df[col] = None

    res_df["lat"] = pd.to_numeric(res_df["lat"], errors="coerce")
    res_df["lon"] = pd.to_numeric(res_df["lon"], errors="coerce")

    res_df = res_df.dropna(subset=["lat", "lon"])

    return res_df.reset_index(drop=True)