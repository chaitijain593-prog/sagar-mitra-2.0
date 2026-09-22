"""
Sagar Mitra - Ocean Intelligence NLP & Explanation Layer
===========================================================

This module wraps Google Gemini (gemini-2.5-flash) using the official
`google-genai` SDK to translate structured oceanographic JSON data into
persona-aware, language-localized advisories for:

    - Fishermen / Coastal Community Members
    - Students (learning mode)
    - Researchers / Technicians (expert mode)
    - General Public / Tourists

Install dependency:
    pip install google-genai

Set your API key as an environment variable before running:
    export GEMINI_API_KEY="your_key_here"        # Linux / macOS
    setx GEMINI_API_KEY "your_key_here"           # Windows

Author: Sagar Mitra Hackathon Team
"""

import os
import json
from typing import Dict, Any, Literal, Optional

from google import genai
from google.genai import types

from app.error_utils import is_quota_or_unavailable_error


# ---------------------------------------------------------------------------
# 1. API CLIENT SETUP
# ---------------------------------------------------------------------------

def get_gemini_client() -> genai.Client:
    """
    Safely initializes and returns a Gemini API client using the current key
    in the rotation (see key-rotation block below).
    """
    api_key = _current_key()
    if not api_key:
        raise EnvironmentError(
            "No Gemini API key found. Set GEMINI_API_KEY (single key) or "
            "GEMINI_API_KEYS (comma-separated, for automatic rotation when "
            "one hits its quota) in your .env file."
        )
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# 1b. MULTI-KEY ROTATION
# ---------------------------------------------------------------------------
# Put multiple free-tier keys in .env as:
#   GEMINI_API_KEYS=key_one,key_two,key_three
# (falls back to single GEMINI_API_KEY if GEMINI_API_KEYS isn't set).
# When a call fails with a quota/rate-limit error, we automatically rotate
# to the next key and retry -- no manual restart needed.

_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()] \
        or ([os.environ["GEMINI_API_KEY"]] if os.environ.get("GEMINI_API_KEY") else [])
_key_index = 0
_client: genai.Client | None = None


def _current_key() -> str | None:
    return _KEYS[_key_index] if _KEYS else None


def _rotate_key():
    global _key_index, _client
    _key_index = (_key_index + 1) % max(len(_KEYS), 1)
    _client = None  # force rebuild with the new key
    print(f"[advisory] Gemini key quota hit -- rotated to key #{_key_index + 1}/{len(_KEYS)}")


def _is_quota_error(e: Exception) -> bool:
    """True for errors where switching to the next key should help:
    quota/rate-limit hits, or this specific key being invalid/disabled."""
    msg = str(e).lower()
    return any(s in msg for s in [
        "429", "quota", "resource_exhausted", "rate limit",
        "401", "unauthenticated", "account_state_invalid",
        "service account is deleted", "service account is disabled",
        "api key not valid", "invalid api key",
    ])


def _is_permission_denied_error(e: Exception) -> bool:
    """True for 403 PERMISSION_DENIED errors from the Gemini API (e.g. the
    key/project lacks access to a model/feature, billing not enabled, or the
    project itself was denied access). This IS per-key -- confirmed live, one
    key in GEMINI_API_KEYS can be denied while another works fine -- so
    generate_content (below) rotates past it like a quota error instead of
    failing the whole request. Callers only see this surface once every key
    has been tried and denied, in which case a retry truly won't help and
    they should show a plain status message instead of the raw error."""
    msg = str(e).lower()
    return "403" in msg or "permission_denied" in msg or "permission denied" in msg


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = get_gemini_client()
    return _client


def require_gemini_key() -> None:
    """
    Strict startup check -- called from app/graph.py's create_orca_graph()
    (which app/main.py runs at import time), so a missing key fails the
    server's own startup with clear terminal instructions instead of
    starting normally and letting every request silently degrade to the
    raw-data fallback formatter ("ORCA's AI summarizer is temporarily
    busy") with no visible signal to whoever's running it.
    """
    if _KEYS:
        return
    print("=" * 72)
    print("ORCA STARTUP ERROR: No Gemini API key configured.")
    print("=" * 72)
    print("ORCA needs a Gemini API key to generate localized, persona-aware")
    print("advisories. Without one, every request will silently fall back to")
    print("the raw-data formatter (\"ORCA's AI summarizer is temporarily busy\").")
    print()
    print("To fix this:")
    print("  1. Copy backend/.env.example to backend/.env")
    print("  2. Get a free key at https://aistudio.google.com/apikey")
    print("  3. Add it to backend/.env as GEMINI_API_KEY=<your key>")
    print("     (or GEMINI_API_KEYS=key1,key2,... for automatic quota rotation)")
    print("  4. Restart the server: uvicorn app.main:app --reload")
    print("=" * 72)
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# 1c. MODEL TIERING -- keep the synthesizer's quota free of classification traffic
# ---------------------------------------------------------------------------
# Gemini's free-tier quota is scoped PER PROJECT PER MODEL (confirmed live:
# a 429 on gemini-3.6-flash did not block a call to gemini-flash-lite-latest
# in the same project/key). Mechanical, structured-output tasks -- picking
# agents, picking a data-lookup tool, extracting a lat/lon -- don't need the
# strongest model and previously competed with the user-facing synthesis
# call for the SAME model's daily quota. Routing them to a separate lite
# model gives the final localized/persona-aware advisory its own quota pool,
# so a burst of routing calls can no longer starve the one call that
# actually has to succeed in the user's language.
LITE_MODEL = "gemini-flash-lite-latest"


def generate_content(model: str, contents, config=None):
    """
    Drop-in replacement for client.models.generate_content(...) that
    automatically rotates through GEMINI_API_KEYS on quota/rate-limit OR
    permission-denied errors and retries, instead of getting permanently
    stuck on a single bad key for the rest of the process lifetime.
    """
    last_err = None
    attempts = max(len(_KEYS), 1)
    for _ in range(attempts):
        client = _get_client()
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            last_err = e
            if (_is_quota_error(e) or _is_permission_denied_error(e)) and len(_KEYS) > 1:
                _rotate_key()
                continue
            raise
    raise RuntimeError(f"All Gemini API keys exhausted/failed. Last error: {last_err}")


def generate_content_with_fallback(primary_model: str, contents, config=None,
                                    fallback_model: str = LITE_MODEL):
    """
    Tries `primary_model` first; if it fails with a quota (429) OR
    availability (503 "high demand") error, retries ONCE on `fallback_model`
    -- a separate quota pool, see LITE_MODEL -- before giving up.

    _is_quota_error() (used for key rotation, above) only recognizes 429s,
    since rotating API KEYS can't fix a 503 -- that's a whole-model outage,
    not a per-key limit. Rotating MODEL can, which is what this adds: the
    user-facing synthesis calls (synthesize_advisory, format_compliance_
    advisory) get a real second chance at producing a localized answer
    instead of immediately dropping to the raw-text fallback the moment the
    strong model has a bad moment.
    """
    try:
        return generate_content(model=primary_model, contents=contents, config=config)
    except Exception as e:
        if is_quota_or_unavailable_error(e) and primary_model != fallback_model:
            print(f"[advisory] {primary_model} unavailable ({e}); retrying on {fallback_model}")
            return generate_content(model=fallback_model, contents=contents, config=config)
        raise


# ---------------------------------------------------------------------------
# 2. PERSONA & LANGUAGE CONFIGURATION
# ---------------------------------------------------------------------------

PersonaType = Literal["Fisherman", "Student", "Researcher", "General Public"]

# Persona-specific system instructions. Each block encodes tone, vocabulary
# rules, and the required response structure, as defined by the Sagar Mitra
# communication policy.
PERSONA_SYSTEM_PROMPTS: Dict[str, str] = {
    "Fisherman": """
You are Sagar Mitra, an ocean safety assistant speaking directly to a
fisherman or coastal community member.

TONE: Empathetic, respectful, direct, and urgent whenever safety is
compromised. Practical and reassuring otherwise.

VOCABULARY RULES:
- Absolutely NO technical jargon (no "Z-score", "climatology", "thermocline",
  "standard deviation", "anomaly coefficient", etc.).
- Translate physics into plain, everyday physical descriptions instead:
  e.g. "unusually warm water", "rough / choppy seas", "calm waters",
  "strong currents", "good fishing waters nearby".

RESPONSE STRUCTURE (always use this order, with these exact section labels
translated naturally into the requested language):
1. Operational Status - one clear line: Safe to Sail / Caution / No-Go Warning
   (use an urgent tone if risk is Moderate or higher).
2. What's Happening - a short, simple explanation of current water and
   weather conditions in plain language.
3. Livelihood & Safety Advice - concrete, actionable tips: whether to go out,
   where fish are likely, what precautions to take.

Always put safety warnings first and make them impossible to miss.
""",
    "Student": """
You are Sagar Mitra, acting as a patient, encouraging ocean-science tutor for
a student learning oceanography.

TONE: Encouraging, educational, clear, and explanatory.

VOCABULARY RULES:
- You MAY use technical terms (Z-score, marine heatwave, thermocline,
  salinity anomaly, mixed layer depth) but you must gently explain what each
  one means and why it matters, as if teaching a curious learner.

RESPONSE STRUCTURE:
1. Core Concept Summary - a short, friendly overview of what the data shows
   overall.
2. Breakdown of Parameters - walk through each key metric (temperature
   anomaly, Z-score, salinity, MHW classification, PFZ status, safety risk),
   explaining what it means in accessible educational language.
3. Real-World Educational Takeaway - connect the data to a bigger-picture
   lesson (e.g. how marine heatwaves affect fish migration, why statistical
   confidence matters).
""",
    "Researcher": """
You are Sagar Mitra, functioning as a rigorous scientific reporting assistant
for a researcher or technician.

TONE: Academic, formal, data-driven, and precise.

VOCABULARY RULES:
- Use proper oceanographic and statistical nomenclature: standard deviations,
  Z-scores, p-values / statistical confidence, Hobday MHW category
  classification, thermocline / mixed layer depth, salinity anomaly (PSU),
  depth-tier context, etc.
- Do not simplify or soften terminology.

RESPONSE STRUCTURE:
1. Statistical Confidence & Baseline Metrics - report confidence level,
   depth tier, and any baseline/climatology context available in the data.
2. Multi-Factor Analysis - integrate temperature, salinity, MHW
   classification, PFZ habitat status, and coastal safety risk into a
   cohesive analytical assessment.
3. Raw Parameter Breakdown - a structured, itemized listing of all
   quantitative values (observed values, anomalies, Z-scores, wind speed,
   wave height, etc.).
""",
    "General Public": """
You are Sagar Mitra, providing a calm, informative coastal safety briefing
for a member of the general public, tourist, or coastal resident.

TONE: Informative, calm, reassuring but honest, and safety-oriented.

VOCABULARY RULES:
- Avoid commercial fishing details and deep technical jargon.
- Focus on beach safety, general weather/sea conditions, and coastal
  awareness relevant to everyday people (swimmers, beachgoers, residents).

RESPONSE STRUCTURE:
1. Current Coastal Conditions - a brief, plain-language summary of sea and
   weather state.
2. Safety Guidance - clear dos and don'ts for beach visits, swimming, or
   coastal activity today.
3. General Awareness Note - any broader context worth knowing (e.g. unusual
   warming, seasonal patterns) in accessible terms.
""",
}


# Normalization map: resolves raw client onboarding inputs (operational
# role, vessel type, experience level, free-text labels, etc.) to one of the
# valid PERSONA_SYSTEM_PROMPTS keys. Keys must be lowercase/stripped for
# lookup; unrecognized inputs safely fall back to "Fisherman".
PERSONA_ALIASES: Dict[str, PersonaType] = {
    # Fisherman / coastal worker
    "fisherman": "Fisherman", "fisher": "Fisherman", "fisherwoman": "Fisherman",
    "fishing": "Fisherman", "fishermen": "Fisherman", "angler": "Fisherman",
    "trawler operator": "Fisherman", "trawler": "Fisherman", "boat owner": "Fisherman",
    "boat operator": "Fisherman", "vessel operator": "Fisherman", "crew": "Fisherman",
    "deckhand": "Fisherman", "coastal community member": "Fisherman",
    "small-scale fisher": "Fisherman", "commercial fisher": "Fisherman",
    # Student / learner
    "student": "Student", "learner": "Student", "school student": "Student",
    "college student": "Student", "beginner": "Student", "trainee": "Student",
    # Researcher / technical
    "researcher": "Researcher", "scientist": "Researcher", "technician": "Researcher",
    "oceanographer": "Researcher", "academic": "Researcher", "analyst": "Researcher",
    "marine biologist": "Researcher", "phd": "Researcher", "expert": "Researcher",
    # General public
    "general public": "General Public", "public": "General Public",
    "tourist": "General Public", "visitor": "General Public",
    "resident": "General Public", "beachgoer": "General Public",
    "swimmer": "General Public", "citizen": "General Public",
}


def normalize_persona(raw_persona: Optional[str]) -> PersonaType:
    """
    Resolves a raw, client-supplied persona-ish string (e.g. from onboarding
    fields like operational role, vessel type, or experience level) to a
    valid PersonaType key. Exact matches against PERSONA_SYSTEM_PROMPTS keys
    are passed through as-is (case-insensitive); anything else is looked up
    in PERSONA_ALIASES; unrecognized input safely falls back to "Fisherman".
    """
    if not raw_persona or not isinstance(raw_persona, str):
        return "Fisherman"

    cleaned = raw_persona.strip().lower()

    for valid_key in PERSONA_SYSTEM_PROMPTS:
        if valid_key.lower() == cleaned:
            return valid_key  # type: ignore[return-value]

    return PERSONA_ALIASES.get(cleaned, "Fisherman")


def _build_system_instruction(persona: PersonaType, language: str) -> str:
    """
    Combines the persona-specific instruction block with a language
    directive, ensuring the final advisory is delivered natively in the
    user's requested language (not just translated word-for-word).
    """
    if persona not in PERSONA_SYSTEM_PROMPTS:
        raise ValueError(
            f"Unknown persona '{persona}'. Must be one of: "
            f"{list(PERSONA_SYSTEM_PROMPTS.keys())}"
        )

    persona_block = PERSONA_SYSTEM_PROMPTS[persona]

    language_directive = f"""
LANGUAGE REQUIREMENT:
Write your entire response natively and fluently in {language}. Do not
mix in English unless {language} itself commonly borrows a term (e.g.
technical/scientific words for the Researcher persona may stay in English
where that is standard practice). Use natural, locally appropriate coastal
terminology, not stiff literal translation. Do not add commentary about
these instructions themselves - respond only with the advisory content.

FORMATTING REQUIREMENT:
Never use LaTeX notation (no $...$, no \\Delta, \\times, etc.) and never use
markdown syntax (no **bold**, no # headers, no backticks). Write everything
in plain conversational text, including numbers and units (e.g. write
"Z = -2.12" and "delta D20 = -660.6 m" directly as plain text, not wrapped
in math delimiters).
"""

    return persona_block.strip() + "\n\n" + language_directive.strip()


# ---------------------------------------------------------------------------
# 3. CORE GENERATION FUNCTION
# ---------------------------------------------------------------------------

def generate_sagar_mitra_advisory(
    json_payload: Dict[str, Any],
    persona: PersonaType,
    language: str = "English",
    model: str = "gemini-3.6-flash",
) -> str:
    """
    Generates a persona-aware, localized ocean advisory from structured
    oceanographic JSON data using Gemini.

    Args:
        json_payload: Dict matching the Sagar Mitra oceanographic schema,
            e.g.:
            {
                "metadata": {...},
                "temperature_analysis": {...},
                "salinity_analysis": {...},
                "coastal_safety_layer": {...},
                "fishing_habitat_layer": {...}
            }
        persona: One of "Fisherman", "Student", "Researcher", "General Public".
        language: Target output language, e.g. "English", "Hindi", "Marathi".
        model: Gemini model name (defaults to the free/fast gemini-2.5-flash).

    Returns:
        A formatted advisory string, ready to display to the end user.
    """
    system_instruction = _build_system_instruction(persona, language)

    # The JSON payload is passed as the user turn; the model is instructed
    # (via system_instruction) on how to interpret and phrase it.
    query_intent = json_payload.get("query_context", {}).get("query_intent", "general advisory")
    user_prompt = (
    f"The user specifically asked about: \"{query_intent}\".\n"
    "Answer THAT question directly and concisely first, in 2-4 sentences. "
    "Only include the full structured breakdown (all sections/metrics) if the "
    "user's question was broad/general — not if they asked about one specific thing.\n\n"
    "Here is the full sensor data for context:\n\n"
    f"```json\n{json.dumps(json_payload, indent=2, ensure_ascii=False)}\n```"
)

    response = generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,  # low-ish temperature: factual, consistent tone
            max_output_tokens=2048,
        ),
    )

    return response.text or ""


def synthesize_advisory(raw_report: str, persona: str = "Fisherman", language: str = "English",
                         user_message: str = "", history_text: str = "",
                         model: str = "gemini-3.6-flash") -> str:
    """
    Combines the raw findings from one or more ORCA specialist agents
    (already live, real data -- wave height, PFZ location, boundary status,
    historical trends, hazard alerts, statistical anomalies) into ONE
    coherent, persona/language-aware advisory.

    Unlike plain_gemini_answer (which assumes no real data was found and
    must hedge accordingly), this assumes real data WAS gathered by the
    dispatch step and must be reflected honestly, not hedged as "general
    guidance" or re-derived from the model's own background knowledge.
    """
    persona = normalize_persona(persona)
    persona_block = PERSONA_SYSTEM_PROMPTS[persona]
    system_instruction = (
        persona_block.strip() + "\n\n"
        f"LANGUAGE REQUIREMENT: Write your entire response natively and fluently in {language}. "
        "Do not mix in English unless that language commonly borrows a term for something.\n\n"
        "GROUNDING: The data below was just gathered live by ORCA's specialist agents for this "
        "exact query. Base your answer on it -- never claim you lack real-time data, and never "
        "invent a number or fact that isn't in it. If a section reports an error or missing "
        "data, say so honestly rather than filling the gap yourself.\n\n"
        "TEMPORAL CONSISTENCY: If the data below mixes a FUTURE forecast (e.g. wave/weather "
        "conditions for 'tomorrow') with a section explicitly marked as TODAY's CURRENT/LIVE "
        "reading (e.g. a PFZ/chlorophyll note saying so), you MUST preserve that distinction "
        "clearly in your answer -- state plainly which figures are the future forecast and "
        "which are today's live reading. Never imply the current/live figures are themselves "
        "a forecast for that future time.\n\n"
        "FORMATTING: Plain text only, no markdown (no **bold**, no # headers, no backticks), "
        "no LaTeX ($...$)."
    )
    history_block = f"Conversation so far:\n{history_text}\n\n" if history_text else ""
    user_prompt = (
        f"{history_block}The user just asked: \"{user_message}\"\n\n"
        f"Raw data gathered by ORCA's specialist agents:\n{raw_report}\n\n"
        "Answer the user's actual question directly first, then mention any other relevant "
        "findings from the data above."
    )
    response = generate_content_with_fallback(
        primary_model=model, contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction, temperature=0.4, max_output_tokens=2048,
        ),
    )
    return response.text or raw_report


def plain_gemini_answer(user_message: str, persona: str = "General Public",
                         language: str = "English", model: str = "gemini-3.6-flash") -> str:
    """
    Fallback path: used when we don't have enough real nearby ocean data to
    run the statistical engine honestly. Answers directly from Gemini's own
    knowledge instead of fabricating statistics, but stays in Sagar Mitra's
    voice/persona/language.
    """
    persona = normalize_persona(persona)
    system_instruction = (
        f"You are Sagar Mitra, an ocean-intelligence assistant for the "
        f"Maharashtra coast. Answer the user's question as best you can in "
        f"{language}, in a tone appropriate for a {persona}. You do NOT have "
        f"specific real-time sensor data for this exact query, so answer "
        f"from general oceanographic/coastal knowledge, and briefly note "
        f"that this is general guidance, not a live sensor-based reading.\n\n"
        f"FORMATTING: Plain text only. Never use markdown (no **bold**, no "
        f"# headers, no bullet asterisks) and never use LaTeX ($...$). Use "
        f"blank lines between points/paragraphs instead of markdown lists."
    )
    response = generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.5,
            max_output_tokens=2048,
        ),
    )
    return response.text or ""


def format_compliance_advisory(raw_report: str, persona: str = "Fisherman",
                                language: str = "English", model: str = "gemini-3.6-flash") -> str:
    """
    Strict, grounded formatter for maritime boundary / MPA compliance checks.

    Compliance findings are legal/safety facts computed deterministically by
    boundary_toool.check_maritime_boundary. This function's only job is to
    phrase that exact finding for the user in their language/persona tone --
    unlike plain_gemini_answer, it must NEVER fall back on general knowledge
    or invent any detail (regulation names, distances, other MPA names,
    penalties, legal citations) that isn't literally present in raw_report.
    """
    persona = normalize_persona(persona)
    system_instruction = (
        f"You are Sagar Mitra's maritime compliance module, writing for a "
        f"{persona} in {language}.\n\n"
        "STRICT GROUNDING RULES (must never be broken):\n"
        "1. Base your entire answer ONLY on the exact facts in the Compliance "
        "Report below. Do not add, infer, or guess any detail that is not "
        "explicitly stated there - no invented regulation names or article "
        "numbers, no made-up distances, no other Marine Protected Area names, "
        "no penalty amounts, no legal citations, and no general oceanographic "
        "knowledge that isn't in the report.\n"
        "2. If the report is marked UNVERIFIED or says boundary data is "
        "unavailable/missing, you MUST tell the user their compliance status "
        "could not be confirmed and advise caution. Never state or imply a "
        "definite 'safe' or 'legal' status in that case.\n"
        "3. If you are unsure whether something is stated in the report, "
        "leave it out rather than guessing.\n\n"
        "FORMATTING: Plain text only, no markdown, no LaTeX. Lead with the "
        "compliance status, then any necessary safety/legal action."
    )
    response = generate_content_with_fallback(
        primary_model=model,
        contents=f"Compliance Report:\n{raw_report}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,  # deterministic, factual - no creative embellishment
            max_output_tokens=1024,
        ),
    )
    # If Gemini returns nothing, fall back to the raw factual finding itself
    # rather than an empty response - never silently drop a compliance result.
    return response.text or raw_report