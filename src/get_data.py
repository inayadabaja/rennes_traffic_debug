from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests


DEFAULT_EXPORT_URL = (
    "https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/"
    "etat-du-trafic-en-temps-reel/exports/json"
    "?lang=fr&timezone=Europe%2FParis&use_labels=true&delimiter=%3B"
)

DEFAULT_RECORDS_URL = (
    "https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/"
    "etat-du-trafic-en-temps-reel/records"
)


TRAFFIC_NORMALIZATION = {
    "freeflow": "freeFlow",
    "free_flow": "freeFlow",
    "free flow": "freeFlow",
    "fluid": "freeFlow",
    "fluide": "freeFlow",
    "libre": "freeFlow",
    "heavy": "heavy",
    "dense": "heavy",
    "ralenti": "heavy",
    "congested": "congested",
    "blocked": "congested",
    "bloque": "congested",
    "bloqué": "congested",
    "sature": "congested",
    "saturé": "congested",
    "unknown": "unknown",
    "inconnu": "unknown",
    "": "unknown",
}


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.getenv("RENNES_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Apikey {api_key}"
    return headers


def _request_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(url, headers=_headers(), params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_data() -> Any:
    """
    Récupère les données Rennes Métropole.

    Correction importante :
    - par défaut on utilise l'endpoint exports/json, comme dans le projet qui affiche beaucoup de points ;
    - si l'utilisateur force l'endpoint /records, on pagine avec limit=100 + offset,
      car un seul appel /records?limit=100 ne renvoie qu'une partie des points.
    """
    url = os.getenv("RENNES_API_URL", DEFAULT_EXPORT_URL).strip() or DEFAULT_EXPORT_URL

    # Cas 1 : export JSON complet. Réponse attendue = liste de dictionnaires.
    if "/exports/json" in url:
        return _request_json(url)

    # Cas 2 : endpoint records. Réponse attendue = dict avec "results" + pagination.
    if "/records" in url:
        limit = int(os.getenv("RENNES_API_LIMIT", "100"))
        limit = max(1, min(limit, 100))  # l'API refuse parfois les limites supérieures à 100
        max_pages = int(os.getenv("RENNES_API_MAX_PAGES", "50"))

        all_records: list[dict[str, Any]] = []
        offset = 0

        for _ in range(max_pages):
            payload = _request_json(url, params={"limit": limit, "offset": offset})
            records = payload.get("results", []) if isinstance(payload, dict) else []

            if not records:
                break

            all_records.extend(records)

            total_count = payload.get("total_count") or payload.get("nhits") or payload.get("total")
            offset += limit

            if total_count is not None and offset >= int(total_count):
                break
            if len(records) < limit:
                break

        return all_records

    # Cas fallback : URL custom.
    return _request_json(url)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    """Accepte les deux formats : exports/json -> list ; records -> {'results': [...]}"""
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("results") or payload.get("records") or []
    else:
        records = []

    cleaned: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        # Compatibilité avec certains formats Opendatasoft anciens : {"fields": {...}}
        if "fields" in record and isinstance(record["fields"], dict):
            record = record["fields"]
        cleaned.append(record)
    return cleaned


def _normalize_traffic(value: Any) -> str:
    raw = str(value or "").strip()
    key = raw.lower().replace("_", " ").strip()
    key_compact = raw.lower().replace("-", "").replace("_", "").replace(" ", "")
    return TRAFFIC_NORMALIZATION.get(key, TRAFFIC_NORMALIZATION.get(key_compact, raw or "unknown"))


def processing_one_point(record: dict[str, Any]) -> dict[str, Any]:
    geo = record.get("geo_point_2d") or record.get("geo_point") or record.get("geo") or {}

    lat = None
    lon = None

    if isinstance(geo, dict):
        lat = geo.get("lat") or geo.get("latitude")
        lon = geo.get("lon") or geo.get("lng") or geo.get("longitude")
    elif isinstance(geo, (list, tuple)) and len(geo) >= 2:
        # Opendatasoft renvoie souvent [lat, lon] quand ce n'est pas un dict.
        lat, lon = geo[0], geo[1]

    traffic = (
        record.get("trafficstatus")      # clé utilisée dans le projet fonctionnel
        or record.get("trafficStatus")   # variante camelCase
        or record.get("traffic_status")
        or record.get("traffic")
        or record.get("etat_trafic")
        or record.get("etat_du_trafic")
        or record.get("status")
        or "unknown"
    )

    road_name = (
        record.get("road_name")
        or record.get("nom_axe")
        or record.get("denomination")
        or record.get("libelle")
        or record.get("predefinedlocationreference")
        or "Inconnu"
    )

    dt = record.get("datetime") or record.get("date") or record.get("timestamp") or ""

    return {
        "road_name": road_name,
        "traffic": _normalize_traffic(traffic),
        "lat": lat,
        "lon": lon,
        "datetime": dt,
    }


def get_clean_data() -> pd.DataFrame:
    payload = fetch_data()
    records = _extract_records(payload)
    rows = [processing_one_point(record) for record in records]

    res_df = pd.DataFrame(rows)

    if res_df.empty:
        return pd.DataFrame(columns=["road_name", "traffic", "lat", "lon", "datetime"])

    for col in ["road_name", "traffic", "lat", "lon", "datetime"]:
        if col not in res_df.columns:
            res_df[col] = None

    res_df["lat"] = pd.to_numeric(res_df["lat"], errors="coerce")
    res_df["lon"] = pd.to_numeric(res_df["lon"], errors="coerce")

    res_df = res_df.dropna(subset=["lat", "lon"])
    res_df = res_df[res_df["traffic"].str.lower() != "unknown"]

    return res_df.reset_index(drop=True)
