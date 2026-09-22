"""
Sagar Mitra / ORCA - Query Planner
=====================================
Replaces the old single-branch keyword router in app/graph.py with an LLM
planner that:

  1. Decomposes the user's message into the SET of specialized agents that
     should run (multi-agent fan-out) -- a compound question like "is it
     safe, and where's the nearest fishing zone" now correctly triggers
     both navigation and fishing, not whichever keyword happened to match
     first.
  2. Detects language/persona/intent in the same pass, so the rest of the
     pipeline (advisory.py) can actually localize the answer instead of the
     graph hardcoding English/Fisherman on every request.
  3. Sees the last couple of conversation turns, so a referential follow-up
     ("those same conditions", "what about tomorrow instead") can be
     resolved against what was just discussed, rather than being planned in
     isolation.

Falls back to deterministic keyword matching (the graph's old logic) if
Gemini is unavailable or the call fails for any reason, so a quota hit or a
missing key degrades the routing quality but never breaks the demo. The
fallback also carries forward the PREVIOUS turn's agent selection when the
new message matches no keyword at all -- a good guess for "and what about
X instead" style follow-ups where a fresh keyword match is unlikely.

Identical/near-identical questions asked again within a short window are
served from cache instead of spending another of the (scarce, free-tier)
Gemini calls -- see app/llm_cache.py.
"""
import json
import re
from typing import List, Optional

from google.genai import types
from app.advisory import generate_content, LITE_MODEL
from app.llm_cache import TTLCache, normalize_key

VALID_AGENTS = ("navigation", "fishing", "compliance", "historical", "hazard", "analytics", "regional")

_cache = TTLCache(ttl_seconds=300)  # short TTL -- routing decisions go stale fast in a live convo

# Deterministic fast path: these phrasings unambiguously mean "run the
# historical/chart agent" -- checked BEFORE the Gemini planning call (not
# only as a post-failure fallback like _keyword_fallback below), so a
# chart/trend/breakdown request never waits on, or gets misrouted by, a
# Gemini call at all -- faster, and immune to a planner-side quota/503
# stall. Loses referential-follow-up reasoning for these specific phrasings
# (e.g. context carried from a prior turn), which is the deliberate
# trade-off for guaranteed instant, correct routing on this query shape.
_INSTANT_HISTORICAL_KEYWORDS = (
    "pie chart", "breakdown", "distribution", "hazard categories",
    "yearly trend", "trend of", "historical",
    "sea surface temperature", "sst", "temperature trend", "yearly",
)

PLANNER_SYSTEM_PROMPT = """
You are the task-planning layer for ORCA, a marine intelligence assistant
for Indian coastal waters.

Given the recent conversation and the user's latest message (any language),
decide which specialized agents must run to answer it, and detect the
user's language/persona/intent. Respond with ONLY valid JSON, no markdown,
matching exactly this schema:

{
  "agents": [<subset of "navigation","fishing","compliance","historical","hazard","analytics","regional", at least one>],
  "language": "<name of the language the user wrote in, e.g. English, Hindi, Marathi>",
  "persona": "<one of: Fisherman, Student, Researcher, General Public>",
  "query_intent": "<short phrase describing what the user wants>"
}

Agent responsibilities:
- navigation: live wave height / sea temperature / tide, safety-to-sail check
- fishing: nearest Potential Fishing Zone + chlorophyll concentration (for a SINGLE location)
- compliance: EEZ boundary / Marine Protected Area legal checks
- historical: past trends, historical extremes, "why did X decline", graphs/charts/pie charts
- hazard: lightning / thunderstorm / cyclone risk
- analytics: deeper statistical anomaly analysis (marine heatwave, salinity anomaly,
  unusual conditions) -- pick this for "why", "unusual", "anomaly", "explain" style questions
- regional: compares MULTIPLE fishing zones/regions against each other by chlorophyll and
  SST -- pick this for "which regions/areas/zones show high chlorophyll and favorable SST",
  "best zones today", "compare fishing zones" style questions (plural regions, not one spot)

If the latest message is a REFERENTIAL follow-up ("those same conditions",
"what about tomorrow instead", "and there?") rather than a fresh, self-
contained question, infer the agents from what the conversation was just
discussing, not from the follow-up's own (likely generic) wording.

Pick every agent whose domain the question genuinely touches -- a compound
question should return multiple agents. Default to Fisherman persona and
English only if genuinely ambiguous; otherwise infer persona from tone
(technical/academic phrasing -> Researcher, curious/learning phrasing ->
Student, casual coastal-safety phrasing -> General Public).
"""


def _keyword_fallback(message: str, last_agents: Optional[List[str]] = None) -> dict:
    """Deterministic fallback used when Gemini is unavailable/fails -- the
    same keyword logic the router used before the planner existed, plus a
    carry-forward of the previous turn's agents for referential follow-ups
    that match no keyword of their own."""
    text = message.lower()
    agents: List[str] = []
    if any(k in text for k in ("legal", "law", "boundary", "restrict", "allowed",
                                "permit", "protected area", "mpa", "eez", "compliance", "violat")):
        agents.append("compliance")
    if any(k in text for k in ("wave", "safe", "weather", "sail", "venture", "condition", "morning", "tomorrow")):
        agents.append("navigation")
    if any(k in text for k in ("fish", "catch", "pfz")):
        agents.append("fishing")
    if any(k in text for k in ("lightning", "cyclone", "storm", "thunder")):
        agents.append("hazard")
    if any(k in text for k in ("when was", "highest", "lowest", "trend", "history",
                                "past", "graph", "plot", "pie chart", "distribution")):
        agents.append("historical")
    if any(k in text for k in ("why", "decline", "anomaly", "unusual", "heatwave")):
        agents.append("analytics")
    if any(k in text for k in ("which regions", "which areas", "which zones", "which fishing zones",
                                "compare zones", "compare regions", "best zones", "best regions",
                                "across the coast", "multiple zones", "several zones")):
        agents.append("regional")
    if not agents:
        # No keyword matched -- most likely a referential follow-up
        # ("those same conditions", "and what about X instead"). Keep
        # talking about whatever the previous turn was about instead of
        # defaulting to an unrelated "compliance" guess.
        agents = list(last_agents) if last_agents else ["compliance"]
    return {"agents": agents, "language": "English", "persona": "Fisherman",
            "query_intent": "general advisory"}


def plan_query(user_message: str, history: Optional[List[dict]] = None,
                last_agents: Optional[List[str]] = None) -> dict:
    """
    Returns {"agents": [...], "language": str, "persona": str, "query_intent": str}.
    `history`: recent [{"role": "user"|"assistant", "text": str}, ...] turns.
    `last_agents`: agent list from the previous turn, used as a fallback
    hint (not sent to Gemini as ground truth -- Gemini gets the real
    conversation text and reasons for itself).
    """
    text_lower = (user_message or "").lower()
    if any(kw in text_lower for kw in _INSTANT_HISTORICAL_KEYWORDS):
        return {"agents": ["historical"], "language": "English", "persona": "Fisherman",
                "query_intent": user_message}

    history = history or []
    cache_key = normalize_key(user_message, *(t["text"] for t in history[-2:]))
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        history_text = "\n".join(f"{t['role']}: {t['text']}" for t in history[-4:])
        contents = (f"Recent conversation:\n{history_text}\n\nLatest message: {user_message}"
                    if history_text else user_message)
        response = generate_content(
            # Pure classification/routing -- runs on its own quota pool (see
            # advisory.LITE_MODEL) so it never competes with the final
            # synthesizer's model for the same daily quota.
            model=LITE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
        text = (response.text or "").strip()
        text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        parsed = json.loads(match.group(0) if match else text)

        agents = [a for a in parsed.get("agents", []) if a in VALID_AGENTS]
        if not agents:
            raise ValueError("planner returned no valid agents")
        result = {
            "agents": agents,
            "language": parsed.get("language") or "English",
            "persona": parsed.get("persona") or "Fisherman",
            "query_intent": parsed.get("query_intent") or "general advisory",
        }
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        print(f"[planner] Falling back to keyword routing: {e}")
        return _keyword_fallback(user_message, last_agents)
