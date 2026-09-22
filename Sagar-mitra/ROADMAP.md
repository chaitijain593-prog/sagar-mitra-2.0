# Sagar Mitra 2.0 / ORCA — Gap Analysis & 48-Hour Execution Plan

Audited against the live codebase on `main` (commit `18b1c50`) on 2026-09-22. This replaces
guesswork with what is actually running: every claim below is backed by a file:line reference.
**No working code was rewritten to produce this document.**

Stack confirmed from `backend/requirements.txt`: FastAPI, LangGraph (planner/dispatch/synth graph
only — no chains/agents/memory from `langchain`), scikit-learn/XGBoost + `shap`, `google-genai`
(Gemini) for all LLM/STT/TTS, `reportlab`, `shapely`/`gsw`. **No `torch`, `tensorflow`, `ollama`,
`llama-cpp`, or `whisper`/Bhashini package is installed anywhere.** That single fact rules out real
PINNs, a local/offline LLM fallback, and non-Gemini voice — see Section A for what that means for
the plan.

---

## Section A — Gap Analysis & Dossier

Status legend: **Verified Complete** (works end-to-end, frontend included) · **Partially
Implemented** (real backend logic exists but is stubbed, mislabeled, or not wired to the UI) ·
**Not Started** (no code, or schema-only dead code).

### The 10 Core Features

| # | Feature | Status | Files / Functions | Gap | Est. |
|---|---|---|---|---|---|
| 1 | Regional Language Voice I/O | Partial | `app/voice.py:45` `SUPPORTED_LANGUAGES` (Marathi/Tamil/Telugu/Gujarati/Malayalam/English); `transcribe_and_translate()` L74, `synthesize_speech()` L114; wired to `POST /api/voice/orchestrate` (`main.py:448`), mic button in `index.html:218`/`script.js` | 100% Gemini-cloud, not Bhashini/Whisper — no offline path exists or is installable without new deps. Hindi/Bengali/Kannada/Punjabi/Odia missing despite being in `error_utils.py`'s translation table. | 2h (add missing languages to `SUPPORTED_LANGUAGES` + prompt table; rebrand as "Gemini-powered", not Bhashini) |
| 2 | Weather-aware A* safe route | **Verified Complete** | `app/route_planner.py`: `_astar()` L169, `_CostGrid` L82, wave penalty `move_cost()` L155 (`HAZARD_CELL_PENALTY=40.0`), MPA avoidance L68-79 | No hard EEZ-crossing block (EEZ is compliance-only, not a routing obstacle) and no storm-*vector* field, just static wave sampling. | 3h to add EEZ as a hard-blocked polygon in `_CostGrid`, same pattern as MPA |
| 3 | Proactive IMBL/geofence siren | **Verified Complete** | `app/boundary_toool.py:112` `distance_to_nearest_boundary_km()`; `GET /api/geofence-check` (`main.py:228`); frontend siren `script.js` `pollGeofence()`/`playGeofenceSiren()` | No return-heading vector (bearing back to safe water) is computed anywhere. | 2h: add haversine bearing calc to `boundary_toool.py`, surface in geofence-check response + banner text |
| 4 | Offline Morning Dispatch (PDF+audio) | Partial | `app/dispatch.py:233` `generate_morning_dispatch()` — real PDF (reportlab, `_render_pdf` L136) + real WAV (`_render_audio` L215); `POST /api/dispatch/generate` (`main.py:553`) | **Zero frontend hookup** — no button, no call in `script.js` (0 matches for "dispatch"). Backend is done. | 1.5h: one button + fetch + `<a download>`/`<audio>` render |
| 5 | Explainable AI / SHAP | **Verified Complete** | `app/pfz_ml.py:79` `_get_explainer()` (real `shap.TreeExplainer`), `_compute_shap_attributions()` L112; rendered by `script.js` `renderShapChart()` for Researcher persona | None — this is done. | 0h |
| 6 | "Blackout Mode" local LLM fallback | **Not Started** | `app/blackout_cache.py` only caches HTTP sensor responses (Open-Meteo etc.), never LLM calls; no Ollama/llama.cpp anywhere in `requirements.txt` or code | No local model exists or can exist without adding a multi-GB dependency + quantized weights in 48h. On Gemini failure the system already falls back to `app/response_formatter.py`'s deterministic templates. | **Descope**: rename this feature in the demo to "Deterministic Offline Advisory Mode" and point at `response_formatter.py`, which is real. True Ollama integration is out of scope for 48h (needs model download + inference wiring + testing) — flag to judges as a stretch goal, don't fake it. |
| 7 | Crowdsourced hazard mesh (24h TTL) | **Not Started (dead code exists)** | `app/db_store.py:43` `hazard_mesh` table + `insert_hazard_point()`/`get_hazard_mesh()` (L117-141) — **never called from `main.py` or anywhere else** | No `POST`/`GET` endpoint, no TTL cleanup job, no map UI for reporting or viewing hazards. | 5h: `POST /api/hazard` + `GET /api/hazard/mesh` endpoints, TTL filter in the SQL query (`WHERE timestamp > now-24h`), Leaflet click-to-report + hazard icon layer in `script.js` |
| 8 | Catch-to-market price arbitrage | **Not Started** | No matches for "price"/"market"/"auction"/"fuel" anywhere | Needs a harbor price dataset (none exists) and a fuel-cost model. | **Descope for 48h** — no data source lined up; building one from scratch (even mocked) plus UI is 6-8h that the team doesn't have slack for. Cut or fake with 3 static harbor price points if a judge-facing demo needs it. |
| 9 | NL Text-to-SQL deep ocean query engine | Partial (not true SQL) | `app/historical.py` — Gemini function-calling over 4 fixed pandas functions (`TOOLS` L183), not NL→SQL text; `app/db.py:127` `query_argo_bbox()` is a real parameterized SQL function but is **never exposed to the NLP layer** | Need a Gemini prompt that emits SQL text (or at minimum a 5th function-call tool that maps to `query_argo_bbox`) and a safe execution path (read-only connection, param binding — already present in `db.py`). | 4h: add `query_argo_bbox` as an 8th tool in `historical.py`'s `TOOLS` list + a LangGraph node exposing it under a "Text-to-SQL" agent label for the demo narrative |
| 10 | Anchor drift sentry | **Not Started** | No matches for "anchor"/"drift" (anchor sense) anywhere | Needs: a stored anchor-point + radius, a poll comparing current GPS to it, and a UI toggle. Structurally identical to the existing geofence-poll pattern (`pollGeofence` in `script.js`), just a different center/radius. | 3h: reuse `pollGeofence()`'s polling skeleton with a user-set anchor point + configurable radius in `localStorage`, alarm via existing `playGeofenceSiren()` |

### Scientific & SOS Enhancements

| # | Feature | Status | Files | Gap | Est. |
|---|---|---|---|---|---|
| 11 | PINNs (Navier-Stokes / Argo interpolation) | **Not Started** | none; `route_planner.py`'s wave interpolation is plain inverse-distance-weighting, not a neural net | **No PyTorch/TensorFlow installed.** A real PINN (physics-loss network) cannot be trained, validated, and integrated in 48h even if the dependency were added today — this is a multi-week research task, not a sprint task. | **Descope entirely.** Keep the honest framing in the pitch: "statistically-validated anomaly detection (`statistical_engine.py`, real Z-tests/KS-tests/TEOS-10) today; PINN-based physics modeling is the named next milestone." Do not fabricate a PINN badge on the dashboard. |
| 12 | Causal reasoning / "what-if" engine | **Not Started** | No matches for "causal"/"counterfactual" | Same issue as #11 — a real causal graph model is a research task. | **Descope.** If a "what-if" UI affordance is wanted for demo polish, fake it client-side as a parameter slider that re-calls the existing SHAP-backed `predict_pfz_confidence()` with perturbed inputs (honest: it's sensitivity analysis on the real ML model, not causal inference) — 3h, and label it accurately in the UI copy. |
| 13 | Maritime boundary escalation to Coast Guard | **Not Started** | `boundary_toool.check_maritime_boundary()` only returns a text ALERT string; no outbound webhook/SMS/email | No real Coast Guard integration exists to call (this is an authorization problem, not just code). | 2h: add a `POST /api/escalate` stub endpoint that logs to `sos_events` (reuse `db.insert_sos_event`) and clearly labels itself "simulated escalation — logs to ops queue" in the response, matching what a judge would expect from a hackathon blueprint. |
| 14 | Emergency SOS / VHF/satellite gateway | Partial | `POST /api/sos` (`main.py:259`) + `db.insert_sos_event()`; real "Initiate SOS" button `index.html:247`/`triggerMayday()` in `script.js` | No radio protocol integration (out of scope — needs real hardware). | 1h: polish the SOS confirmation UI (`script.js:603-641` has two near-duplicate `triggerMayday`/`startGeofenceMonitor` implementations with dead template-literal bugs — `` `/api/geofence-check?lat=\({coords.lat}&lon=\){coords.lon}` `` is broken string interpolation; **fix, don't rewrite**, the escaped `\(` / `\)` around L726) |

### ORCA Suggestions & Explorers

| # | Feature | Status | Files | Gap | Est. |
|---|---|---|---|---|---|
| 15 | Multi-persona user flow | Partial | Onboarding in `index.html:44-83` collects persona **once** (Primary/High School Student, Researcher, Coastal Community, Others) | Onboarding persona vocabulary **doesn't match** backend's `PERSONA_SYSTEM_PROMPTS` set (Fisherman/Student/Researcher/General Public, `advisory.py:209`) — no "Explorer"/"Fisherman" mapping visible, and there's no runtime switcher, only a one-time choice. | 3h: add a persona dropdown in the dashboard header that calls `/api/orchestrate` with the backend's actual persona strings; fix the onboarding→backend persona mapping table |
| 16 | Personalized feed / ocean news | Partial | `app/news_feed.py` + `GET /api/news` — real ScienceDaily RSS, 1h cache | **Zero frontend consumer** (0 matches in `script.js`); not filtered by onboarding domain interests. | 2h: news panel + fetch on load; filter client-side by `localStorage` onboarding `domains[]` |
| 17 | Tiered explanations | **Verified Complete** | `advisory.py:256-278` per-persona vocabulary tiers; `chat.py:93` `_build_evidence_footer()` appends raw stats after narrative | None. | 0h |
| 18 | Chatbot inline charts | Partial | `historical.py` renders matplotlib PNGs (static `<img>` URLs), not interactive Chart.js; Chart.js *is* loaded and used for the real SHAP bar chart | Trend/distribution charts are raster images, not GRAPH/PIE keyword-triggered Chart.js renders as spec'd. | 4h: add a Chart.js-based line/pie renderer fed by `historical.py`'s already-computed series data (return JSON alongside the PNG instead of only the PNG) |
| 19 | Specialized multi-agent swarm | Partial | `graph.py` genuinely fans out 7 nodes concurrently (`AGENT_FUNCS` L42-50, `dispatch_node` L146); but `sub_agents.py`'s nodes (navigation/fishing/compliance/hazard) are mostly non-LLM formatters over one shared `_fetch_common_signals()` batch, not independent LLM specialists with distinct system prompts | Only `planner.py` and the final synthesizer call Gemini. This is real parallel task decomposition, but not "N agents with N system prompts" as advertised. | **Reframe, don't rebuild**: this is architecturally sound (real concurrency, real routing) — 48h isn't enough to give every node its own LLM call without blowing the latency budget the team already fixed (see `main.py:363-369` comment on the 23s-latency fix). Pitch it accurately as "planner-routed parallel specialist pipeline," which is true and still strong. |
| 20 | Biodiversity/oil-spill + CG hotline | **Not Started** | Only an unfulfilled onboarding checkbox label ("Marine Biodiversity") | No data or logic. | **Descope.** |
| 21 | In-chat interactive map | **Not Started/Partial** | Main map (`#oceanMap`) is a separate panel, not embedded per-message | Would need a mini-Leaflet-per-message-card pattern. | 3h: render a small static Leaflet instance inside `appendAdvisoryCard()` centered on `vessel_coord`, reusing the existing map init pattern |
| 22 | Ocean Indicators Dashboard | Partial | `index.html:229-245` "Prediction Telemetry" — 3 bars (SST anomaly, chlorophyll gradient, ML confidence) | No pH/salinity gauges, despite `statistical_engine.py` already detecting salinity/pH anomalies server-side — this is a UI gap, not a backend gap. | 2h: add 2 more telemetry bars fed from `statistical_engine`'s existing salinity/pH Z-test outputs, thread through `_build_telemetry()` in `main.py` |
| 23 | Marine Species Explorer | **Not Started** | None | Needs species dataset + depth-color UI — no data source lined up. | **Descope for 48h.** |
| 24 | Live satellite data pipeline | Partial, mislabeled | `chlorophyll_tool.py` (real NASA/NOAA MODIS-Aqua ERDDAP) and `pfz_tool.py` (real INCOIS WFS) **are** genuine live satellite/INCOIS feeds; `satellite_tool.py` is actually an Open-Meteo marine-**weather** API, not satellite imagery, despite its name | Rename `satellite_tool.py` → `marine_weather_tool.py` (or add a doc comment) so the pitch deck doesn't overclaim; no code logic changes needed. | 0.5h (rename + import fixes only, per "don't rewrite working code" — a pure rename, not a rewrite) |
| 25 | Inland lakes data | **Not Started** | None — dataset is Arabian Sea coastal Argo only | Out of scope, different dataset entirely. | **Descope.** |
| 26 | Precipitation / El Niño / IOD tracking | **Not Started** | None | Out of scope. | **Descope.** |
| 27 | Thermodynamic cycle simulation | **Not Started** | None | Out of scope. | **Descope.** |
| 28 | Navigation suite (compass/bearing) | **Not Started** | None — vessel marker shows position only, no bearing | Straightforward client-side geometry, no backend needed. | 2h: compass widget using `navigator.geolocation`'s heading (or two-point bearing calc) + a CSS-rotated needle |
| 29 | Coastal Resilience Index | **Not Started** | None | Out of scope — needs a scoring methodology and data the team doesn't have. | **Descope.** |

### Benchmark Alignment (30–33)

All four — INCOIS SAMUDRA, Global Fishing Watch/AIS, Mercator Digital Twin Ocean, Allen Coral
Atlas — have **no direct integration**. The only genuine INCOIS tie-in is the live PFZ WFS feed in
`pfz_tool.py:55`, which is real but is the operational PFZ layer, not SAMUDRA itself. **Do not
claim benchmark alignment in the pitch beyond "consumes the same live INCOIS PFZ product SAMUDRA
publishes."** Everything else in this section is out of scope for 48h.

### Scorecard

Of 33 items: **6 Verified Complete** (2, 3, 5, 17, plus 24's chlorophyll/PFZ half), **~11 Partially
Implemented** (1, 4, 9, 14, 15, 16, 18, 19, 21, 22, 24), **~16 Not Started**, of which **11 should
be formally descoped** for this sprint (6, 8, 11, 12, 20, 23, 25, 26, 27, 29, 30-33) because they
require datasets, ML dependencies, or hardware integrations that do not exist and cannot be
honestly built in 48 hours.

---

## Section B — 48-Hour Chronological Sprint Roadmap

Reordered from the original brief to match what's actually gap-having vs. already-done — no time
is spent on items already Verified Complete (2, 3, 5, 17), and no time is spent faking PINNs/causal
graphs/Bhashini/local-LLM (11, 12, 6, 8, 20, 23, 25-27, 29-33), which are called out as explicit
non-goals below. Times assume 4 people working in parallel on independent files (see Section C for
exactly which files, so no two people touch the same one).

### Day 1, Hours 00:00–12:00 — Backend Gaps + Data Wiring
- Hazard mesh endpoints + TTL query (Feature 7) — `main.py`, `db_store.py`
- Text-to-SQL tool exposure (Feature 9) — `historical.py`
- EEZ hard-block in A* grid (Feature 2 polish) — `route_planner.py`
- Return-heading bearing calc (Feature 3 polish) — `boundary_toool.py`
- Escalation stub endpoint (Feature 13) — `main.py`, `db.py`
- Fix broken template-literal bug in `startGeofenceMonitor()` (`script.js` ~L726)
- `satellite_tool.py` → `marine_weather_tool.py` rename pass (Feature 24 labeling)
- Salinity/pH telemetry threading (Feature 22 backend half) — `main.py`'s `_build_telemetry()`

### Day 1, Hours 12:00–24:00 — Remaining Backend + Voice/Dispatch Polish
- Missing language entries (Hindi/Bengali/Kannada/Punjabi/Odia) in `voice.py` + `advisory.py`
- Anchor drift sentry backend hook, reusing geofence poll pattern — new small endpoint or pure
  client-side (team's call; client-side is cheaper, see Section C)
- SHAP "what-if" sensitivity slider backend support (perturbed `predict_pfz_confidence` calls) —
  `pfz_ml.py` already supports this; just needs a param-passthrough in `main.py`
- Persona vocabulary reconciliation: onboarding choices → backend `PERSONA_SYSTEM_PROMPTS` keys
- News feed personalization filter groundwork (return `domains` tags on each article if cheap; else
  filter purely client-side)

### Day 2, Hours 24:00–36:00 — Frontend Wiring (the biggest single gap)
- Morning Dispatch button + PDF/audio render (Feature 4) — this is the single highest-value/lowest-
  effort item on the whole matrix: fully-built backend, zero frontend, 1.5h estimate
- Hazard mesh map layer: click-to-report modal + hazard icon rendering (Feature 7 frontend half)
- News feed panel (Feature 16 frontend half)
- Persona runtime switcher in dashboard header (Feature 15 frontend half)
- Chart.js trend/pie rendering fed by `historical.py`'s JSON series (Feature 18 frontend half)
- Compass/bearing widget (Feature 28)
- In-chat mini-map per advisory card (Feature 21)
- 2 additional Ocean Indicators telemetry bars (Feature 22 frontend half)

### Day 2, Hours 36:00–48:00 — Hardening, Honest Framing, Rehearsal
- End-to-end pass through every newly-wired endpoint with the real backend running (not mocks)
- Verify the `MOCK_ORCHESTRATOR_RESPONSE` fallback in `script.js` still triggers cleanly if the
  backend is down during the live demo (it already exists — just confirm it isn't stale)
- Update pitch deck / demo script to match Section A's honest status table — **do not claim PINNs,
  Bhashini, local-LLM blackout mode, or benchmark alignment (30-33) exist**; instead frame them as
  "validated next milestones," which is defensible to judges and avoids a live technical
  cross-examination the team can't win
- Performance pass: re-confirm the ~23s→lower latency fix noted in `main.py:363-369` still holds
  after adding the new endpoints (they should be additive, not on the hot path)
- Full demo rehearsal covering: voice query → advisory → route → geofence siren trip → hazard
  report → Morning Dispatch download → SOS button

**No "Blackout Mode local LLM," "PINN training," "causal reasoning engine," or "Bhashini pipeline"
tasks appear anywhere above** — building fake versions of these would cost more time than the real
gaps above and would not survive a technical Q&A. This is the single most important correction to
the original 48-hour brief.

---

## Section C — Team Role Allocations & Dependency Graph

File-level split, chosen so no two people ever touch the same file in the same window:

**Chakshu (Backend, APIs, LangGraph, Voice I/O)**
- `main.py`: hazard mesh endpoints, escalation stub, telemetry threading, Text-to-SQL tool wiring
- `voice.py`, `advisory.py`: additional language entries
- `dispatch.py`: confirm generation still works after other backend changes (no changes needed —
  it's done; Chakshu's job here is just the frontend handoff sync with Aarya)

**Aarya (Frontend, UI/UX, Leaflet Maps)** — *note: `script.js` is currently open in your editor*
- `script.js` / `index.html`: Morning Dispatch button, hazard mesh map layer + report modal, news
  panel, persona switcher, compass widget, in-chat mini-map, telemetry bars, fix the broken
  template literal in `startGeofenceMonitor()`
- Coordinate with Chakshu on exact JSON shapes before wiring each fetch call — the backend
  responses for hazard mesh and Text-to-SQL are new, so lock the contract first to avoid rework

**Chaiti (Data Science, ML, Explainability, Text-to-SQL)**
- `pfz_ml.py`: expose the perturbed-input path for the "what-if" sensitivity slider
- `historical.py`: add `query_argo_bbox` as an 8th Gemini tool call target
- `statistical_engine.py`: confirm salinity/pH outputs are in the right shape for `main.py`'s new
  telemetry fields (read-only check, this file is otherwise complete)
- Own the honest-framing pass for the pitch deck's ML/AI claims (SHAP is real and should be
  headlined; PINN/causal claims should be removed, not embellished)

**Rushil (DevOps, Data Pipelines, Geofencing, Boundary Logic)**
- `route_planner.py`: EEZ hard-block in the A* cost grid
- `boundary_toool.py`: return-heading bearing calculation
- `db_store.py`: TTL query for hazard mesh (`get_hazard_mesh` needs a `WHERE timestamp > ...` clause
  added — the table and insert function already exist)
- `db.py`: confirm `insert_sos_event` reuse for the escalation stub is safe under concurrent writes
- File rename: `satellite_tool.py` → `marine_weather_tool.py` (update the two importers: `main.py`,
  `sub_agents.py`)

No dependency blocks: every backend file above is either new code or an isolated, additive change
to a file no one else is editing. The only cross-team dependency is Aarya needing Chakshu's and
Chaiti's new endpoint response shapes agreed *before* Hour 24 — schedule a 15-minute contract sync
at the Day 1/Day 2 boundary, not ad hoc.

---

## Section D — UI/UX Dashboard Architecture Specification

**Current state** (`index.html`, 255 lines): loading screen → 2-step onboarding modal → hero slide
→ "About Us" slide → single "ORCA Control Room" dashboard slide (map panel + chat side-panel +
3-bar telemetry footer + SOS button). This is already a clean, non-generic nautical aesthetic (dark
ocean/satellite map tiles, pink-noise ocean ambience, language-rotating hero title) — **preserve
it**, extend it.

- **High-contrast nautical aesthetic**: keep the existing dark ocean-tile basemap and amber/red
  hazard-banner palette; new panels (hazard mesh, news, compass, dispatch button) should reuse the
  existing `.advisory-card`/`.agent-badge` CSS classes already in `style.css` rather than
  introducing a new visual language.
- **Desktop layout**: add the persona switcher and compass widget to the existing dashboard header
  row (same row as the Ocean/Satellite base-layer toggle); add the news panel and Morning Dispatch
  button as new cards stacked below the Prediction Telemetry footer, not as new top-level slides —
  the app's single-scroll-dashboard structure should stay intact.
- **Mobile viewport**: the map panel and chat panel already stack vertically below a breakpoint per
  `style.css` — confirm the new cards (news, dispatch, compass) collapse into the same single-column
  stack, tested at 375px width before Hour 48.
- **Chatbot behavior**: already correctly tiered (`advisory.py` persona prompts put plain narrative
  first, `chat.py`'s evidence footer appends raw stats after) — this pattern is the template every
  new panel should follow: plain-language headline first, expandable raw numbers/chart second.

---

## Non-Goals (explicit, so no one burns hours on these in the next 48h)

PINNs/Navier-Stokes modeling (11), causal reasoning graphs (12), Bhashini/Whisper/offline STT (1's
stretch), local/offline LLM via Ollama (6), catch-to-market pricing (8), biodiversity/oil-spill
modeling (20), species explorer (23), inland lakes (25), El Niño/IOD tracking (26), thermodynamic
simulation (27), coastal resilience index (29), and benchmark parity with SAMUDRA/Global Fishing
Watch/Mercator/Coral Atlas (30-33). Each requires either a missing ML dependency, a dataset that
doesn't exist, or a multi-week research effort — attempting any of them in this sprint would trade
real, demoable gaps (Section A/B above) for a fake feature that fails under judge questioning.
