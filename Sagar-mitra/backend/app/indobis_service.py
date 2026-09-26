"""OBIS occurrence retrieval and normalization for the Indian EEZ map layer."""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OBIS_OCCURRENCES_URL = "https://api.obis.org/v3/occurrence"
# OBIS expects a Well-Known Text geometry, ordered as longitude latitude.
EEZ_BBOX = "POLYGON ((65 5, 95 5, 95 25, 65 25, 65 5))"
INDIAN_OCEAN_BBOX = "POLYGON ((20 -60, 120 -60, 120 30, 20 30, 20 -60))"
DEFAULT_LIMIT = 500
MAX_LIMIT = 1000
OBIS_REQUEST_TIMEOUT_SECONDS = 60.0
OBIS_CONNECT_TIMEOUT_SECONDS = 10.0
GLOBAL_TRACK_DEFAULT_YEARS = 10
DEFAULT_MIGRATORY_TAXA = ("Thunnus", "Chelonioidea", "Cetacea", "Selachimorpha")
SEASON_MONTHS = {
    "winter": {12, 1, 2},
    "summer": {3, 4, 5},
    "monsoon": {6, 7, 8, 9},
    "post_monsoon": {10, 11},
}
DEPTH_CLASSES = (
    ("surface", 0.0, 50.0, "#87CEFA"),
    ("mid_water", 50.0, 1000.0, "#1E88E5"),
    ("deep_sea", 1000.0, math.inf, "#001B44"),
)
UNKNOWN_DEPTH = {"category": "unknown", "color": "#94A3B8"}

# Map common user terms to accepted OBIS taxonomic names. Keys are normalized
# with casefold(), so user capitalization does not affect lookup.
COMMON_NAME_TAXA = {
    "coral": "Scleractinia",
    "corals": "Scleractinia",
    "tuna": "Thunnus",
    "tunas": "Thunnus",
    "turtle": "Chelonioidea",
    "turtles": "Chelonioidea",
    "sea turtle": "Chelonioidea",
    "sea turtles": "Chelonioidea",
    "dolphin": "Delphinidae",
    "dolphins": "Delphinidae",
    "shark": "Selachimorpha",
    "sharks": "Selachimorpha",
    "whale": "Cetacea",
    "whales": "Cetacea",
    "ray": "Batoidea",
    "rays": "Batoidea",
    "swordfish": "Xiphias gladius",
    "manta ray": "Mobula",
    "manta rays": "Mobula",
}
MIGRATORY_TAXON_HINTS = (
    "thunnus", "scombridae", "xiphias", "istiophoridae", "chelonioidea",
    "cheloniidae", "caretta", "eretmochelys", "lepidochelys", "dermochelys",
    "cetacea", "delphinidae", "balaenoptera", "megaptera", "physeter",
    "rhincodon", "selachimorpha", "mobula", "manta",
)


def _parse_date(value: date | str | None, field_name: str) -> date | None:
    """Parse supported date inputs; malformed or partial values are ignored."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None

    candidate = value.strip()
    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(candidate, date_format).date()
        except ValueError:
            continue

    logger.warning("Ignoring malformed %s value: %r", field_name, value)
    return None


def _parse_month(value: int | str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        month = int(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring malformed month filter: %r", value)
        return None
    if not 1 <= month <= 12:
        logger.warning("Ignoring out-of-range month filter: %r", value)
        return None
    return month


def _parse_season(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "premonsoon": "summer",
        "pre_monsoon": "summer",
        "postmonsoon": "post_monsoon",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SEASON_MONTHS:
        logger.warning("Ignoring unknown marine season filter: %r", value)
        return None
    return normalized


def get_indian_season(timestamp: date | datetime | str | None) -> str | None:
    """Map an observation date to India's broad seasonal grouping."""
    if isinstance(timestamp, datetime):
        month = timestamp.month
    elif isinstance(timestamp, date):
        month = timestamp.month
    elif isinstance(timestamp, str) and timestamp.strip():
        value = timestamp.strip()
        try:
            month = datetime.fromisoformat(value.replace("Z", "+00:00")).month
        except ValueError:
            try:
                month = date.fromisoformat(value[:10]).month
            except ValueError:
                return None
    else:
        return None
    return next((season for season, months in SEASON_MONTHS.items() if month in months), None)


def classify_depth(depth_m: Any) -> dict[str, str]:
    """Classify depth into a stable category and explicit Leaflet hex color."""
    try:
        depth = abs(float(depth_m))
    except (TypeError, ValueError, OverflowError):
        return dict(UNKNOWN_DEPTH)
    if not math.isfinite(depth):
        return dict(UNKNOWN_DEPTH)
    for category, minimum, maximum, color in DEPTH_CLASSES:
        if minimum <= depth <= maximum:
            return {"category": category, "color": color}
    return dict(UNKNOWN_DEPTH)


async def _fetch_records(client: httpx.AsyncClient, params: dict[str, Any]) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Return records and an upstream error code (if the query failed)."""
    try:
        response = await client.get(OBIS_OCCURRENCES_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        records = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            logger.error("OBIS returned an unexpected occurrence payload")
            return None, "unexpected_payload"
        return [record for record in records if isinstance(record, dict)], None
    except httpx.TimeoutException:
        logger.exception("Timed out retrieving marine occurrences from OBIS")
        return None, "upstream_timeout"
    except httpx.ConnectError:
        logger.exception("Could not connect to OBIS")
        return None, "upstream_connection_error"
    except httpx.HTTPStatusError:
        logger.exception("OBIS returned an unsuccessful HTTP status")
        return None, "upstream_http_error"
    except (httpx.RequestError, ValueError, TypeError):
        logger.exception("Unable to retrieve marine occurrences from OBIS")
        return None, "upstream_error"


def _normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [_normalize(record) for record in records]
    return [item for item in normalized if item is not None]


def _first(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize(record: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one OBIS occurrence into the stable frontend observation shape."""
    try:
        lat = float(_first(record, "decimalLatitude", "latitude"))
        lon = float(_first(record, "decimalLongitude", "longitude"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    raw_date = _first(record, "eventDate", "dateIdentified", "year")
    observation_date = str(raw_date) if raw_date is not None else ""
    # Preserve the date portion when OBIS returns an ISO datetime.
    if "T" in observation_date:
        observation_date = observation_date.split("T", 1)[0]

    observation_month = None
    try:
        observation_month = date.fromisoformat(observation_date[:10]).month
    except (TypeError, ValueError):
        pass
    observation_season = get_indian_season(observation_date)

    raw_depth = _first(
        record,
        "depth",
        "minimumDepthInMeters",
        "verticalCoordinate",
        "maximumDepthInMeters",
        "minDepth",
        "maxDepth",
    )
    try:
        depth_m = abs(float(raw_depth)) if raw_depth is not None else None
        if depth_m is not None and not math.isfinite(depth_m):
            depth_m = None
    except (TypeError, ValueError, OverflowError):
        depth_m = None
    depth_classification = classify_depth(depth_m)

    species_name = _first(record, "scientificName", "vernacularName", "species") or "Unknown species"
    dataset_name = _first(record, "datasetName", "datasetTitle", "dataset_name", "institutionCode") or "OBIS"
    record_id = _first(record, "occurrenceID", "id")
    source_link = (
        f"https://obis.org/occurrence/{record_id}"
        if record_id is not None
        else "https://obis.org"
    )
    return {
        "lat": lat,
        "lon": lon,
        "observation_date": observation_date,
        "month": observation_month,
        "season": observation_season,
        "depth_m": depth_m,
        "depth_category": depth_classification["category"],
        "depth_color": depth_classification["color"],
        "species_name": str(species_name),
        "dataset_name": str(dataset_name),
        "source_link": source_link,
    }


def _observation_sort_key(observation: dict[str, Any]) -> tuple[int, str]:
    """Sort valid observation dates chronologically, placing unknown dates last."""
    value = str(observation.get("observation_date") or "").strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (0, parsed.isoformat())
    except ValueError:
        try:
            return (0, date.fromisoformat(value[:10]).isoformat())
        except ValueError:
            return (1, value)


def _is_migratory_taxon(taxon_name: str) -> bool:
    normalized = taxon_name.casefold()
    return any(hint in normalized for hint in MIGRATORY_TAXON_HINTS)


async def get_marine_observations(
    species: str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    month: int | str | None = None,
    season: str | None = None,
    region: str = "indian_ocean",
    include_global_tracks: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Fetch normalized records within a selectable extent and normalize them.

    Filters are applied without substituting unrelated records. The envelope
    distinguishes a successful empty result from an upstream failure.
    """
    species_input = (species or "").strip()
    taxon_name = COMMON_NAME_TAXA.get(species_input.casefold(), species_input)
    parsed_start = _parse_date(start_date, "start_date")
    parsed_end = _parse_date(end_date, "end_date")
    parsed_month = _parse_month(month)
    parsed_season = _parse_season(season)
    normalized_region = (region or "indian_ocean").strip().casefold().replace("-", "_")
    if normalized_region not in {"indian_ocean", "indian_eez", "global"}:
        logger.warning("Unknown marine observation region %r; using Indian Ocean", region)
        normalized_region = "indian_ocean"
    geometry = {
        "indian_ocean": INDIAN_OCEAN_BBOX,
        "indian_eez": EEZ_BBOX,
        "global": None,
    }[normalized_region]
    if parsed_start and parsed_end and parsed_start > parsed_end:
        logger.warning("Ignoring inverted marine observation date range")
        parsed_start = parsed_end = None

    today = datetime.now(timezone.utc).date()
    track_start = parsed_start or (parsed_end - timedelta(days=GLOBAL_TRACK_DEFAULT_YEARS * 365) if parsed_end else today - timedelta(days=GLOBAL_TRACK_DEFAULT_YEARS * 365))
    track_end = parsed_end or today
    migratory_track_supported = bool(taxon_name and _is_migratory_taxon(taxon_name))

    requested_limit = max(int(limit), MAX_LIMIT) if parsed_month or parsed_season else int(limit)
    safe_limit = min(max(requested_limit, 1), MAX_LIMIT)
    params: dict[str, Any] = {"size": safe_limit}
    if geometry:
        params["geometry"] = geometry
    if taxon_name:
        # OBIS scientificname searches resolve taxonomic names and descendants;
        # common terms are mapped above before being sent to the API.
        params["scientificname"] = taxon_name
    if parsed_start:
        params["startdate"] = parsed_start.isoformat()
    if parsed_end:
        params["enddate"] = parsed_end.isoformat()
    if include_global_tracks and normalized_region == "global" and migratory_track_supported:
        params.setdefault("startdate", track_start.isoformat())
        params.setdefault("enddate", track_end.isoformat())

    def apply_temporal_filters(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            observation for observation in observations
            if (parsed_month is None or observation["month"] == parsed_month)
            and (parsed_season is None or observation["season"] == parsed_season)
        ]

    tracks_available = False
    track_message = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(
            OBIS_REQUEST_TIMEOUT_SECONDS,
            connect=OBIS_CONNECT_TIMEOUT_SECONDS,
        )) as client:
            records, error_code = await _fetch_records(client, params)
            if records is None:
                return {"data": [], "status": "error", "message": "Marine observations are temporarily unavailable from OBIS.", "error_code": error_code, "source": "OBIS", "tracks": {"requested": include_global_tracks, "available": False, "message": "Track data is unavailable because the OBIS query failed."}}
            observations = apply_temporal_filters(_normalize_records(records))
            if include_global_tracks and not migratory_track_supported:
                track_message = "Migratory paths are available for supported migratory taxa such as tuna, swordfish, sea turtles, whales, and manta rays."
            elif include_global_tracks and normalized_region == "global":
                tracks_available = True
                for observation in observations:
                    observation["track_scope"] = "global"
            elif include_global_tracks:
                track_taxa = (taxon_name,)
                per_taxon_limit = MAX_LIMIT
                def observation_key(item: dict[str, Any]) -> str:
                    if item["source_link"] != "https://obis.org":
                        return item["source_link"]
                    return "|".join((
                        item["species_name"], item["observation_date"],
                        str(item["lat"]), str(item["lon"]),
                    ))

                known_records = {observation_key(item) for item in observations}

                track_params: dict[str, Any] = {
                    "scientificname": taxon_name,
                    "size": per_taxon_limit,
                    "startdate": track_start.isoformat(),
                    "enddate": track_end.isoformat(),
                }
                track_records, track_error = await _fetch_records(client, track_params)
                if track_records is None:
                    track_message = "Regional observations loaded, but global migratory-path data could not be retrieved."
                    logger.warning("OBIS global track lookup failed: %s", track_error)
                else:
                    tracks_available = True
                    track_observations = apply_temporal_filters(_normalize_records(track_records))
                    # The regional results are also part of the same chronological
                    # population sequence. Mark all records in the path dataset so
                    # the metadata count matches what the frontend can draw.
                    for observation in observations:
                        observation["track_scope"] = "global"
                    known_records = {observation_key(item) for item in observations}
                    for observation in track_observations:
                        key = observation_key(observation)
                        if key in known_records:
                            continue
                        observation["track_scope"] = "global"
                        observation["track_only"] = True
                        known_records.add(key)
                        observations.append(observation)
            observations.sort(key=_observation_sort_key)
            return {
                "data": observations, "status": "success", "message": None,
                "error_code": None, "source": "OBIS",
                "tracks": {"requested": include_global_tracks, "available": tracks_available,
                           "message": track_message,
                           "point_count": sum(
                               item.get("track_scope") == "global"
                               and _observation_sort_key(item)[0] == 0
                               for item in observations
                           )},
            }
    except (httpx.RequestError, ValueError, TypeError, OverflowError):
        logger.exception("Marine occurrence processing failed")
        return {"data": [], "status": "error", "message": "Marine observations could not be processed.", "error_code": "processing_error", "source": "OBIS", "tracks": {"requested": include_global_tracks, "available": False, "message": "Track data could not be processed."}}
