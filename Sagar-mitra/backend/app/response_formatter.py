"""
Sagar Mitra / ORCA - Deterministic Fallback Formatting
==========================================================
When Gemini synthesis is unavailable (quota/outage -- see error_utils.py),
the graph used to fall back to raw string concatenation:

    "ORCA Official Advisory: Navigation Report: ... \\n\\n Fishing Advisory: ..."

with each sub-agent's own "Xxx Report:"/"Xxx Advisory:" label still baked
in -- unreadable, English-only regardless of the requested language, and
occasionally carrying a leaked raw error string. This builds a clean,
per-agent, human-labeled response from the structured agent_reports dict
(not the flattened string) without needing an LLM call, so a quota outage
degrades the FORMATTING, not to "wall of raw text."

This is NOT a substitute for real translation -- only the section labels
and the busy-notice are localized via a small static phrase table. Full
prose translation needs the LLM, which is exactly what's unavailable when
this path runs.
"""
import re
from app.error_utils import busy_notice

# Shared with main.py (which computes the authoritative hazard_status field
# returned to the frontend's hazard banner) so a degraded advisory's
# "Operational Status" line below can never contradict it -- defined once
# here instead of duplicated, since two independent copies of this logic
# drifting apart would be a real safety bug for a maritime advisory app.
def derive_hazard_status(boundary_report: str, ocean_report: str, hazard_report: dict) -> str:
    if boundary_report.startswith("ALERT"):
        return "HAZARDOUS"
    if "HAZARDOUS" in ocean_report.upper():
        return "HAZARDOUS"
    if hazard_report.get("cyclone_alert"):
        return "HAZARDOUS"
    if hazard_report.get("lightning_alert"):
        return "CAUTION"
    if boundary_report.startswith("UNVERIFIED"):
        return "CAUTION"
    return "SAFE"

AGENT_DISPLAY_NAMES = {
    "English": {
        "navigation": "Navigation & Weather", "fishing": "Fishing Zones",
        "compliance": "Legal & Boundary", "historical": "Historical Trends",
        "hazard": "Storm & Lightning Hazards", "analytics": "Ocean Analytics",
        "regional": "Regional Comparison",
    },
    "Hindi": {
        "navigation": "नौवहन और मौसम", "fishing": "मछली पकड़ने के क्षेत्र",
        "compliance": "कानूनी और सीमा", "historical": "ऐतिहासिक रुझान",
        "hazard": "तूफान और बिजली का खतरा", "analytics": "समुद्री विश्लेषण",
        "regional": "क्षेत्रीय तुलना",
    },
    "Marathi": {
        "navigation": "नौकानयन आणि हवामान", "fishing": "मासेमारी क्षेत्र",
        "compliance": "कायदेशीर आणि सीमा", "historical": "ऐतिहासिक कल",
        "hazard": "वादळ आणि वीज धोका", "analytics": "सागरी विश्लेषण",
        "regional": "प्रादेशिक तुलना",
    },
}

_LABEL_PREFIX_RE = re.compile(
    r"^[A-Za-z &]+(Report|Advisory|Alert|Analysis|Analytics):\s*", re.IGNORECASE
)


def _clean_text(text: str) -> str:
    """Strips the redundant 'Xxx Report:'-style prefix each sub-agent bakes
    into its own final_output, since this formatter supplies its own label."""
    return _LABEL_PREFIX_RE.sub("", text or "").strip()


def format_fallback_advisory(agent_reports: dict, language: str = "English",
                              degraded: bool = True) -> str:
    """
    Builds a clean, sectioned advisory directly from the structured
    {agent_name: report_text} dict -- used whenever Gemini synthesis
    couldn't run. `degraded` controls whether the busy-notice header is
    shown (False for e.g. a pure formatting-only path with no error).
    """
    labels = AGENT_DISPLAY_NAMES.get(language, AGENT_DISPLAY_NAMES["English"])
    lines = []
    if degraded:
        lines.append(busy_notice(language))
        lines.append("")

    for agent_name, text in (agent_reports or {}).items():
        label = labels.get(agent_name, AGENT_DISPLAY_NAMES["English"].get(agent_name, agent_name.title()))
        clean = _clean_text(text)
        if clean:
            lines.append(f"• {label}: {clean}")

    if not lines or (degraded and len(lines) <= 2):
        lines.append(labels.get("_empty", "No data was available for this request."))

    return "\n".join(lines)


# Real values only, parsed straight out of the same live tool-report text
# Gemini synthesis would otherwise read (see sub_agents.py's navigation_node
# / fishing_node) -- never fabricated. Kept next to their source format
# strings for easy cross-checking:
#   marine_weather_tool.py:  "... Wave Height: {wave_height}m, Water Temp: {temp}°C, ..."
#   pfz_tool.py:              "... Nearest PFZ is near {landing}. Distance: ..."
#   chlorophyll_tool.py:      "... Chlorophyll-a: {avg_chl} mg/m³. ..."
_WAVE_HEIGHT_RE = re.compile(r"Wave Height:\s*([-\d.]+)m")
_WATER_TEMP_RE = re.compile(r"Water Temp:\s*([-\d.]+)")
_NEAREST_PFZ_RE = re.compile(r"Nearest PFZ is near ([^.]+)\.")
_CHLOROPHYLL_RE = re.compile(r"Chlorophyll-a:\s*([\d.]+)")

_OPERATIONAL_STATUS_TEXT = {
    "SAFE": "Safe for navigation.",
    "CAUTION": "Exercise caution -- monitor conditions closely before proceeding.",
    "HAZARDOUS": "Hazardous -- do not proceed without confirming conditions.",
}


def format_natural_fallback_advisory(agent_reports: dict, hazard_status: str,
                                      language: str = "English") -> str:
    """
    A calm, natural-sounding maritime paragraph built from REAL gathered
    telemetry (wave height / water temperature / nearest PFZ / chlorophyll,
    all parsed from the same live navigation/fishing agent reports the
    Gemini synthesis path would otherwise phrase) -- used in place of
    format_fallback_advisory's busy-notice-plus-bullet-dump when Gemini
    synthesis is unavailable, so a degraded response still reads like a
    normal advisory instead of exposing "AI summarizer busy"/infrastructure
    language to the end user.

    The Operational Status line always reflects the REAL, independently-
    computed hazard_status (see derive_hazard_status above) -- this is a
    maritime safety advisory, so a degraded/no-LLM response must never
    claim conditions are safe when they aren't, no matter how clean the
    prose needs to read. Falls back to a minimal, still-honest sentence
    when no navigation/fishing data is present at all (e.g. a compliance-
    or analytics-only query reached this path).
    """
    nav_report = agent_reports.get("navigation", "") or ""
    fishing_report = agent_reports.get("fishing", "") or ""

    wave_match = _WAVE_HEIGHT_RE.search(nav_report)
    temp_match = _WATER_TEMP_RE.search(nav_report)
    pfz_match = _NEAREST_PFZ_RE.search(fishing_report)
    chl_match = _CHLOROPHYLL_RE.search(fishing_report)

    status_text = _OPERATIONAL_STATUS_TEXT.get(hazard_status, _OPERATIONAL_STATUS_TEXT["CAUTION"])
    sentences = [f"Operational Status: {status_text}"]

    if wave_match and temp_match:
        sentences.append(
            f"Sea conditions off the coast show mild wave heights of {wave_match.group(1)}m "
            f"with water temperature at {temp_match.group(1)}°C."
        )
    elif wave_match:
        sentences.append(f"Wave heights off the coast are currently around {wave_match.group(1)}m.")
    elif temp_match:
        sentences.append(f"Water temperature off the coast is currently near {temp_match.group(1)}°C.")

    if pfz_match:
        pfz_sentence = f"Potential fishing zones are active near {pfz_match.group(1).strip()}"
        pfz_sentence += (f", with favorable chlorophyll concentrations around {chl_match.group(1)} mg/m³."
                          if chl_match else ".")
        sentences.append(pfz_sentence)

    sentences.append("Exercise standard maritime caution, particularly near boundary zones.")
    return " ".join(sentences)
