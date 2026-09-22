<h1 align="center">🏙️ GeoStack — 3D ULPIN Assistant</h1>

<p align="center">
  <b>From 2D land parcels to verifiable 3D property records.</b><br>
  A geospatial platform that turns India's ULPIN cadastral system into an interactive, floor-by-floor 3D map — with an AI assistant, ML-driven compliance audits, and a cryptographically signed property ledger.
</p>

<p align="center">
  <b>Smart India Hackathon 2026 — Problem Statement 11</b><br>
  <i>3D ULPIN Generation and Vertical Property Mapping System</i><br>
  Ministry of Rural Development · Department of Land Resources
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white">
  <img alt="Google Gemini" src="https://img.shields.io/badge/Google_Gemini-GenAI_SDK-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white">
  <img alt="MapLibre GL" src="https://img.shields.io/badge/MapLibre_GL-3D_Map-396CB2?style=for-the-badge&logo=mapbox&logoColor=white">
  <img alt="CesiumJS" src="https://img.shields.io/badge/CesiumJS-Satellite_Globe-3D97D3?style=for-the-badge&logo=cesium&logoColor=white">
  <img alt="Pandas" src="https://img.shields.io/badge/Pandas-Data_Engine-150458?style=for-the-badge&logo=pandas&logoColor=white">
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-Isolation_Forest-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge">
</p>

<p align="center">
  <a href="#-problem-statement">Problem Statement</a> •
  <a href="#-overview">Overview</a> •
  <a href="#-key-domains--features">Features</a> •
  <a href="#%EF%B8%8F-proposed-architecture">Architecture</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-build-roadmap">Roadmap</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-data-sources">Data</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-license">License</a>
</p>

---

## 📋 Problem Statement

> India's land parcels are identified today by a **2D ULPIN** (Unique Land Parcel Identification Number) — a flat, surface-only record that cannot represent what actually exists on that parcel: a 40-floor tower, three basement levels, podium parking, or an unauthorized vertical extension built above the sanctioned height. Municipal authorities, RERA regulators, and citizens have no single, verifiable, floor-aware identity for vertical property — which means undeclared construction, disputed ownership, and non-compliant floors routinely go undetected until it's too late.
>
> **Goal:** Design a system that generates a true **3D ULPIN** — extending the 2D land parcel identity vertically, floor by floor and unit by unit — and uses it to make land and building records interactively verifiable, tamper-evident, and auditable for compliance.

## 🔎 Overview

GeoStack (built as **PixelPlot**) answers this with a live, explorable 3D cadastre of South Mumbai: every RERA-registered project in the dataset is rendered as a stack of real, floor-height-accurate polygons, each carrying its own 3D ULPIN, and layered with an AI assistant, an ML anomaly auditor, and a cryptographic ownership ledger on top.

| | **Traditional Approach** | **GeoStack's Approach** |
|---|---|---|
| **Identity** | One flat ULPIN per land parcel — no floor/unit granularity | Hierarchical 3D ULPIN per floor & unit (`{base}-F{floor}-U{unit}`), plus basement (`-B{level}`) and podium (`-F{floor}-PARK`) variants |
| **Verification** | Paper records, static PDFs, manual RERA lookups | Natural-language AI assistant + interactive 3D map, searchable by project, promoter, RERA ID, or ULPIN |
| **Compliance Auditing** | Manual, reactive inspection after complaints | Automated **Isolation Forest** anomaly detection flags unauthorized vertical extensions ("ghost floors") from height/floor discrepancies |
| **Ownership Records** | Mutable registry entries, no tamper evidence | SHA-256 signed audit ledger — every verified claim is cryptographically sealed |
| **Accessibility** | Text-only, English-only, desk-bound | Voice-driven chat in **English, Hindi, and Marathi**, markdown-rendered answers, usable on mobile |
| **Site Verification** | Manual measurement, no on-site overlay | AR camera view overlays live ULPIN identities on real buildings; LiDAR-style point-cloud elevation survey |

## 🧩 Key Domains / Features

### 1. 🗺️ 3D Cadastral Map
- MapLibre GL–powered interactive 3D city, centered on South Mumbai, with real building extrusions per floor
- Search bar resolves free text — coordinates, project name, promoter, RERA ID, PIN code, or ULPIN — and flies the camera to the result (`Seek` / `Fly`)
- Eight visual themes (Light, Dark, Blueprint, Cyberpunk, Synthwave, Midnight Ocean, Matrix, Sepia) and a live sun-position slider for real-time shadow simulation
- Layered filters: promoter, PIN code, project type, height tier, floor-count band, completion date, and lat/lng bounding box
- Subsurface X-ray mode reveals basements and underground parking; solar-investment heatmap grades rooftops by exposure

### 2. 🤖 AI ULPIN Assistant (Chatbot)
- Flask backend (`pixelplot/chatbot-server/app.py`) powered by the **Google GenAI SDK**, with automatic **model fallback** across `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-1.5-flash` and rotation across multiple API keys
- Two-step Gemini pipeline: (1) parses free-text queries into structured intent (`SEARCH_PROJECT`, `LIST_ALL`, `FOLLOW_UP_FLOOR`, `GENERAL_CONVERSATION`), (2) synthesizes a grounded, markdown-formatted answer from the retrieved dataset row
- Follow-up-aware — remembers the last discussed project so "what about floor 8?" resolves correctly without repeating the project name
- Replies render as markdown (via `marked.js`) and can drive the live map: a matched project triggers a `FLY_TO_LOCATION` action that flies the camera and opens that unit's popup
- **Multi-lingual voice input/output** — Web Speech API recognition and synthesis in **English (`en-IN`), Hindi (`hi-IN`), and Marathi (`mr-IN`)**, with an optional "read aloud" mode

### 3. 🆔 3D ULPIN Generation Engine
- `pipeline/ulpin.py` defines the vertical ID grammar — stable, position-only identifiers that never encode mutable facts (status, complaints, heights live as separate feature attributes instead):
  - `{base_ulpin}` — surface parcel
  - `{base_ulpin}-B{level:02d}` — underground/basement level, counted from grade down
  - `{base_ulpin}-F{floor:02d}-PARK` — above-ground podium/parking floor
  - `{base_ulpin}-F{floor:02d}-U{unit:02d}` — above-ground residential/commercial unit
- `pipeline/geometry.py` computes floor/basement vertical extents and MSL (mean sea level) elevation from ground elevation + structural height, so every floor's 3D bounding box is physically accurate
- `pixelplot/data/dataset.py` runs the full city-scale build: reads the master RERA CSV, generates a 3D ULPIN + SHA-256 integrity hash per building, and emits floor-by-floor GeoJSON for the whole dataset plus a locked `master_audit_ledger.json`
- `pipeline/generate_building.py` / `pipeline/api_server.py` do the same for a single new building on demand — footprint sourced from OpenStreetMap, classical CV edge detection, Segment Anything (SAM), or an area-derived square approximation

### 4. 🕵️ Ghost Floor ML Audit
- `pixelplot/chatbot-server/ghost_floor_detector.py` trains a **scikit-learn Isolation Forest** on engineered features (`height_discrepancy`, `floor_discrepancy`, `height_per_floor`) built from each building's sanctioned vs. observed floor count and height
- Flags projects where the built structure exceeds its sanctioned floors/height — an automated proxy for unauthorized vertical extensions — and reports the first illegal floor, excess height, and a confidence score
- Exposed via `GET /api/audit/ghost-floors` and surfaced on the map as a one-click toggle that highlights flagged buildings

### 5. 🔐 Cryptographic Ownership Ledger
- Citizens submit ownership claims (`POST /api/submit-claim`) into a pending queue; municipal officers/super-admins verify them (`POST /api/verify-claim`), which SHA-256-signs the claim and writes it into `master_audit_ledger.json`
- `pixelplot/js/geostack-ui.js` renders a live, role-gated spreadsheet view of the cadastral vault (PIN-gated: Desk Officer / Super Administrator), with field-level edit detection, tamper flags, and an accept/reject/re-sign workflow that mints a fresh integrity hash
- Digital Passbook (`passbook.html`) and QR-code generation (`qrcode.min.js`) provide a shareable, instantly scannable property passport

### 6. 📡 Site Verification Tools
- **AR View** (`js/ar-view.js`) — overlays nearby buildings' ULPIN labels directly onto the live device camera feed, using GPS position and compass heading
- **LiDAR Survey** (`js/lidar-survey.js`) — simulates a point-cloud elevation scan of the 3D scene for visual structural inspection
- **Real Satellite View** (`js/satellite-view.js`) — a lazily-loaded **CesiumJS** globe with real-world satellite imagery, world terrain, and OSM 3D buildings; flies to a hero building and renders its ULPIN flats as extruded, clickable polygons clamped to real terrain
- **Drone Flythrough** — scripted camera fly-around of a hero building for a full 3D walkthrough

## 🏗️ Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BROWSER (pixelplot/)                        │
│                                                                       │
│   index.html — MapLibre GL 3D city  ── js/map.js                    │
│        │                                                             │
│        ├── js/chatbot.js ───────────► AI Assistant widget           │
│        ├── js/geostack-ui.js ───────► Audit ledger / role gate      │
│        ├── js/ar-view.js ───────────► Camera AR overlay             │
│        ├── js/lidar-survey.js ──────► Point-cloud survey            │
│        └── js/satellite-view.js ────► CesiumJS globe (lazy-loaded)  │
│                                                                       │
└──────────────┬───────────────────────────────┬──────────────────────┘
               │ POST /api/chat                 │ POST /api/generate-building
               │ POST /api/submit-claim         │
               │ POST /api/verify-claim         │
               │ GET  /api/audit/ghost-floors   │
               ▼                                ▼
┌────────────────────────────────┐   ┌───────────────────────────────┐
│  Flask · Chat & Audit API      │   │  Flask · Building Pipeline API │
│  pixelplot/chatbot-server/     │   │  pipeline/api_server.py        │
│  app.py            :5000       │   │                     :5057      │
│                                 │   │  pipeline/build.py             │
│  ┌───────────────────────────┐ │   │  pipeline/geometry.py          │
│  │ Google GenAI SDK          │ │   │  pipeline/footprint.py         │
│  │ gemini-2.5 → 2.0 → 1.5    │ │   │   (OSM / CV / SAM / approx)    │
│  │ multi-key fallback        │ │   │  pipeline/ulpin.py             │
│  └───────────────────────────┘ │   └───────────────────────────────┘
│  ghost_floor_detector.py       │
│  (Isolation Forest)            │
└──────────────┬──────────────────┘
               │ reads/writes
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (pixelplot/data/)                    │
│                                                                       │
│  SoBo_3D_Master_Backend_Ready.csv  — 708 South Mumbai RERA records   │
│  mumbai_rera_projects.geojson      — per-floor 3D features            │
│  underground_surface.geojson       — basement / surface features      │
│  master_audit_ledger.json          — SHA-256 signed ownership ledger  │
│  dataset.py                        — CSV → GeoJSON + ULPIN + hash     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 3D Map Engine | MapLibre GL JS, OpenFreeMap tiles, Turf.js |
| Real-World Globe | CesiumJS (satellite imagery, world terrain, OSM 3D buildings) |
| AI Backend | Flask, Google GenAI SDK (Gemini 2.5 / 2.0 / 1.5 Flash), python-dotenv |
| ML Audit Engine | scikit-learn (Isolation Forest), pandas, NumPy |
| Building Pipeline | Flask, OpenCV, Pillow, Segment Anything (SAM), OSM footprint extraction |
| Data Layer | Pandas-driven CSV → GeoJSON build (`dataset.py`), JSON audit ledger |
| Frontend | Vanilla JavaScript, HTML5, CSS3, `marked.js` (markdown rendering), `qrcodejs` |
| Voice I/O | Web Speech API — `SpeechRecognition` + `SpeechSynthesisUtterance` (English / Hindi / Marathi) |
| Security | SHA-256 cryptographic hashing, session-based role gating (citizen / officer / super-admin) |

## 🚀 Build Roadmap

**Phase 1 — Cadastral Foundation**
*Goal: Get real RERA data onto a real 3D map.*
- Ingest and clean the South Mumbai RERA dataset (708 records)
- Build the vertical ULPIN grammar (`pipeline/ulpin.py`) and elevation math (`pipeline/geometry.py`)
- Generate per-floor GeoJSON and render it as extruded 3D buildings in MapLibre GL

**Phase 2 — AI-Assisted Discovery**
*Goal: Let anyone query the cadastre in plain language.*
- Stand up the Flask chat backend with Gemini-powered intent parsing and grounded response synthesis
- Wire chat responses to map actions (`FLY_TO_LOCATION`) and add multi-lingual voice input/output

**Phase 3 — Compliance & Trust**
*Goal: Make non-compliance detectable and ownership verifiable.*
- Train the Isolation Forest ghost-floor auditor on height/floor discrepancy features
- Build the claim submission → officer/admin verification → SHA-256 audit ledger workflow
- Ship the Digital Passbook and QR-based property passport

**Phase 4 — Site Verification**
*Goal: Bridge the map to the physical site.*
- Add camera-based AR overlay of live ULPIN identities
- Add LiDAR-style point-cloud elevation survey and the CesiumJS real satellite view
- Add on-demand new-building generation (OSM / CV / SAM footprint extraction) via the pipeline API

## 📁 Project Structure

```
PixelPlot/
├── start-all.bat                        # Launches all 3 services (chat API, build API, frontend)
├── pipeline/                            # 3D ULPIN generation engine
│   ├── ulpin.py                         # Vertical ULPIN ID grammar
│   ├── geometry.py                      # Floor/basement elevation math
│   ├── build.py                         # Shared GeoJSON feature assembly
│   ├── generate_building.py             # CLI: generate one building's GeoJSON
│   ├── api_server.py                    # Flask API (:5057) — "Add Building" panel
│   ├── footprint.py / osm_footprint.py  # Footprint extraction
│   ├── sam_footprint.py                 # Segment Anything (SAM) footprint extraction
│   ├── imagery.py                       # Imagery helpers
│   ├── viewer.html                      # Standalone pipeline viewer
│   ├── requirements.txt                 # numpy, opencv-python, Pillow, requests
│   └── requirements-sam.txt             # torch, torchvision, segment-anything (optional)
│
└── pixelplot/                           # Frontend + chat backend
    ├── index.html                       # Main 3D map app
    ├── login.html                       # Citizen / Government sign-in
    ├── passbook.html                    # Digital ULPIN Passbook certificate
    ├── test_portal.html                 # Zero-trust registration portal
    ├── serve.bat                        # Static frontend server (:8000)
    ├── ghost_floor_detector.py          # Root-level copy of the ML auditor
    ├── master_audit_ledger.json         # Signed ownership ledger (root mirror)
    │
    ├── assets/
    │   ├── logo.png
    │   ├── chatbot-avatar.png
    │   └── ulpin-assistant-sprite.png
    │
    ├── css/
    │   └── style.css                    # Full app styling (themes, panels, chatbot, sprite)
    │
    ├── js/
    │   ├── map.js                       # Core MapLibre GL 3D map logic
    │   ├── chatbot.js                   # AI chat widget (voice, markdown, map actions)
    │   ├── geostack-ui.js               # Audit ledger UI, role gating, tamper detection
    │   ├── ar-view.js                   # Camera-based AR overlay
    │   ├── lidar-survey.js              # Point-cloud elevation survey
    │   ├── satellite-view.js            # CesiumJS real satellite globe
    │   └── ulpin-assistant-sprite.js    # Animated map-section mascot
    │
    ├── data/
    │   ├── SoBo_3D_Master_Backend_Ready.csv   # 708-record master RERA dataset
    │   ├── dataset.py                         # CSV → GeoJSON + ULPIN + hash build script
    │   ├── mumbai_rera_projects.geojson       # Per-floor 3D building features
    │   ├── underground_surface.geojson        # Basement / surface features
    │   ├── marol_3d_cadastre.json             # Marol Cadastral Vault municipal-audit data
    │   ├── master_audit_ledger.json           # Signed ownership ledger (source of truth)
    │   ├── building-1.geojson
    │   ├── hubtown-serene-a.geojson
    │   └── neo-galaxy.geojson
    │
    └── chatbot-server/
        ├── app.py                       # Flask AI chat + audit API (:5000)
        ├── ghost_floor_detector.py      # Isolation Forest ghost-floor auditor
        ├── index.html                   # Standalone chatbot demo page
        ├── master_audit_ledger.json     # Signed ownership ledger (service-local mirror)
        ├── data/pending_claims.json     # Pending ownership claims queue
        └── .env                         # GEMINI_AI_KEYS (see Environment Variables)
```

## 📊 Data Sources

| Source | Description | Records |
|---|---|---|
| `pixelplot/data/SoBo_3D_Master_Backend_Ready.csv` | Master South Mumbai RERA property dataset — project, promoter, RERA ID, floors, heights, FSI, complaints/cases, coordinates | 708 |
| `pixelplot/data/mumbai_rera_projects.geojson` | Generated per-floor 3D building features (above-ground, podium, unit-level) derived from the CSV | Derived |
| `pixelplot/data/underground_surface.geojson` | Generated basement and at-grade surface features | Derived |
| `pixelplot/data/marol_3d_cadastre.json` | Marol Cadastral Vault municipal-audit fields (OC status, parking type, litigation risk) | Subset |
| `pixelplot/data/master_audit_ledger.json` | SHA-256 cryptographic integrity hashes, source of truth for the audit ledger | Derived |
| OpenStreetMap | Real building footprint geometry for the "Add Building" pipeline (`osm_footprint.py`) | External |
| Segment Anything (SAM) | Optional AI-based footprint segmentation from satellite imagery | External |

## ⚙️ Getting Started

### Prerequisites
- **Python 3.10+**
- A **Google Gemini API key** ([Google AI Studio](https://aistudio.google.com/apikey))
- Windows (the provided `.bat` launchers are Windows batch scripts — on macOS/Linux, run the equivalent `python` commands from each service's directory instead)

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd PixelPlot
```

### 2. Install backend dependencies
The chat backend (`pixelplot/chatbot-server/app.py`) currently has no dedicated `requirements.txt` — install its dependencies directly:
```bash
pip install flask flask-cors google-genai python-dotenv pandas numpy scikit-learn
```

The building-generation pipeline has its own requirements file:
```bash
pip install -r pipeline/requirements.txt
```

Optional — only if you want SAM-based footprint segmentation for the "Add Building" tool:
```bash
pip install -r pipeline/requirements-sam.txt
```

### 3. Configure environment variables
Create/edit `pixelplot/chatbot-server/.env`:
```env
GEMINI_AI_KEYS=your_gemini_api_key_here
```
You can pass multiple comma-separated keys for automatic rotation:
```env
GEMINI_AI_KEYS=key_one,key_two,key_three
```

> ⚠️ This file is currently committed to git — rotate any existing keys and add `.env` to `.gitignore` before pushing further changes.

### 4. Run everything
From the repository root:
```bash
start-all.bat
```
This launches, in separate windows:
| Service | Port | Purpose |
|---|---|---|
| `pixelplot/chatbot-server/app.py` | `5000` | AI chat, ghost-floor audit, claims & ledger API |
| `pipeline/api_server.py` | `5057` | On-demand building generation ("Add Building" panel) |
| Static frontend (`python -m http.server`) | `8000` | Serves `pixelplot/index.html` and friends |

It also opens `http://localhost:8000/login.html` automatically.

> 🔒 Voice input (`SpeechRecognition`) requires a secure context — `https://` or `localhost`/`127.0.0.1`. Opening `index.html` directly as a `file://` path, or serving it from any other hostname, will silently block the microphone. Always use the `:8000` server above (or `pixelplot/serve.bat` for frontend-only runs).

### Running services individually
```bash
# Chat / audit API
cd pixelplot/chatbot-server
python app.py

# Building-generation API
cd pipeline
python api_server.py

# Frontend
cd pixelplot
python -m http.server 8000
```

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- **Ministry of Rural Development, Department of Land Resources** — Smart India Hackathon 2026, Problem Statement 11
- **MapLibre GL JS** & **OpenFreeMap** — open-source 3D map rendering and tiles
- **CesiumJS** & **Cesium ion** — real-world 3D globe, terrain, and imagery
- **Google GenAI SDK (Gemini)** — natural-language property assistant
- **OpenStreetMap** & **Segment Anything (Meta AI)** — building footprint data and extraction
- **scikit-learn** — Isolation Forest anomaly detection for compliance auditing

---

<p align="center"><b>GeoStack — putting every floor of India's land records on the map, one verifiable ULPIN at a time.</b></p>
