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
GLOBAL_TRACK_DEFAULT_YEARS = 10
DEFAULT_MIGRATORY_TAXA = ("Thunnus", "Chelonioidea", "Cetacea", "Selachimorpha")
SEASON_MONTHS = {
    "winter": {12, 1, 2},
    "pre_monsoon": {3, 4, 5},
    "monsoon": {6, 7, 8, 9},
    "post_monsoon": {10, 11},
}

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
}


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
    aliases = {"premonsoon": "pre_monsoon", "postmonsoon": "post_monsoon"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in SEASON_MONTHS:
        logger.warning("Ignoring unknown marine season filter: %r", value)
        return None
    return normalized


async def _fetch_records(client: httpx.AsyncClient, params: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return records, [] for a successful empty response, or None on API failure."""
    try:
        response = await client.get(OBIS_OCCURRENCES_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        records = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            logger.error("OBIS returned an unexpected occurrence payload")
            return None
        return [record for record in records if isinstance(record, dict)]
    except httpx.TimeoutException:
        logger.exception("Timed out retrieving marine occurrences from OBIS")
    except httpx.ConnectError:
        logger.exception("Could not connect to OBIS")
    except httpx.HTTPStatusError:
        logger.exception("OBIS returned an unsuccessful HTTP status")
    except (httpx.RequestError, ValueError, TypeError):
        logger.exception("Unable to retrieve marine occurrences from OBIS")
    return None


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
    observation_season = next(
        (season for season, months in SEASON_MONTHS.items() if observation_month in months),
        None,
    )

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
        "species_name": str(species_name),
        "dataset_name": str(dataset_name),
        "source_link": source_link,
    }


async def get_marine_observations(
    species: str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    month: int | str | None = None,
    season: str | None = None,
    region: str = "indian_ocean",
    include_global_tracks: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch normalized records within a selectable extent and normalize them.

    Filters are applied to the requested region without substituting unrelated
    records when a species search has no matches. API errors return [] gracefully.
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

    def apply_temporal_filters(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            observation for observation in observations
            if (parsed_month is None or observation["month"] == parsed_month)
            and (parsed_season is None or observation["season"] == parsed_season)
        ]

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            records = await _fetch_records(client, params)
            if records is None:
                return []
            observations = apply_temporal_filters(_normalize_records(records))
            if include_global_tracks and normalized_region != "global":
                today = datetime.now(timezone.utc).date()
                track_start = parsed_start or (parsed_end - timedelta(days=GLOBAL_TRACK_DEFAULT_YEARS * 365) if parsed_end else today - timedelta(days=GLOBAL_TRACK_DEFAULT_YEARS * 365))
                track_end = parsed_end or today
                track_taxa = (taxon_name,) if taxon_name else DEFAULT_MIGRATORY_TAXA
                per_taxon_limit = min(MAX_LIMIT, max(DEFAULT_LIMIT, MAX_LIMIT // len(track_taxa)))
                def observation_key(item: dict[str, Any]) -> str:
                    if item["source_link"] != "https://obis.org":
                        return item["source_link"]
                    return "|".join((
                        item["species_name"], item["observation_date"],
                        str(item["lat"]), str(item["lon"]),
                    ))

                known_records = {observation_key(item) for item in observations}

                for track_taxon in track_taxa:
                    track_params: dict[str, Any] = {
                        "scientificname": track_taxon,
                        "size": per_taxon_limit,
                        "startdate": track_start.isoformat(),
                        "enddate": track_end.isoformat(),
                    }
                    track_records = await _fetch_records(client, track_params)
                    if track_records is None:
                        continue
                    track_observations = apply_temporal_filters(_normalize_records(track_records))
                    for observation in track_observations:
                        key = observation_key(observation)
                        if key in known_records:
                            continue
                        observation["track_scope"] = "global"
                        known_records.add(key)
                        observations.append(observation)
            return observations
    except (httpx.RequestError, ValueError, TypeError, OverflowError):
        logger.exception("Marine occurrence processing failed")
        return []
