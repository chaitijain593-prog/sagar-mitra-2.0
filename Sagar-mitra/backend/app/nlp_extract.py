"""
Sagar Mitra - Phase 1 NLP: User Query -> Structured Parameters
=================================================================
Takes free-text user input (any language) and extracts the structured
parameters needed to run the Statistical Anomaly Engine and Phase 2
(advisory generation).
"""
import json
import os
import re
from datetime import date
from typing import Optional, Tuple

from app.advisory import generate_content, LITE_MODEL, GROQ_API_KEY

EXTRACTION_SYSTEM_PROMPT = """
You are the input-parsing layer for Sagar Mitra, an ocean intelligence system
for the Maharashtra coast (Arabian Sea).

Extract structured query parameters from the user's message, regardless of
language (English/Hindi/Marathi/Konkani). Respond with ONLY valid JSON, no
markdown, no explanation, matching this exact schema:

{
  "location_name": "<place name mentioned, or nearest known coastal town if implied, else null>",
  "latitude": <float, best-guess coordinates for that Maharashtra coastal location, else null>,
  "longitude": <float, else null>,
  "date": "<YYYY-MM-DD if mentioned/implied (e.g. 'tomorrow'), else null>",
  "depth_m": <float, fishing/query depth if mentioned, else 10.0 as default surface>,
  "persona": "<one of: Fisherman, Student, Researcher, General Public - infer from tone/question, default Fisherman>",
  "language": "<detected input language name, e.g. Marathi, Hindi, English>",
  "query_intent": "<short phrase: e.g. 'fishing safety check', 'general curiosity', 'research query'>"
}

Known Maharashtra coastal reference points (use if user names these or nearby areas):
Mumbai (19.07,72.87), Ratnagiri (16.99,73.30), Sindhudurg (16.02,73.45),
Raigad/Alibaug (18.64,72.87), Palghar (19.70,72.77), Vengurla (15.85,73.63).

If the user gives no location, default to Ratnagiri coordinates.
If no date, use today.
Today's date is {today}.
"""


def extract_query_parameters(user_message: str, model: str = LITE_MODEL) -> dict:
    """
    Phase 1 NLP: Converts a free-text user query into structured parameters
    for the Statistical Anomaly Engine.

    Runs on the lite model (see advisory.LITE_MODEL) -- structured field
    extraction is a classification-shaped task, and keeping it off the
    synthesizer's model means a burst of location lookups can't eat into
    the quota the final localized advisory needs.
    """
    system_instruction = EXTRACTION_SYSTEM_PROMPT.replace("{today}", date.today().isoformat())

    response = generate_content(
        model=model,
        contents=user_message,
        system_instruction=system_instruction,
        temperature=0.1,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    text = (response.text or "").strip()
    text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse extraction output: {text}")


# ---------------------------------------------------------------------------
# Coordinate resolver for the ORCA orchestrator (/api/orchestrate)
# ---------------------------------------------------------------------------
# extract_query_parameters() above is the full Phase-1 NLP pass (depth,
# persona, language, etc.) used by the legacy /api/chat pipeline, and it
# ALWAYS returns some lat/lon (defaulting to Ratnagiri) even when the user
# named no place at all -- fine for that pipeline, wrong for this one.
#
# The ORCA graph was previously ignoring user_message entirely and always
# operating on whatever coordinate the frontend happened to send (the
# vessel's actual reported GPS position), even when the user typed a
# specific place name in their query. This resolver fixes that: it treats
# the message text as the primary source of truth for location, and only
# defers to the caller-supplied GPS coordinate when the question is
# genuinely about "here" / "my current location".

_COORD_PATTERN = re.compile(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)")

_CURRENT_LOCATION_PHRASES = (
    "my location", "my current location", "current position", "current location",
    "near me", "around me", "where i am", "right here", "this spot", "my position",
    "here safe", "is it safe here",
)

# Small, fast local gazetteer for common Indian coastal reference points, so
# the common case never needs a OpenAI call. Anything not listed here falls
# through to the LLM-based extract_query_parameters() below (only when a
# OpenAI key is configured), which can resolve arbitrary place names.
KNOWN_COASTAL_LOCATIONS = {
    "mumbai": (19.07, 72.87), "bombay": (19.07, 72.87),
    "ratnagiri": (16.99, 73.30),
    "sindhudurg": (16.02, 73.45),
    "alibaug": (18.64, 72.87), "raigad": (18.64, 72.87),
    "palghar": (19.70, 72.77),
    "vengurla": (15.85, 73.63),
    "goa": (15.30, 73.83), "panaji": (15.49, 73.82),
    "mangalore": (12.87, 74.84), "mangaluru": (12.87, 74.84),
    "kochi": (9.93, 76.26), "cochin": (9.93, 76.26),
    "chennai": (13.08, 80.27), "madras": (13.08, 80.27),
    "visakhapatnam": (17.69, 83.22), "vizag": (17.69, 83.22),
    "surat": (21.17, 72.83),
    "kandla": (23.03, 70.22),
    "kollam": (8.88, 76.60),
    "kanyakumari": (8.08, 77.55),
    "puri": (19.80, 85.83),
}


def _is_current_location_query(message: str) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in _CURRENT_LOCATION_PHRASES)


def extract_coordinates_from_message(user_message: str) -> Optional[Tuple[float, float]]:
    """
    Best-effort location resolver for the ORCA orchestrator.

    Returns (lat, lon) if the message clearly names a place or contains an
    explicit coordinate pair, or None if it doesn't (e.g. a "is my current
    location safe?" style question, or a message with no location at all)
    -- callers should fall back to the caller-supplied GPS coordinate in
    the None case.
    """
    if not user_message or _is_current_location_query(user_message):
        return None

    # 1. Explicit "lat, lon" pair typed directly in the message.
    match = _COORD_PATTERN.search(user_message)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return (lat, lon)

    # 2. Known place name (fast, no API call).
    text = user_message.lower()
    for name, coords in KNOWN_COASTAL_LOCATIONS.items():
        if name in text:
            return coords

    # 3. Fall through to the OpenAI-based extractor for a place name outside
    # the local gazetteer. Only trust its coordinates if it actually
    # identified a location_name -- extract_query_parameters() otherwise
    # fabricates a Ratnagiri default for every message, which would
    # wrongly override the real GPS position on generic/conceptual queries.
    if GROQ_API_KEY:
        params = extract_query_parameters(user_message)
        if params.get("location_name") and params.get("latitude") is not None \
                and params.get("longitude") is not None:
            return (float(params["latitude"]), float(params["longitude"]))

    return None


# ---------------------------------------------------------------------------
# Day/time-of-day resolver for the ORCA orchestrator (/api/orchestrate)
# ---------------------------------------------------------------------------
# marine_weather_tool.py and weather_alert_tool.py previously only ever fetched
# Open-Meteo's "current" endpoint, so "is it safe to sail tomorrow morning?"
# was silently answered with right-now data. Regex-only (no OpenAI call) so
# it works even without an API key and never adds latency/quota cost to the
# common "today" case -- it just returns (0, None), which both tools treat
# identically to their pre-existing "current conditions" behavior.

_DAY_OFFSET_PATTERNS: Tuple[Tuple[re.Pattern, int], ...] = (
    (re.compile(r"\bday after tomorrow\b", re.IGNORECASE), 2),
    (re.compile(r"\btomorrow\b", re.IGNORECASE), 1),
    (re.compile(r"\b(today|right now|currently|at the moment)\b", re.IGNORECASE), 0),
)

_TIME_OF_DAY_HOURS: Tuple[Tuple[re.Pattern, int], ...] = (
    (re.compile(r"\bmorning\b", re.IGNORECASE), 8),
    (re.compile(r"\bafternoon\b", re.IGNORECASE), 14),
    (re.compile(r"\b(evening|dusk)\b", re.IGNORECASE), 18),
    (re.compile(r"\b(night|tonight)\b", re.IGNORECASE), 22),
)


def extract_target_datetime_from_message(message: str) -> Tuple[int, Optional[int]]:
    """
    Returns (day_offset, hour_24):
      - day_offset: 0 = today, 1 = tomorrow, 2 = day after tomorrow.
      - hour_24: the mentioned time of day (8/14/18/22), or None if the
        message named no time of day.

    (0, None) means "the message named no future date or time of day" --
    callers should treat that exactly like their old "current conditions"
    behavior. Any other result means the tools should fetch a genuine
    forecast for that specific day/hour instead.
    """
    day_offset = 0
    for pattern, offset in _DAY_OFFSET_PATTERNS:
        if pattern.search(message or ""):
            day_offset = offset
            break

    hour = None
    for pattern, h in _TIME_OF_DAY_HOURS:
        if pattern.search(message or ""):
            hour = h
            break

    return day_offset, hour
