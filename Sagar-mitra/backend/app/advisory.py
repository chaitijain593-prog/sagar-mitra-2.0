"""
Sagar Mitra - Ocean Intelligence NLP & Explanation Layer
===========================================================

This module uses the official OpenAI Python SDK to translate structured
oceanographic JSON data into
persona-aware, language-localized advisories for:

    - Fishermen / Coastal Community Members
    - Students (learning mode)
    - Researchers / Technicians (expert mode)
    - General Public / Tourists

Install dependency:
    pip install openai

Set GROQ_API_KEY in the environment or backend/.env. OPENAI_API_KEY is
also accepted for compatibility with an existing local setup.

Author: Sagar Mitra Hackathon Team
"""

import re
import os
from types import SimpleNamespace
from typing import Dict, Any, Literal, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load backend/.env when running from a different working directory.
load_dotenv()
if not (os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")):
    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_MODEL = "openai/gpt-oss-120b"
OPENAI_TIMEOUT_SECONDS = 30
_openai_client = (
    OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL, timeout=OPENAI_TIMEOUT_SECONDS)
    if GROQ_API_KEY else None
)


def get_openai_client() -> OpenAI:
    """Return the shared client or fail clearly when configuration is missing."""
    if _openai_client is None:
        raise EnvironmentError("GROQ_API_KEY (or legacy OPENAI_API_KEY) is not configured in the environment or backend/.env.")
    return _openai_client


def require_openai_key() -> None:
    """Keep startup available; OpenAI-backed requests fail clearly without a key."""
    if _openai_client is None:
        print("[ORCA LLM ERROR] GROQ_API_KEY is not configured.")


def _is_quota_error(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    message = str(error).lower()
    return status == 429 or any(token in message for token in ("429", "rate limit", "quota", "insufficient_quota"))


def _is_permission_denied_error(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    message = str(error).lower()
    return status == 403 or any(token in message for token in ("403", "permission_denied", "permission denied", "forbidden"))


def generate_content(
    model: str,
    contents,
    *,
    system_instruction: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    response_format: dict | None = None,
    tools: list | None = None,
    tool_choice=None,
):
    """Call OpenAI Chat Completions and propagate API errors to the caller."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    if isinstance(contents, list) and all(isinstance(item, dict) for item in contents):
        messages.extend(contents)
    else:
        messages.append({"role": "user", "content": str(contents)})
    kwargs = {
        "model": model or OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if tools is not None:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    completion = get_openai_client().chat.completions.create(**kwargs)
    message = completion.choices[0].message
    return SimpleNamespace(text=message.content or "", completion=completion, message=message)


def _query_language(user_message: str, language: str | None = None) -> str:
    """Return the response language code, recognizing Hindi and Hinglish."""
    message = str(user_message or "")
    if re.search(r"[\u0900-\u097f]", message):
        return "hi"
    hinglish_terms = {
        "aaj", "samundar", "mausam", "kaisa", "hai", "macchli", "machli",
        "kidhar", "jaana", "kare", "batao", "paani", "kaisi", "machhli",
        "lahar", "lehren", "jaun",
    }
    if set(re.findall(r"[a-z]+", message.lower())) & hinglish_terms:
        return "hi"
    if language and str(language).lower() in {"hi", "hindi"}:
        return "hi"
    return "en"


PRIMARY_MODEL = OPENAI_MODEL
LITE_MODEL = OPENAI_MODEL


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

# Vessel/operator-category system instructions (Task 4: Persona Vocabulary
# Reconciliation). Declared once at onboarding (see main.py's
# reconcile_persona_key) and orthogonal to PERSONA_SYSTEM_PROMPTS above --
# that dict picks the AUDIENCE communication style (tone/vocabulary level,
# detected live from message tone by planner.py), while this one picks the
# OPERATIONAL vocabulary/focus (what kind of vessel, what hazards matter)
# layered on top of it in the same system instruction.
VESSEL_PERSONA_SYSTEM_PROMPTS: Dict[str, str] = {
    "artisanal_coastal": """
VESSEL OPERATION CONTEXT: Traditional artisanal/coastal fisher, typically
operating a small non-motorized or small-outboard (OBM) craft in shallow
nearshore waters. When relevant, frame safety/operational guidance around
shallow-water hazards, small-outboard-motor limits, and local coastal
landmarks rather than deep-water commercial shipping concerns.
""",
    "mechanized_trawler": """
VESSEL OPERATION CONTEXT: Mechanized trawler operator. When relevant, frame
safety/operational guidance around trawl-net operating depth, winch/gear
clearance, diesel fuel reserves for the return trip, and proximity to
offshore shipping lanes.
""",
    "deep_sea_commercial": """
VESSEL OPERATION CONTEXT: Deep-sea commercial longliner, operating far from
shore for extended periods. When relevant, frame safety/operational guidance
around long-range weather systems, international maritime boundaries, and
commercial fishing quotas rather than nearshore concerns.
""",
    "coastal_allied": """
VESSEL OPERATION CONTEXT: Aquaculture/coastal allied worker (cage culture,
shore-based operations). When relevant, frame safety/operational guidance
around near-shore aquaculture infrastructure, tide timings, and localized
storm surge risk.
""",
}


def _vessel_context_block(vessel_persona: str) -> str:
    """Empty string for an unrecognized/missing key -- reconcile_persona_key
    in main.py is the layer responsible for falling back to a valid key, so
    this stays a quiet no-op rather than raising, matching _build_system_
    instruction's stricter contract only for the (required) audience persona."""
    return VESSEL_PERSONA_SYSTEM_PROMPTS.get(vessel_persona, "").strip()


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
Write your entire response natively and fluently in {language}, using
{language}'s own native script (e.g. Devanagari for Hindi/Marathi, Bengali
script for Bengali, Kannada script for Kannada, Gurmukhi for Punjabi, Odia
script for Odia, Tamil script for Tamil). Never romanize or transliterate
into Latin characters. Do not mix in English unless {language} itself
commonly borrows a term (e.g. technical/scientific words for the Researcher
persona may stay in English where that is standard practice). Use natural,
locally appropriate coastal terminology, not stiff literal translation. Do
not add commentary about these instructions themselves - respond only with
the advisory content.

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
    model: str = PRIMARY_MODEL,
) -> str:
    """
    Generates a persona-aware, localized ocean advisory from structured
    oceanographic JSON data using OpenAI.

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
        model: OpenAI model name (defaults to PRIMARY_MODEL).

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
        model=model, contents=user_prompt, system_instruction=system_instruction,
        temperature=0.3, max_tokens=2048,
    )

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("OpenAI returned an empty advisory for the live sensor data.")
    return text


def synthesize_advisory(raw_report: str, persona: str = "Fisherman", language: str = "English",
                         user_message: str = "", history_text: str = "",

                         model: str = PRIMARY_MODEL, vessel_persona: str = "artisanal_coastal") -> str:

                         

    """
    Combines the raw findings from one or more ORCA specialist agents
    (already live, real data -- wave height, PFZ location, boundary status,
    historical trends, hazard alerts, statistical anomalies) into ONE
    coherent, persona/language-aware advisory.

    Unlike plain_openai_answer (which assumes no real data was found and
    must hedge accordingly), this assumes real data WAS gathered by the
    dispatch step and must be reflected honestly, not hedged as "general
    guidance" or re-derived from the model's own background knowledge.
    """

    language = "Hindi" if _query_language(user_message, language) == "hi" else "English"
    persona_block = PERSONA_SYSTEM_PROMPTS.get(persona, PERSONA_SYSTEM_PROMPTS["Fisherman"])
    vessel_block = _vessel_context_block(vessel_persona)

    persona = normalize_persona(persona)
    persona_block = PERSONA_SYSTEM_PROMPTS[persona]

    system_instruction = (
        persona_block.strip() + "\n\n"
        + (vessel_block + "\n\n" if vessel_block else "")
        + f"LANGUAGE REQUIREMENT: Write your entire response natively and fluently in {language}, "
        f"using {language}'s own native script (e.g. Devanagari for Hindi/Marathi, Bengali script "
        "for Bengali, Kannada script for Kannada, Gurmukhi for Punjabi, Odia script for Odia, Tamil "
        "script for Tamil). Never romanize or transliterate into Latin characters. Do not mix in "
        "English unless that language commonly borrows a term for something.\n\n"
        "QUERY-LANGUAGE RULE: Detect the language of the user's latest question. If it contains "
        "Hindi, Romanized Hinglish, or Devanagari characters, generate the ENTIRE advisory in "
        "fluent Hindi using clean Devanagari script. If it is English, respond in English. "
        "Do not answer Hindi in Romanized script.\n\n"
        "LIVE DATA RULE: Generate the advisory strictly from the [LIVE VESSEL & OCEANOGRAPHIC "
        "TELEMETRY] block and the agent data provided. Incorporate the exact numerical readings; "
        "never invent or estimate values. Do not use canned disclaimers or template prose. If a "
        "measurement is marked unavailable, state that it is unavailable.\n\n"
        "QUERY-LANGUAGE REQUIREMENT: Answer directly in the language used by the user's latest "
        "question. If the question is Hindi or Hinglish (Hindi written in Latin letters), answer "
        "in natural Hindi using Devanagari. If it is English, answer in English. Use the requested "
        "language above when the question itself does not make its language clear.\n\n"
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
    response = generate_content(
        model=model, contents=user_prompt, system_instruction=system_instruction,
        temperature=0.3, max_tokens=2048,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("OpenAI returned an empty advisory for the live telemetry.")
    return text


def plain_openai_answer(user_message: str, persona: str = "General Public",
                        language: str = "English", model: str = PRIMARY_MODEL) -> str:
    """
    General-knowledge path used when nearby ocean data is not available.
    Answers directly from OpenAI's own
    knowledge instead of fabricating statistics, but stays in Sagar Mitra's
    voice/persona/language.
    """
    language = "Hindi" if _query_language(user_message, language) == "hi" else "English"
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
        model=model, contents=user_message, system_instruction=system_instruction,
        temperature=0.3, max_tokens=2048,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("OpenAI returned an empty response for the user query.")
    return text


def format_compliance_advisory(raw_report: str, persona: str = "Fisherman",

                                language: str = "English", model: str = PRIMARY_MODEL,
                                vessel_persona: str = "artisanal_coastal") -> str:

                                

    """
    Strict, grounded formatter for maritime boundary / MPA compliance checks.

    Compliance findings are legal/safety facts computed deterministically by
    boundary_toool.check_maritime_boundary. This function's only job is to
    phrase that exact finding for the user in their language/persona tone --
    unlike plain_openai_answer, it must NEVER fall back on general knowledge
    or invent any detail (regulation names, distances, other MPA names,
    penalties, legal citations) that isn't literally present in raw_report.
    """

    vessel_block = _vessel_context_block(vessel_persona)

    persona = normalize_persona(persona)
    system_instruction = (
        f"You are Sagar Mitra's maritime compliance module, writing for a "
        f"{persona} in {language}, using {language}'s own native script (e.g. Devanagari for "
        "Hindi/Marathi, Bengali script for Bengali, Kannada script for Kannada, Gurmukhi for "
        "Punjabi, Odia script for Odia, Tamil script for Tamil) -- never romanized/transliterated "
        "into Latin characters.\n\n"
        + (vessel_block + "\n\n" if vessel_block else "")
        + "STRICT GROUNDING RULES (must never be broken):\n"
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
    response = generate_content(
        model=model, contents=f"Compliance Report:\n{raw_report}",
        system_instruction=system_instruction, temperature=0.3, max_tokens=1024,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("OpenAI returned an empty compliance advisory.")
    return text
