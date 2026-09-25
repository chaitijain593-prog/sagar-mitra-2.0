# Sagar Mitra 2.0 / ORCA — Remaining Work

Re-audited against the live codebase on `main` on 2026-09-22. **Day 1 (all backend gaps + voice/dispatch
polish) is fully complete and verified against the code.** Day 2's frontend wiring pass is mostly done
too — Morning Dispatch, hazard mesh map layer + report modal, news panel, persona runtime switcher, and
the 5-bar Ocean Indicators telemetry row are all wired end-to-end. This file now only tracks what's
actually left.

The Vessel Bearing compass (Feature 28) was also fixed in this pass: it previously only recomputed a
bearing when the backend's `vessel_coord` happened to change between two advisory responses (which in
practice almost never fires, so the needle looked frozen), and had no path to real device orientation at
all. It now has a "Live Compass" toggle that reads the device's real orientation sensor
(`deviceorientationabsolute`/`deviceorientation`, with the iOS `webkitCompassHeading` and
`DeviceOrientationEvent.requestPermission()` gesture-gated permission flow both handled), falls back
cleanly to the old GPS-course-over-ground behavior when no sensor is available or permission is denied,
and stands the GPS fallback down while the live sensor is active so the two sources don't fight. Verified
with a headless-Chromium run: pure heading math (webkit-priority, absolute-only gating, screen-angle
offset, wraparound) all checked, and the live end-to-end flow (button → permission → sensor event →
needle rotation → readout text) was exercised with synthetic orientation events and produced zero
console/page errors.

---

## Open Items

### 1. Chart.js trend/pie charts are still raster PNGs, not real Chart.js renders (Feature 18)
- `backend/app/historical.py`'s `plot_yearly_trend` / `plot_category_distribution` tools still render
  matplotlib PNGs server-side and return only a `plot_url` — no JSON series/breakdown data comes back
  alongside them.
- The dashboard's `historicalChart` (Chart.js line chart, `script.js:342`) only ever shows static
  baseline mock data; `updateHistoricalChart()` is wired to read `telemetry.historical_series`, but
  nothing in the backend ever populates that field.
- **To close:** have `historical.py` return the underlying series (years/values, or category
  percentages) as JSON alongside `plot_url`, and add a Chart.js pie-chart renderer for the distribution
  case in `script.js` triggered off keywords like "pie chart"/"distribution"/"breakdown", matching the
  existing line-chart pattern.

### 2. In-chat mini-map per advisory card is not implemented (Feature 21)
- `appendAdvisoryCard()` (`script.js:599`) renders status/alerts/SHAP chart but never embeds a map.
- **To close:** render a small static Leaflet instance inside the advisory card, centered on
  `data.vessel_coord`, reusing the existing main-map init pattern (`script.js:189`).

### 3. Anchor drift sentry has no frontend (Feature 10)
- Backend is done: `GET/POST` anchor endpoints exist (`backend/app/main.py:314-342`,
  `/api/sentry/anchor-drift`), backed by `db_store.get_anchor`/`set_anchor`.
- Zero frontend — no UI to set an anchor point, no polling, no alarm wiring. `script.js` has no
  matches for "anchor" at all.
- **To close:** reuse the existing `pollGeofence()`/`playGeofenceSiren()` polling skeleton
  (`script.js`) against `/api/sentry/anchor-drift` instead of the boundary endpoint, plus a small
  "Set Anchor Here" map-click affordance.

### 4. SHAP "what-if" sensitivity slider has no frontend
- Backend support is done: `main.py` (`~L79`, `~L242`) already accepts perturbed inputs and threads
  them through to `pfz_ml.py`'s SHAP path.
- No slider or any UI control exists to actually send a perturbation — the capability is unreachable
  from the dashboard.
- **To close:** add parameter sliders (e.g. SST/chlorophyll offset) to the Researcher-persona advisory
  card that re-call the orchestrate endpoint with perturbed values and re-render the SHAP chart,
  labeled honestly as sensitivity analysis on the real model (not causal inference), per the original
  non-goals note below.

### 5. Hardening, honest framing, and rehearsal pass (originally Day 2, Hours 36–48)
Not code gaps, but still outstanding before this is demo-ready:
- End-to-end pass through every wired endpoint with the real backend running (not the `MOCK_
  ORCHESTRATOR_RESPONSE` fallback).
- Confirm the `MOCK_ORCHESTRATOR_RESPONSE` fallback in `script.js` still triggers cleanly if the
  backend is down during a live demo.
- Confirm the mobile layout (map/chat stack, news/dispatch/compass cards) actually collapses to a
  single column at 375px width — not yet visually verified.
- Update the pitch deck / demo script to match reality: SHAP explainability, the live INCOIS PFZ feed,
  the parallel specialist pipeline, and now the live-sensor compass are real and worth headlining;
  PINNs, Bhashini, local-LLM blackout mode, and SAMUDRA/Global Fishing Watch/Mercator/Coral Atlas
  parity do not exist and should not be claimed (see Non-Goals below).
- Full demo rehearsal: voice query → advisory → route → geofence siren trip → hazard report → Morning
  Dispatch download → live compass → SOS button.

---

## Non-Goals (unchanged — do not build these)

PINNs/Navier-Stokes modeling, causal reasoning graphs, Bhashini/Whisper/offline STT, local/offline LLM
via Ollama, catch-to-market pricing, biodiversity/oil-spill modeling, species explorer, inland lakes,
El Niño/IOD tracking, thermodynamic simulation, coastal resilience index, and benchmark parity with
SAMUDRA/Global Fishing Watch/Mercator/Coral Atlas. Each requires either a missing ML dependency, a
dataset that doesn't exist, or a multi-week research effort — building any of them would trade real,
demoable work above for a fake feature that fails under technical questioning.

---

# Sagar Mitra 2.0 — Specification Audit and Roadmap

**Audit date:** 2026-09-25  
**Scope:** `Sagar-mitra/` project workspace, including `backend/app/`, backend data and model artifacts, and `frontend/`.  
**Reference:** The master specification supplied in the audit request. No separate file named “Master System Specification & Architecture” was present in the scanned project files.

## Executive Summary

**Estimated specification completion: 55% (qualitative, evidence-weighted estimate).** The project is a working prototype with meaningful end-to-end coverage for interactive marine queries, live ocean/weather signals, route/map display, geofence alerts, voice input, and several optional data layers. It is not yet a production-ready, independently orchestrated nine-agent system. Several named agents are capabilities inside a monolithic LangGraph dispatch stage rather than independent graph nodes, and the Marine Data Discovery and Visualization agents are not graph agents at all.

The strongest implemented areas are the PFZ/weather query flow, EEZ/MPA geospatial checks, Leaflet observations and ecosystem overlays, depth coloring/clustering, crowdsourced hazard reporting, and audio input/advisory output. Important limits include synthetic fallback ocean-profile data, heuristic rather than official cyclone detection, no measured migratory tracks, only coarse seasonal occurrence filtering, incomplete uncertainty/evidence display, and in-memory session/anchor state. The stand-alone sensitivity route also supplies fallback probability/SHAP values when model output is unavailable, which can make its output look more certain than the model actually is.

The percentage is a planning estimate, not a test-coverage or code-volume calculation. Statuses below are judged against end-to-end wiring and the stated target, not against whether a similarly named file exists.

## Agent Architecture Audit Matrix

The actual LangGraph in `backend/app/graph.py:create_orca_graph` has three top-level nodes: `planner`, `dispatch`, and `synthesizer`. `dispatch` concurrently invokes selected functions from `backend/app/sub_agents.py`; the workers are separate functions, but are not nine separate LangGraph nodes. `backend/app/planner.py:VALID_AGENTS` currently lists eight specialist labels and omits Discovery, Visualization, and User Interaction as independent specialist agents.

| Spec agent | Status | Implementation and capability | Gap against specification |
|---|---|---|---|
| 1. Planner Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/graph.py:create_orca_graph` registers `planner_node`; it calls `backend/app/planner.py:plan_query` to select workers, infer language/persona/intent, and consider recent history. | Planner is a nested function in the graph module, not its own module/class or reusable graph sub-agent. LLM output parsing and routing are implemented, but no task graph decomposition/execution plan is exposed as structured steps to clients. |
| 2. Marine Data Discovery Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/indobis_service.py:get_marine_observations` calls OBIS and normalizes occurrence records; `/api/marine-observations` in `backend/app/main.py` exposes it. `backend/app/data.py` and `backend/app/db.py` provide Argo profile data/query support. | No Discovery agent/node in `AGENT_FUNCS` or the LangGraph; IndOBIS is a separate map API, not coordinated by the conversational planner. No live Argo discovery client is wired into the agent flow; Argo profiles load from a local Parquet file or synthetic data. |
| 3. Weather Intelligence Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/sub_agents.py:navigation_node` and `hazard_node`; `backend/app/marine_weather_tool.py:get_live_ocean_conditions`; `backend/app/weather_alert_tool.py:get_weather_hazard_alerts`. Common reads are run concurrently in `graph.py:dispatch_node`. | Worker functions exist, but not as separately registered graph nodes. “Cyclone” is a gale-force wind proxy, explicitly not an official IMD/INCOIS track or warning. No continuous server-side monitoring; browser polling covers geofence, not general weather alerts. |
| 4. Ocean Analytics Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/sub_agents.py:analytics_node` uses `ArgoStatisticalAnomalyEngine`; `backend/app/statistical_engine.py` computes physical layer metrics and anomaly tests; `backend/app/pfz_ml.py:predict_pfz_confidence` supplies trained-model predictions and optional SHAP. `fishing_node` also queries chlorophyll/PFZ. | It is a worker function, not an independent graph node. Production coverage depends on local real data/model artifacts; `backend/app/data.py` constructs synthetic Argo-like data if the Parquet dataset is absent. Oxygen/pH baselines can be fallback constants where observations are unavailable. |
| 5. Geospatial Reasoning Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/sub_agents.py:compliance_node`; `backend/app/boundary_toool.py:check_maritime_boundary` and `distance_to_nearest_boundary_km`; `backend/app/route_planner.py:plan_safe_route`; route, PFZ, and regional geometries are surfaced to the map. | No separately modeled spatial-temporal reasoning agent. Seasonal correlation is limited to occurrence month/season labels and filters; cross-dataset spatial correlation and confidence/provenance tracking are absent. |
| 6. Risk Assessment Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/main.py:_derive_geofence_alert`, `/api/geofence-check`, and `run_orchestration`; `backend/app/boundary_toool.py` checks EEZ/MPAs; frontend `pollGeofence`/`updateGeofenceTransition` and siren functions alert on state changes. | Risk rules are distributed across modules rather than a dedicated agent. The 5 km threshold is primarily a frontend transition rule informed by backend boundary distances. IMBL rule coverage is not demonstrated as a complete, validated regulatory ruleset; alerts are not a substitute for official navigation warnings. |
| 7. Visualization Agent | [~] **PARTIAL / IN PROGRESS** | `frontend/script.js` renders PFZ, hazard, marine-observation, mangrove, and chlorophyll layers; `renderMarineObservationLayer` supports depth colors, cluster markers, and optional observation-sequence lines. | No Visualization agent/node prepares rendering directives. Rendering and styling live directly in browser code. No map rendering API contract beyond layer metadata and query records. |
| 8. Reporting Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/graph.py` has `synthesizer_node`; `backend/app/advisory.py:synthesize_advisory` creates localized responses; `backend/app/dispatch.py:generate_morning_dispatch` creates PDF/audio; `/api/dispatch/generate` and frontend `initDispatchButton` expose dispatch. Statistical results are produced by `statistical_engine.py`. | Synthesis is a graph node, but there is no independent Reporting agent. Responses do not consistently surface source-level evidence, confidence/limitations, or statistical diagnostics in structured form. The chat-triggered `morning_dispatch_node` returns signal text; downloadable artifacts are built through the separate dispatch route. |
| 9. User Interaction Agent | [~] **PARTIAL / IN PROGRESS** | `backend/app/main.py:run_orchestration`, `/api/voice/orchestrate`; `backend/app/nlp_extract.py`; `backend/app/voice.py`; `backend/app/session_store.py`; frontend `handleQuerySubmit`, `initVoiceMic`, and prompt-edit/regenerate UI. | No independent User Interaction agent/node. Session history is an in-process store and is lost on backend restart; the browser preserves a single ongoing transcript. The multi-conversation manager/history UI was removed at the user's request. Authentication is a simple JSON-file/OTP prototype, not a production identity/access-control system. |

**Architecture conclusion:** The code has a functional planner → dispatch → synthesizer flow with specialist worker functions, but does not meet a literal requirement for nine autonomous, independently addressable agents. Discovery, Visualization, Reporting, and User Interaction are especially cross-cutting or external to the graph. A dedicated `backend/app/agents/` package does not exist.

## Feature-by-Feature Breakdown

### Stakeholders and Core Query Flows

- [~] **Fishermen — PFZ, safe route, weather:** `/api/orchestrate` → `run_orchestration` invokes the LangGraph; `fishing_node`, `navigation_node`, and `compliance_node` provide PFZ/chlorophyll, marine weather, and boundary signals. `plan_safe_route` supplies route geometry; the frontend displays advisories, PFZ areas, and routes. This is the most complete end-to-end workflow. The PFZ source can be local CSV and data availability is not guaranteed everywhere.
- [~] **Coastal authorities — hazard reporting and incident logging:** `POST /api/hazard`, `GET /api/hazard/mesh`, `/api/sos`, and `/api/escalate` are backed by SQLite (`backend/app/db_store.py` and `backend/app/db.py`) and map/report UI in `frontend/script.js`. This supports local crowdsourced reports and simulated escalation, not authority dispatch, review/triage queues, or role-based authority workflows.
- [~] **Researchers — history, anomalies, species data:** Historical queries/charts, statistical anomaly worker, SHAP outputs, OBIS search, and observation filters exist. The underlying profile data may be synthetic, seasonal analysis is basic, and the observation API returns capped occurrence records rather than statistical distribution products.
- [~] **Personas / user access:** Frontend role/persona selection and `reconcile_persona_key` influence advice style. There is no authorization model establishing different capabilities or data access for the three stakeholder groups.

### Spatial-Temporal Reasoning and Marine Species

- [~] **OBIS/IndOBIS observation lookup:** `backend/app/indobis_service.py:get_marine_observations` supports Indian EEZ, Indian Ocean, or global extents; scientific/common-name taxon mapping; dates; month/season filters; normalization; and best-effort timeout/HTTP error handling. `backend/app/main.py:/api/marine-observations` exposes JSON records to the frontend. There is no explicit cache in this fetch function, and an upstream failure becomes `[]`, indistinguishable to the client from a valid empty result.
- [~] **Seasonal display:** The service derives month and Indian season from each occurrence date and applies query filters. The filter and popup are wired in `frontend/script.js`. This is occurrence-date grouping/filtering, not climatological seasonal distributions, effort-corrected abundance, or a seasonal statistics service.
- [~] **Migratory paths:** `include_global_tracks` can add recent records for known migratory taxa, and `renderMarineObservationLayer` sorts dated records and draws `L.polyline` sequences. These are lines between observations of a taxon, not a tagged animal’s trajectory or validated migration corridor. Data caps, uneven sampling, and year-to-year joins can produce misleading paths; the UI describes them as observation sequences.
- [x] **Depth styling and clustering (map rendering):** OBIS normalization includes `depth_m`; `renderMarineObservationLayer` styles depth-colored markers and uses `L.markerClusterGroup` where available. The filter control and legend are in `frontend/script.js`; MarkerCluster CSS/JS is loaded from CDN in `frontend/index.html`. Unknown-depth styling remains distinct. This meets the requested rendering behavior, but depends on third-party CDN availability.

### ML, SHAP, and Statistical Explainability

- [~] **PFZ model:** `backend/app/pfz_ml.py:predict_pfz_confidence` loads `backend/app/pfz_predictor_best.joblib`; model training and dataset preparation scripts are under `backend/scripts/`. Missing artifacts are handled with `None`, so the actual probability is unavailable until a usable model is present.
- [~] **SHAP attribution:** Tree SHAP is attempted for supported tree classifiers; unsupported models or SHAP errors return `None`. The orchestrator telemetry can include real attribution data. `POST /api/predict/sensitivity` and frontend `initWhatIfSensors` provide slider interaction, but the endpoint contains fallback probability/SHAP values when the model result is absent. Those fallbacks are not model-derived evidence and should be removed or explicitly labeled as unavailable before treating the feature as explainable output.
- [~] **Statistical testing:** `backend/app/statistical_engine.py:ArgoStatisticalAnomalyEngine` implements QC, TEOS-10 standardization, Z/MAD, t-test, two-sample K-S, physical layer metrics, and persistence checks. It is reachable through `analytics_node`. Coverage and validity depend on real, co-located profile/time-series data and domain validation; `backend/app/data.py` currently has a synthetic fallback profile/dataset.
- [ ] **Calibrated explanation quality evaluation:** No visible model evaluation report, data-split protocol, prospective validation, SHAP consistency checks, or dedicated test suite was found in the scanned project tree.

### Proactive Geofencing, Routing, and Anchor Drift

- [x] **EEZ/MPA checks and map geofence polling:** `backend/app/boundary_toool.py` uses `backend/data/india_eez.geojson` and `india_mpas.geojson`; `/api/geofence-check` returns boundary status/distance. Frontend `pollGeofence` runs periodically and `updateGeofenceTransition` updates the safety banner and can trigger the browser siren when the state changes.
- [~] **5 km alert semantics:** The frontend defines `GEOFENCE_ALERT_KM = 5`; server boundary checks and the client combine distances/statuses. Verify in operational acceptance testing that the value represents proximity to both EEZ and MPA boundaries as intended, including boundary-data failure and alert-reset behavior.
- [~] **Safe route generation:** `backend/app/route_planner.py:plan_safe_route` considers EEZ/MPA geometry and sampled wave costs; orchestration plots the response. Dataset freshness, route quality, and safe handling of cells with unavailable wave data need documented validation.
- [~] **Anchor Drift Sentry:** UI (`Set Anchor`, `toggleAnchorMode`, `setAnchorAt`, `pollAnchorDrift`) and `/api/sentry/anchor-drift` endpoints are wired. `backend/app/anchor_store.py` is an in-memory store, so anchor state is lost on process restart and is not shared by multiple workers. A second SQLite anchor implementation exists in `db_store.py`, but the route uses the in-memory store.
- [~] **IMBL safety policy:** Boundary geometry and warnings exist, but no auditable, complete IMBL regulatory rule engine or legal-content versioning was found.

### Environmental Data, Ecosystems, and Hazard Mesh

- [~] **Marine environmental signals:** `marine_weather_tool.py` queries marine weather; `weather_alert_tool.py` derives thunderstorm and high-wind alerts; `chlorophyll_tool.py` queries NOAA CoastWatch; `pfz_tool.py` supplies PFZ information. Network/error handling and spatial/temporal coverage differ by source; cyclone output is a heuristic.
- [~] **Mangroves and chlorophyll map overlays:** `GET /api/ecosystem-layers` returns Global Mangrove Watch query metadata and NASA GIBS chlorophyll WMS settings; frontend `loadEcosystemLayers` fetches GeoJSON, applies green polygon styling/popups, and registers a chlorophyll tile overlay. The configured local mangrove mirror `/static/data/mangroves_india.geojson` is not present in the scanned file list; the browser falls back to the external ArcGIS endpoint. External service availability and GIBS layer compatibility are not validated here.
- [~] **Hazard mesh:** Reports are stored in SQLite with a 24-hour read TTL (`db_store.py:insert_hazard_point/get_hazard_mesh`); frontend `initHazardReporting` and `loadHazardMesh` allow reports and display points. It is a manually reported local hazard mesh; no automated plastic/pollution detection or networked authority moderation exists.
- [ ] **Dedicated pollution intelligence:** No concrete plastic detection model, pollutant concentration ingestion, or pollution analysis pipeline was found. Hazard type labels let users report debris/slicks, which is not automated pollution tracking.

### Multi-Modal Voice, NLP, and Persistence

- [~] **Text chat and planner NLP:** Chat submissions call `/api/orchestrate`; `planner.py:plan_query` detects requested agents/language/persona/intent, and `nlp_extract.py` parses coordinates/time. This depends on configured model credentials and external services.
- [~] **Voice input/output:** `POST /api/voice/orchestrate` accepts audio and returns transcription/translation plus spoken advisory URL where TTS succeeds. `voice.py` uses hosted transcription/speech APIs; current speech synthesis supports English only, while the UI has audio capture and response playback. No offline STT/TTS or fully multilingual speech synthesis.
- [~] **Multi-turn persistence:** `backend/app/session_store.py` holds recent history/context in process memory; frontend saves the active transcript locally. There is no database-backed server session store in the active orchestration import path, no cross-device conversation persistence, and no conversation-history management UI (removed per user direction).
- [~] **Authentication:** Signup/login/OTP/profile endpoints exist in `main.py`; `users.json` and in-memory token/OTP dictionaries do not provide production-grade secure identity, durable sessions, rate limiting, or role-based permissions.

### API, Frontend, and Operational Readiness

- [x] **Core endpoints are present:** `/api/orchestrate`, `/api/voice/orchestrate`, `/api/dispatch/generate`, `/api/geofence-check`, `/api/hazard`, `/api/hazard/mesh`, `/api/marine-observations`, `/api/ecosystem-layers`, news, and sensitivity routes are registered in `backend/app/main.py`.
- [~] **Frontend resilience:** Marine observation and ecosystem fetch paths show status/errors and generally keep the map operational. Several other frontend fetch flows and backend routes need consistent timeouts, validation, structured failure codes, and user-visible degraded-mode behavior.
- [~] **Deployment configuration:** CORS currently allows wildcard origins with credentials. This is convenient for local development but should be replaced with explicit deployment origins before production. Frontend API base URL is hard-coded to `http://127.0.0.1:8000`.
- [ ] **Automated verification:** No dedicated test suite or CI configuration was found in the scanned project files. Prior roadmap notes refer to manual/headless checks, but reproducible committed test coverage for API contracts, provider failures, data validity, or browser flows was not identified.

## Actionable Next Steps / Backlog

### P0 — Correctness, Safety, and Trust

- [ ] Remove fabricated sensitivity endpoint defaults; return `null`/unavailable status if model confidence or SHAP cannot be computed. Mark the frontend display as unavailable instead of reporting fallback values as model results.
- [ ] Establish a real Argo ingestion/update path and explicitly surface whether the current request is using real, stale, or synthetic data. Do not present synthetic profile output as a live observation.
- [ ] Add automated tests for endpoint contracts, OBIS timeouts/status codes/empty results, date/species filters, boundary edge cases, and SHAP unavailable/model unavailable paths.
- [ ] Validate route planning and geofence thresholds against authoritative boundary data and documented maritime safety requirements; record geometry provenance/version and fail visibly when geometry is unavailable.
- [ ] Replace wildcard credentialed CORS and hard-coded localhost API URLs with environment-specific deployment configuration.

### P1 — Data and Architecture Completion

- [ ] Create an explicit `backend/app/agents/` package with independently named/typed agent modules and graph nodes for Discovery, Weather, Ocean Analytics, Geospatial Reasoning, Risk, Visualization, Reporting, and User Interaction. Keep Planner as a dedicated node and define typed inputs/outputs, evidence, failures, and provenance for each.
- [ ] Make OBIS fetch failure distinguishable from a successful empty result (for example structured `{data, status, source, stale}`); consider bounded TTL caching and pagination/rate controls. Current OBIS endpoint returns an empty array on upstream failure and caps response size.
- [ ] Replace migratory observation-sequence lines with validated, selectable temporal cohorts or a trajectory product backed by individual tags/track identifiers. Keep ordinary occurrence points clearly distinguished from animal tracks.
- [ ] Upgrade seasonal display from month/season filtering to a real temporal aggregation API with sample counts, spatial bins, date completeness, and effort/caveat metadata.
- [ ] Persist chat history and anchor state in the active SQLite/production database layer; use a shared persistent store appropriate to multi-worker deployment and document retention/privacy policy.
- [ ] Add source freshness, licensing, attribution, units, and uncertainty metadata to map layers and advisory evidence. Verify Global Mangrove Watch and NASA GIBS responses and deploy/refresh the missing local mangrove mirror if local hosting is required.

### P2 — Stakeholder Workflows and Product Hardening

- [ ] Add stakeholder-specific access and workflows for fishermen, researchers, and coastal authorities, including explicit role permissions and authority review/escalation handling.
- [ ] Add a verified cyclone/storm warning source and distinguish official alerts from heuristic weather indicators in API schemas and UI.
- [ ] Build pollution tracking beyond user-entered hazard points: define source datasets, coverage, update cadence, quality checks, and event moderation.
- [ ] Complete researcher-facing evidence outputs: expose anomaly test/sample sizes, baseline period, confidence/limitations, model version, and source records alongside summaries.
- [ ] Standardize input validation, timeout/retry policy, error schemas, rate limiting, health checks, observability, and API documentation across all external-data routes.
- [ ] Reconcile roadmap/specification docs with implemented behavior, remove stale claims, and run end-to-end acceptance checks on desktop/mobile with external providers unavailable as well as online.

## Audit Notes and Limits

- This audit is based on source inspection of the project tree on the date above. It does not claim that external OBIS, NOAA, NASA, Open-Meteo, hosted LLM, or email services were reachable during the audit.
- File/function references describe the implementation found in source. No automated test suite was run as part of creating this audit document.
- The workspace contains existing uncommitted changes and data/runtime artifacts. This audit records current code behavior; it does not assume those changes are production-approved.
