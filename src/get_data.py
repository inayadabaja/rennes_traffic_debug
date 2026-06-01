from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

DEFAULT_RENNES_API_URL = (
    "https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/"
    "etat-du-trafic-en-temps-reel/records"
)

# L'API Explore v2.1 accepte généralement 100 enregistrements par page.
# Un limit trop élevé a déjà provoqué des erreurs 400 dans les logs du projet.
DEFAULT_LIMIT = 100
MAX_SAFE_LIMIT = 100

STATUS_LABELS = {
    "unknown": "Inconnu",
    "freeflow": "Fluide",
    "free_flow": "Fluide",
    "heavy": "Chargé",
    "congested": "Congestionné",
    "impossible": "Impossible",
}

STATUS_SEVERITY = {
    "unknown": 0,
    "freeflow": 1,
    "free_flow": 1,
    "heavy": 2,
    "congested": 3,
    "impossible": 4,
}


def _cache_path() -> Path:
    return Path(os.getenv("RENNES_CACHE_PATH", "data/last_rennes_payload.json"))


def _safe_limit() -> int:
    raw = os.getenv("RENNES_API_LIMIT", str(DEFAULT_LIMIT))
    try:
        limit = int(raw)
    except ValueError:
        limit = DEFAULT_LIMIT
    return max(1, min(limit, MAX_SAFE_LIMIT))


def _write_cache(payload: dict[str, Any]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        # Le cache est une sécurité de démonstration : il ne doit jamais casser l'application.
        pass


def _read_cache() -> dict[str, Any] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def fetch_data() -> dict[str, Any]:
    """
    Récupère les données Rennes Métropole.

    Corrections importantes pour E5 :
    - limite API bornée à 100 afin d'éviter les erreurs HTTP 400 ;
    - timeout configurable ;
    - cache local utilisé en secours pour ne pas figer la démonstration si l'API externe échoue.
    """
    url = os.getenv("RENNES_API_URL", DEFAULT_RENNES_API_URL)
    timeout = int(os.getenv("RENNES_REQUEST_TIMEOUT", "20"))

    headers: dict[str, str] = {}
    api_key = os.getenv("RENNES_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Apikey {api_key}"

    params = {"limit": _safe_limit()}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        _write_cache(payload)
        return payload
    except requests.RequestException:
        cached = _read_cache()
        if cached is not None:
            cached["_from_cache"] = True
            return cached
        raise


def _lower_key_map(record: dict[str, Any]) -> dict[str, str]:
    return {str(k).lower(): k for k in record.keys()}


def _get_first(record: dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    if not isinstance(record, dict):
        return default
    lowered = _lower_key_map(record)
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
        key = lowered.get(name.lower())
        if key is not None and record.get(key) not in (None, ""):
            return record[key]
    return default


def _normalize_status(raw_status: Any) -> tuple[str, str, int]:
    raw = str(raw_status or "unknown").strip()
    key = raw.replace(" ", "").replace("-", "").lower()
    label = STATUS_LABELS.get(key, raw if raw else "Inconnu")
    severity = STATUS_SEVERITY.get(key, 0)
    return raw, label, severity


def _extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Compatible avec :
    - API Explore v2.1 : payload['results'] = [{...}]
    - anciens formats Opendatasoft : payload['records'][i]['fields'] = {...}
    """
    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("results"), list):
        return [r for r in payload["results"] if isinstance(r, dict)]

    if isinstance(payload.get("records"), list):
        rows: list[dict[str, Any]] = []
        for item in payload["records"]:
            if not isinstance(item, dict):
                continue
            fields = item.get("fields")
            if isinstance(fields, dict):
                rows.append(fields)
            else:
                rows.append(item)
        return rows

    return []


def _coords_from_nested_list(value: Any) -> list[tuple[float, float]]:
    """Extrait récursivement des couples (lon, lat) depuis une géométrie GeoJSON."""
    coords: list[tuple[float, float]] = []
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
            lon = float(value[0])
            lat = float(value[1])
            coords.append((lon, lat))
        else:
            for child in value:
                coords.extend(_coords_from_nested_list(child))
    return coords


def _extract_lat_lon(record: dict[str, Any]) -> tuple[Any, Any]:
    geo = _get_first(record, ["geo_point_2d", "geopoint", "geo_point", "coordinates"])

    if isinstance(geo, dict):
        lat = _get_first(geo, ["lat", "latitude"])
        lon = _get_first(geo, ["lon", "lng", "longitude"])
        if lat is not None and lon is not None:
            return lat, lon

    if isinstance(geo, (list, tuple)) and len(geo) >= 2:
        # geo_point_2d Opendatasoft est souvent [lat, lon].
        return geo[0], geo[1]

    geometry = _get_first(record, ["geo_shape", "geometry", "geom"])
    if isinstance(geometry, str):
        try:
            geometry = json.loads(geometry)
        except json.JSONDecodeError:
            geometry = None

    if isinstance(geometry, dict):
        coords = _coords_from_nested_list(geometry.get("coordinates"))
        if coords:
            lon_values = [p[0] for p in coords]
            lat_values = [p[1] for p in coords]
            return sum(lat_values) / len(lat_values), sum(lon_values) / len(lon_values)

    return None, None


def processing_one_point(record: dict[str, Any]) -> dict[str, Any]:
    """Extraction robuste d'un enregistrement de trafic."""
    lat, lon = _extract_lat_lon(record)

    traffic_raw = _get_first(
        record,
        [
            "trafficStatus",
            "traffic_status",
            "traffic",
            "etat_trafic",
            "etat_du_trafic",
            "status",
        ],
        "unknown",
    )
    traffic, traffic_label, traffic_severity = _normalize_status(traffic_raw)

    road_name = _get_first(
        record,
        [
            "road_name",
            "nom_axe",
            "libelle",
            "predefinedLocationReference",
            "predefinedLocationRerefence",  # orthographe publiée sur la fiche Rennes
            "predefinedlocationreference",
            "predefinedlocationrerefence",
        ],
        "Inconnu",
    )

    dt = _get_first(record, ["datetime", "date", "timestamp", "lastupdate"], "")
    speed = _get_first(record, ["averageVehicleSpeed", "average_vehicle_speed", "speed"])
    travel_time = _get_first(record, ["travelTime", "travel_time"])
    reliability = _get_first(record, ["travelTimeReliability", "travel_time_reliability"])

    return {
        "road_name": str(road_name),
        "traffic": str(traffic),
        "traffic_label": traffic_label,
        "traffic_severity": traffic_severity,
        "lat": lat,
        "lon": lon,
        "datetime": dt,
        "average_vehicle_speed": speed,
        "travel_time": travel_time,
        "travel_time_reliability": reliability,
    }


def get_clean_data() -> pd.DataFrame:
    payload = fetch_data()
    records = _extract_records(payload)
    rows = [processing_one_point(r) for r in records]

    columns = [
        "road_name",
        "traffic",
        "traffic_label",
        "traffic_severity",
        "lat",
        "lon",
        "datetime",
        "average_vehicle_speed",
        "travel_time",
        "travel_time_reliability",
    ]
    res_df = pd.DataFrame(rows, columns=columns)

    if res_df.empty:
        return pd.DataFrame(columns=columns)

    res_df["lat"] = pd.to_numeric(res_df["lat"], errors="coerce")
    res_df["lon"] = pd.to_numeric(res_df["lon"], errors="coerce")
    res_df["traffic_severity"] = pd.to_numeric(res_df["traffic_severity"], errors="coerce").fillna(0).astype(int)

    for numeric_col in ["average_vehicle_speed", "travel_time", "travel_time_reliability"]:
        res_df[numeric_col] = pd.to_numeric(res_df[numeric_col], errors="coerce")

    res_df = res_df.dropna(subset=["lat", "lon"])
    return res_df.reset_index(drop=True)
