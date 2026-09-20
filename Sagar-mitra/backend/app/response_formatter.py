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

AGENT_DISPLAY_NAMES = {
    "English": {
        "navigation": "Navigation & Weather", "fishing": "Fishing Zones",
        "compliance": "Legal & Boundary", "historical": "Historical Trends",
        "hazard": "Storm & Lightning Hazards", "analytics": "Ocean Analytics",
    },
    "Hindi": {
        "navigation": "नौवहन और मौसम", "fishing": "मछली पकड़ने के क्षेत्र",
        "compliance": "कानूनी और सीमा", "historical": "ऐतिहासिक रुझान",
        "hazard": "तूफान और बिजली का खतरा", "analytics": "समुद्री विश्लेषण",
    },
    "Marathi": {
        "navigation": "नौकानयन आणि हवामान", "fishing": "मासेमारी क्षेत्र",
        "compliance": "कायदेशीर आणि सीमा", "historical": "ऐतिहासिक कल",
        "hazard": "वादळ आणि वीज धोका", "analytics": "सागरी विश्लेषण",
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
