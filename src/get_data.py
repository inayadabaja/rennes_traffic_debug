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
    """
    Extraction robuste d'un enregistrement.
    On évite d'utiliser des clés supposées non présentes.
    """

    # géométrie
    geo = record.get("geo_point_2d") or {}
    lat = geo.get("lat") or geo.get("latitude")
    lon = geo.get("lon") or geo.get("longitude")

    # trafic : on essaie plusieurs clés plausibles
    traffic = (
        record.get("traffic")
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
        "traffic": str(traffic).lower(),
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

    res_df = res_df.dropna(subset=["lat", "lon"])
    res_df = res_df[res_df["traffic"] != "unknown"]  # crochet fermant corrigé

    return res_df.reset_index(drop=True)