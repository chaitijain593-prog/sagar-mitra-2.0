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
