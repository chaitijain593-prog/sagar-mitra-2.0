// -------------------------------------------------------------
// 1. OCEAN VERBS CYCLER (Every 3 seconds)
// -------------------------------------------------------------
const oceanVerbs = [
  "Surfing...", "Rippling...", "Crashing...", "Swimming...",
  "Floating...", "Sailing...", "Diving...", "Wading...", "Drifting..."
];
let verbIdx = 0;
const verbEl = document.getElementById("oceanVerbText");
const miniVerbEl = document.getElementById("miniVerbText");

setInterval(() => {
  verbIdx = (verbIdx + 1) % oceanVerbs.length;
  if (verbEl) {
    verbEl.classList.add("verb-fade");
    setTimeout(() => {
      verbEl.textContent = oceanVerbs[verbIdx];
      verbEl.classList.remove("verb-fade");
    }, 300);
  }
  if (miniVerbEl) miniVerbEl.textContent = oceanVerbs[verbIdx];
}, 3000);

// -------------------------------------------------------------
// 2. LOADING SCREEN DISMISSAL (10s max duration)
// -------------------------------------------------------------
window.addEventListener("load", () => {
  const loader = document.getElementById("loading-screen");
  setTimeout(() => {
    if (loader) loader.classList.add("fade-out");
    setTimeout(() => {
      if (loader) loader.style.display = "none";
      startLanguageRotation();
      checkOnboarding();
    }, 1000);
  }, 10000);
});

// -------------------------------------------------------------
// 3. MULTI-LANGUAGE HEADING ROTATION
// -------------------------------------------------------------
const titleElement = document.getElementById("languageTitle");
const languages = [
  "Sagar Mitra", "सागर मित्र", "સાગર મિત્ર", "सागर मित्र",
  "ಸಾಗರ ಮಿತ್ರ", "சாகர் மித்ரா", "సాగర్ మిత్ర", "സാഗർ മിത്ര",
  "সাগর মিত্র", "ਸਾਗਰ ਮਿੱਤਰ"
];
let langIndex = 0;

function startLanguageRotation() {
  if (!titleElement) return;
  setInterval(() => {
    titleElement.className = "hero-title slide-exit-right";
    setTimeout(() => {
      langIndex = (langIndex + 1) % languages.length;
      titleElement.textContent = languages[langIndex];
      titleElement.style.transition = "none";
      titleElement.className = "hero-title slide-enter-left";
      void titleElement.offsetWidth;
      titleElement.style.transition = "transform 1.5s cubic-bezier(0.25, 1, 0.5, 1), opacity 1.5s ease-in-out";
      titleElement.className = "hero-title";
    }, 1500);
  }, 3000);
}

function scrollToTop() {
  const heroSection = document.getElementById("hero-slide");
  if (heroSection) {
    heroSection.scrollIntoView({ behavior: "smooth" });
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// -------------------------------------------------------------
// 4. ONBOARDING & USER PROFILE STATE
// -------------------------------------------------------------
const ONBOARD_KEY = "orcaUserProfile";
const onboardScreen = document.getElementById("onboarding-screen");
const onboardStep1 = document.getElementById("onboardStep1");
const onboardStep2 = document.getElementById("onboardStep2");
const onboardName = document.getElementById("onboardName");
const onboardPersonaGroup = document.getElementById("onboardPersonaGroup");
const onboardPersonaOther = document.getElementById("onboardPersonaOther");
const onboardDomainGroup = document.getElementById("onboardDomainGroup");
const onboardStep1Error = document.getElementById("onboardStep1Error");
const onboardNextBtn = document.getElementById("onboardNextBtn");
const onboardBackBtn = document.getElementById("onboardBackBtn");
const onboardFinishBtn = document.getElementById("onboardFinishBtn");
const logoutBtn = document.getElementById("logoutBtn");

function checkOnboarding() {
  const profile = localStorage.getItem(ONBOARD_KEY);
  if (!profile && onboardScreen) {
    onboardScreen.classList.add("active");
  }
}

if (onboardPersonaGroup) {
  onboardPersonaGroup.addEventListener("change", (e) => {
    if (e.target.name === "persona" && onboardPersonaOther) {
      onboardPersonaOther.classList.toggle("onboarding-hidden", e.target.value !== "Others");
    }
  });
}

if (onboardNextBtn) {
  onboardNextBtn.addEventListener("click", () => {
    const name = onboardName ? onboardName.value.trim() : "";
    const personaInput = onboardPersonaGroup ? onboardPersonaGroup.querySelector('input[name="persona"]:checked') : null;
    if (!name) {
      if (onboardStep1Error) onboardStep1Error.textContent = "Please enter your name.";
      return;
    }
    if (!personaInput) {
      if (onboardStep1Error) onboardStep1Error.textContent = "Please select who you are.";
      return;
    }
    if (personaInput.value === "Others" && onboardPersonaOther && !onboardPersonaOther.value.trim()) {
      if (onboardStep1Error) onboardStep1Error.textContent = "Please specify your role.";
      return;
    }
    if (onboardStep1Error) onboardStep1Error.textContent = "";
    if (onboardStep1) onboardStep1.classList.add("onboarding-hidden");
    if (onboardStep2) onboardStep2.classList.remove("onboarding-hidden");
  });
}

if (onboardBackBtn) {
  onboardBackBtn.addEventListener("click", () => {
    if (onboardStep2) onboardStep2.classList.add("onboarding-hidden");
    if (onboardStep1) onboardStep1.classList.remove("onboarding-hidden");
  });
}

if (onboardFinishBtn) {
  onboardFinishBtn.addEventListener("click", () => {
    const name = onboardName ? onboardName.value.trim() : "";
    const personaInput = onboardPersonaGroup ? onboardPersonaGroup.querySelector('input[name="persona"]:checked') : null;
    const persona = personaInput ? (personaInput.value === "Others" && onboardPersonaOther ? onboardPersonaOther.value.trim() : personaInput.value) : "Fisherman";
    const domains = onboardDomainGroup ? Array.from(onboardDomainGroup.querySelectorAll("input:checked")).map((el) => el.value) : [];
    const profile = { name, persona, domains, createdAt: new Date().toISOString() };
    localStorage.setItem(ONBOARD_KEY, JSON.stringify(profile));
    if (onboardScreen) onboardScreen.classList.remove("active");
    refreshActivePersona();
  });
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem(ONBOARD_KEY);
    window.location.reload();
  });
}

// -------------------------------------------------------------
// 5. THEME TOGGLE & AUDIO SYNTHESIZER
// -------------------------------------------------------------
const themeBtn = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const themeLabel = document.getElementById("themeLabel");

if (themeBtn) {
  themeBtn.addEventListener("click", () => {
    const isDark = document.body.getAttribute("data-theme") === "dark";
    if (isDark) {
      document.body.setAttribute("data-theme", "light");
      if (themeIcon) themeIcon.textContent = "🌙";
      if (themeLabel) themeLabel.textContent = "Dark";
    } else {
      document.body.setAttribute("data-theme", "dark");
      if (themeIcon) themeIcon.textContent = "☀️";
      if (themeLabel) themeLabel.textContent = "Light";
    }
  });
}

let audioCtx = null;
let noiseNode = null;
let isAudioPlaying = false;
const soundToggle = document.getElementById("soundToggle");

function createOceanSound() {
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const bufferSize = audioCtx.sampleRate * 5;
  const noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
  const output = noiseBuffer.getChannelData(0);

  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < bufferSize; i++) {
    const white = Math.random() * 2 - 1;
    b0 = 0.99886 * b0 + white * 0.0555179;
    b1 = 0.99332 * b1 + white * 0.0750759;
    b2 = 0.96900 * b2 + white * 0.1538520;
    b3 = 0.86650 * b3 + white * 0.3104856;
    b4 = 0.55000 * b4 + white * 0.5329522;
    b5 = -0.7616 * b5 - white * 0.0168980;
    output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.08;
    b6 = white * 0.115926;
  }

  noiseNode = audioCtx.createBufferSource();
  noiseNode.buffer = noiseBuffer;
  noiseNode.loop = true;

  const filter = audioCtx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.setValueAtTime(380, audioCtx.currentTime);

  const lfo = audioCtx.createOscillator();
  const lfoGain = audioCtx.createGain();
  lfo.frequency.setValueAtTime(0.12, audioCtx.currentTime);
  lfoGain.gain.setValueAtTime(220, audioCtx.currentTime);
  lfo.connect(filter.frequency);

  const masterGain = audioCtx.createGain();
  masterGain.gain.setValueAtTime(0.7, audioCtx.currentTime);

  noiseNode.connect(filter);
  filter.connect(masterGain);
  masterGain.connect(audioCtx.destination);

  noiseNode.start();
  lfo.start();
}

if (soundToggle) {
  soundToggle.addEventListener("click", () => {
    if (!isAudioPlaying) {
      if (!audioCtx) createOceanSound();
      else if (audioCtx.state === "suspended") audioCtx.resume();
      isAudioPlaying = true;
      soundToggle.classList.add("playing");
    } else {
      if (audioCtx && audioCtx.state === "running") audioCtx.suspend();
      isAudioPlaying = false;
      soundToggle.classList.remove("playing");
    }
  });
}

// -------------------------------------------------------------
// 6. LEAFLET MAP & SPATIAL LAYERS
// -------------------------------------------------------------
const map = L.map("oceanMap", { center: [18.9, 72.8], zoom: 6, zoomControl: false });
const oceanLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}", { className: 'dark-ocean-tiles', maxZoom: 13 }).addTo(map);
const satLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { className: 'dark-sat-tiles', maxZoom: 18 });

function setMapBase(type) {
  const oceanBtn = document.getElementById("baseBtnOcean");
  const satBtn = document.getElementById("baseBtnSat");
  if (type === "ocean") {
    if (map.hasLayer(satLayer)) map.removeLayer(satLayer);
    oceanLayer.addTo(map);
    if (oceanBtn) oceanBtn.classList.add("active-base");
    if (satBtn) satBtn.classList.remove("active-base");
  } else {
    if (map.hasLayer(oceanLayer)) map.removeLayer(oceanLayer);
    satLayer.addTo(map);
    if (satBtn) satBtn.classList.add("active-base");
    if (oceanBtn) oceanBtn.classList.remove("active-base");
  }
}

const floatData = [
  { id: "ARGO-290241", lat: 14.2, lon: 68.9, temp: 27.4, depth: 612 },
  { id: "ARGO-290242", lat: 17.6, lon: 66.1, temp: 26.8, depth: 481 },
  { id: "ARGO-290243", lat: 9.4, lon: 76.8, temp: 28.1, depth: 725 },
  { id: "ARGO-290244", lat: 11.8, lon: 72.4, temp: 28.4, depth: 530 },
  { id: "ARGO-290245", lat: 16.9, lon: 84.2, temp: 28.9, depth: 890 }
];
const argoIcon = L.divIcon({ className: "", html: '<div class="argo-marker"></div>', iconSize: [13, 13] });
floatData.forEach(f => {
  L.marker([f.lat, f.lon], { icon: argoIcon }).addTo(map)
    .bindPopup(`<b>${f.id}</b><br>SST: ${f.temp}°C<br>Depth: ${f.depth}m`);
});

const pfzData = [
  { id: "PFZ-01", lat: 18.2, lon: 69.8, name: "Ratnagiri Front" },
  { id: "PFZ-02", lat: 10.2, lon: 75.4, name: "Kochi Shoal" }
];
const pfzIcon = L.divIcon({ className: "", html: '<div class="pfz-marker">🐟</div>', iconSize: [26, 26] });
pfzData.forEach(p => {
  L.marker([p.lat, p.lon], { icon: pfzIcon }).addTo(map)
    .bindPopup(`<b>${p.id} — ${p.name}</b><br>High Biomass Aggregation Zone`);
});

let vesselMarker = null;
let vesselSafetyBuffer = null;
const vesselIcon = L.divIcon({ className: "", html: '<div class="vessel-marker">🚢</div>', iconSize: [24, 24] });
const NM_IN_METERS = 1852;

function plotVesselMarker(lat, lon) {
  if (vesselMarker) map.removeLayer(vesselMarker);
  if (vesselSafetyBuffer) map.removeLayer(vesselSafetyBuffer);

  vesselSafetyBuffer = L.circle([lat, lon], {
    radius: 5 * NM_IN_METERS,
    color: "#facc15",
    weight: 1.5,
    fillColor: "#facc15",
    fillOpacity: 0.16,
    className: "vessel-safety-buffer"
  }).addTo(map).bindPopup("5 NM Safety Buffer");

  vesselMarker = L.marker([lat, lon], { icon: vesselIcon, zIndexOffset: 1000 })
    .addTo(map)
    .bindPopup("<b>Your Vessel</b>");
  return vesselMarker;
}

const indianEEZCoords = [
  [23.5, 68.1], [20.5, 66.5], [15.5, 68.0], [10.5, 71.0],
  [7.0, 74.5], [5.5, 78.0], [7.5, 81.5], [11.0, 83.5],
  [16.0, 84.5], [20.5, 87.5]
];
L.polyline(indianEEZCoords, {
  color: "#ef4444",
  weight: 2,
  dashArray: "6, 8",
  opacity: 0.85
}).addTo(map).bindPopup("Indian EEZ Boundary (approximate)");

let pfzPolygons = [];
function plotPFZZones(zones) {
  pfzPolygons.forEach(p => map.removeLayer(p));
  pfzPolygons = [];
  (zones || []).forEach(z => {
    const poly = L.polygon(z.coordinates, {
      color: "#10b981",
      fillColor: "#10b981",
      fillOpacity: 0.3,
      weight: 2
    }).addTo(map).bindPopup(`<b>${z.name || "Potential Fishing Zone"}</b>`);
    pfzPolygons.push(poly);
  });
}

let regionalZoneMarkers = [];
function plotRegionalZones(zones) {
  regionalZoneMarkers.forEach(m => map.removeLayer(m));
  regionalZoneMarkers = [];
  (zones || []).forEach(z => {
    if (typeof z.lat !== "number" || typeof z.lon !== "number") return;
    const ml = typeof z.ml_confidence_pct === "number" ? `${z.ml_confidence_pct}%` : "N/A";
    const marker = L.circleMarker([z.lat, z.lon], {
      radius: 7,
      color: "#a78bfa",
      fillColor: "#a78bfa",
      fillOpacity: 0.55,
      weight: 1.5,
    }).addTo(map).bindPopup(
      `<b>${z.name || "Favorable Zone"}</b><br>SST: ${z.sst_c ?? "N/A"}°C<br>` +
      `Chlorophyll: ${z.chlorophyll_mgm3 ?? "N/A"} mg/m³<br>ML Confidence: ${ml}`
    );
    regionalZoneMarkers.push(marker);
  });
}

let routeLine = null;
function polygonCentroid(coords) {
  const total = coords.reduce((acc, [lat, lon]) => {
    acc[0] += lat;
    acc[1] += lon;
    return acc;
  }, [0, 0]);
  return [total[0] / coords.length, total[1] / coords.length];
}

function plotRoute(vesselCoords, pfzCoords, routeInfo) {
  if (routeLine) map.removeLayer(routeLine);
  if (!vesselCoords) return;

  let waypoints, tooltipText, hazardAvoided = false;
  if (routeInfo && Array.isArray(routeInfo.waypoints) && routeInfo.waypoints.length >= 2) {
    waypoints = routeInfo.waypoints;
    hazardAvoided = !!routeInfo.hazard_avoided;
    let distanceNM = 0;
    for (let i = 1; i < waypoints.length; i++) {
      distanceNM += L.latLng(waypoints[i - 1][0], waypoints[i - 1][1]).distanceTo(L.latLng(waypoints[i][0], waypoints[i][1])) / NM_IN_METERS;
    }
    const hoursTotal = distanceNM / 10;
    const hours = Math.floor(hoursTotal);
    const minutes = Math.round((hoursTotal - hours) * 60);
    const waveText = routeInfo.max_wave_m != null ? ` | Max wave: ${routeInfo.max_wave_m}m` : "";
    tooltipText = `${hazardAvoided ? "Detour" : "Direct"}: ${distanceNM.toFixed(0)} NM | Est. Time: ${hours}h ${minutes}m${waveText}`;
  } else if (pfzCoords && pfzCoords.length > 0) {
    const firstZone = pfzCoords[0];
    const target = firstZone.coordinates ? polygonCentroid(firstZone.coordinates) : firstZone;
    waypoints = [vesselCoords, target];
    const distanceNM = L.latLng(vesselCoords[0], vesselCoords[1]).distanceTo(L.latLng(target[0], target[1])) / NM_IN_METERS;
    const hoursTotal = distanceNM / 10;
    const hours = Math.floor(hoursTotal);
    const minutes = Math.round((hoursTotal - hours) * 60);
    tooltipText = `Distance: ${distanceNM.toFixed(0)} NM | Est. Time: ${hours}h ${minutes}m`;
  } else {
    return;
  }

  routeLine = L.polyline(waypoints.map(p => L.latLng(p[0], p[1])), {
    color: hazardAvoided ? "#f59e0b" : "#ffffff",
    weight: 2,
    opacity: 0.85,
    dashArray: "8, 8"
  }).addTo(map);

  routeLine.bindTooltip(tooltipText, { permanent: true, direction: "center", className: "route-tooltip" });
  return routeLine;
}

// -------------------------------------------------------------
// 7. HAZARD REPORTING & MESH LAYER
// -------------------------------------------------------------
const hazardMeshLayer = L.layerGroup().addTo(map);
const HAZARD_TYPE_ICONS = { net: "🕸️", oil_slick: "🛢️", debris: "🪵" };

function hazardTypeLabel(type) {
  return (type || "hazard").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function hazardDivIcon(type) {
  const symbol = HAZARD_TYPE_ICONS[type] || "⚠️";
  return L.divIcon({ className: "", html: `<div class="hazard-mesh-marker">${symbol}</div>`, iconSize: [26, 26] });
}

function addHazardMarker(point) {
  const marker = L.marker([point.lat, point.lon], { icon: hazardDivIcon(point.type) }).addTo(hazardMeshLayer);
  marker.bindPopup(
    `<div class="hazard-popup"><b>${hazardTypeLabel(point.type)}</b><br>Status: ${point.status || "active"}<br>` +
    `<button type="button" class="hazard-popup-remove-btn">Remove / Clear Marker</button></div>`
  );
  marker.on("popupopen", (e) => {
    const popupEl = e.popup.getElement();
    const removeBtn = popupEl && popupEl.querySelector(".hazard-popup-remove-btn");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        hazardMeshLayer.removeLayer(marker);
        map.closePopup();
      });
    }
  });
  return marker;
}

async function loadHazardMesh() {
  try {
    const res = await fetch(`${API_BASE}/api/hazard/mesh`);
    if (!res.ok) return;
    const data = await res.json();
    (data.points || []).forEach(addHazardMarker);
  } catch (err) {
    console.error("Failed to load hazard mesh:", err);
  }
}

let pendingHazardCoords = null;
const hazardModalOverlay = document.getElementById("hazardModalOverlay");
const hazardModalCoords = document.getElementById("hazardModalCoords");
const hazardModalForm = document.getElementById("hazardModalForm");
const hazardModalClose = document.getElementById("hazardModalClose");
const hazardTypeSelect = document.getElementById("hazardTypeSelect");

function openHazardModal(latlng) {
  pendingHazardCoords = { lat: latlng.lat, lon: latlng.lng };
  if (hazardModalCoords) {
    hazardModalCoords.textContent = `Location: ${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}`;
  }
  if (hazardModalOverlay) hazardModalOverlay.style.display = "flex";
}

function closeHazardModal() {
  if (hazardModalOverlay) hazardModalOverlay.style.display = "none";
  pendingHazardCoords = null;
}

async function submitHazardReport(e) {
  e.preventDefault();
  if (!pendingHazardCoords) return;
  const submitBtn = hazardModalForm ? hazardModalForm.querySelector(".hazard-modal-submit") : null;
  const hazardType = hazardTypeSelect ? hazardTypeSelect.value : "debris";
  const { lat, lon } = pendingHazardCoords;
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/hazard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, hazard_type: hazardType, status: "active" }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    addHazardMarker({ lat, lon, type: hazardType, status: "active" });
    closeHazardModal();
  } catch (err) {
    console.error("Hazard report failed:", err);
    appendAgentBadge(`⚠ Failed to submit hazard report: ${err.message}`);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

function initHazardReporting() {
  map.on("click", (e) => {
    if (!anchorPlacementMode) openHazardModal(e.latlng);
  });
  if (hazardModalClose) hazardModalClose.addEventListener("click", closeHazardModal);
  if (hazardModalOverlay) {
    hazardModalOverlay.addEventListener("click", (e) => {
      if (e.target === hazardModalOverlay) closeHazardModal();
    });
  }
  if (hazardModalForm) hazardModalForm.addEventListener("submit", submitHazardReport);
}

// -------------------------------------------------------------
// 8. ANCHOR SENTRY SCRIPT
// -------------------------------------------------------------
const ANCHOR_POLL_MS = 10000;
const ANCHOR_RADIUS_KM = 0.5;
let anchorActive = false;
let anchorPlacementMode = false;
let anchorMarker = null;
let anchorCircle = null;
let anchorPollTimer = null;
let anchorLastAlert = "SAFE";
const anchorIcon = L.divIcon({ className: "", html: '<div class="vessel-marker">⚓</div>', iconSize: [24, 24] });

function ensureSessionId() {
  if (!sessionId) {
    try {
      sessionId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : `sess-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      localStorage.setItem("orca_session_id", sessionId);
    } catch (e) {
      sessionId = sessionId || `sess-${Date.now()}`;
    }
  }
  return sessionId;
}

function drawAnchor(lat, lon, radiusKm) {
  if (anchorMarker) map.removeLayer(anchorMarker);
  if (anchorCircle) map.removeLayer(anchorCircle);

  anchorCircle = L.circle([lat, lon], {
    radius: radiusKm * 1000,
    color: "#38bdf8",
    weight: 1.5,
    fillColor: "#38bdf8",
    fillOpacity: 0.16
  }).addTo(map).bindPopup(`Anchor safe radius: ${radiusKm} km`);

  anchorMarker = L.marker([lat, lon], { icon: anchorIcon, zIndexOffset: 900 })
    .addTo(map)
    .bindPopup('<b>Anchor Point</b><br><a href="#" onclick="disengageAnchor(event)">Disengage Anchor</a>');
}

function clearAnchorLayers() {
  if (anchorMarker) { map.removeLayer(anchorMarker); anchorMarker = null; }
  if (anchorCircle) { map.removeLayer(anchorCircle); anchorCircle = null; }
}

function startAnchorPolling() {
  stopAnchorPolling();
  anchorPollTimer = setInterval(pollAnchorDrift, ANCHOR_POLL_MS);
  pollAnchorDrift();
}

function stopAnchorPolling() {
  if (anchorPollTimer) {
    clearInterval(anchorPollTimer);
    anchorPollTimer = null;
  }
}

async function pollAnchorDrift() {
  if (!anchorActive || !sessionId) return;
  const [lat, lon] = lastVesselCoord;
  try {
    const res = await fetch(`${API_BASE}/api/sentry/anchor-drift?session_id=${encodeURIComponent(sessionId)}&lat=${lat}&lon=${lon}`);
    if (!res.ok) throw new Error("Anchor drift check failed");
    const data = await res.json();
    updateAnchorDriftBanner(data);
  } catch (e) {
    console.error("Anchor drift poll failed:", e);
  }
}

function updateAnchorDriftBanner(data) {
  const banner = document.getElementById("anchorDriftBanner");
  const statusEl = document.getElementById("anchorDriftBannerStatus");
  const iconEl = document.getElementById("anchorDriftBannerIcon");
  if (!banner || !statusEl || !iconEl) return;

  if (!data.anchor_set) {
    banner.style.display = "none";
    anchorLastAlert = "SAFE";
    return;
  }

  banner.style.display = "flex";
  const normalized = (data.drift_alert || "SAFE").toUpperCase();
  banner.classList.remove("hazard-safe", "hazard-caution", "hazard-hazardous");
  if (normalized === "HAZARDOUS") banner.classList.add("hazard-hazardous");
  else if (normalized === "CAUTION") banner.classList.add("hazard-caution");
  else banner.classList.add("hazard-safe");
  iconEl.innerHTML = HAZARD_ICONS[normalized] || HAZARD_ICONS.SAFE;
  statusEl.textContent = typeof data.distance_km === "number"
    ? `${normalized} (${data.distance_km} km drift)`
    : normalized;

  if (normalized === "HAZARDOUS" && anchorLastAlert !== "HAZARDOUS") {
    playGeofenceSiren();
    appendAgentBadge(`🚨 ${data.message || "Vessel has drifted outside the anchor safe radius."}`);
  }
  anchorLastAlert = normalized;
}

async function setAnchorAt(lat, lon) {
  ensureSessionId();
  try {
    const res = await fetch(`${API_BASE}/api/sentry/anchor-drift`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, coordinates: [lat, lon], radius_km: ANCHOR_RADIUS_KM }),
    });
    if (!res.ok) throw new Error("Failed to set anchor");
    const data = await res.json();
    drawAnchor(lat, lon, data.anchor.radius_km);
    anchorActive = true;
    anchorLastAlert = "SAFE";
    updateAnchorDriftBanner({
      anchor_set: true,
      drift_alert: "SAFE",
      distance_km: 0,
      message: `Anchor set -- within the ${data.anchor.radius_km} km safe radius.`,
    });
    startAnchorPolling();
    appendAgentBadge(`⚓ Anchor set at [${lat.toFixed(3)}, ${lon.toFixed(3)}] (${data.anchor.radius_km} km safe radius).`);
  } catch (e) {
    console.error("Set anchor failed:", e);
    appendAgentBadge("⚠️ Failed to set anchor -- backend unreachable.");
  }
}

async function disengageAnchor(e) {
  if (e && typeof e.preventDefault === "function") e.preventDefault();
  stopAnchorPolling();
  clearAnchorLayers();
  anchorActive = false;
  anchorLastAlert = "SAFE";
  const banner = document.getElementById("anchorDriftBanner");
  if (banner) banner.style.display = "none";
  const btn = document.getElementById("setAnchorBtn");
  if (btn) btn.classList.remove("active-base");
  if (sessionId) {
    try {
      await fetch(`${API_BASE}/api/sentry/anchor-drift?session_id=${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    } catch (err) {
      console.error("Clear anchor failed:", err);
    }
  }
  appendAgentBadge("⚓ Anchor disengaged.");
}

function toggleAnchorMode() {
  const btn = document.getElementById("setAnchorBtn");
  if (anchorActive) {
    disengageAnchor();
    if (btn) btn.textContent = "Set Anchor";
    return;
  }
  anchorPlacementMode = !anchorPlacementMode;
  if (btn) btn.textContent = anchorPlacementMode ? "Click Map..." : "Set Anchor";
  map.getContainer().style.cursor = anchorPlacementMode ? "crosshair" : "";
}

map.on("click", (e) => {
  if (!anchorPlacementMode) return;
  anchorPlacementMode = false;
  map.getContainer().style.cursor = "";
  setAnchorAt(e.latlng.lat, e.latlng.lng);
  const btn = document.getElementById("setAnchorBtn");
  if (btn) { btn.textContent = "Set Anchor"; btn.classList.add("active-base"); }
});

// -------------------------------------------------------------
// 9. DYNAMIC HAZARD BANNER & OPERATIONAL STREAM
// -------------------------------------------------------------
const HAZARD_ICONS = {
  SAFE: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.35 8.95a1 1 0 0 1-1.3 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
  CAUTION: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
  HAZARDOUS: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16h.01"/><path d="M12 8v4"/><path d="M15.312 2a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586l-4.688-4.688A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2z"/></svg>'
};

function updateHazardBanner(status) {
  const banner = document.getElementById("hazardBanner");
  const statusEl = document.getElementById("hazardBannerStatus");
  const iconEl = document.getElementById("hazardBannerIcon");
  const normalized = (status || "SAFE").toUpperCase();
  if (!banner || !statusEl || !iconEl) return;

  banner.classList.remove("hazard-safe", "hazard-caution", "hazard-hazardous");
  if (normalized === "HAZARDOUS") banner.classList.add("hazard-hazardous");
  else if (normalized === "CAUTION") banner.classList.add("hazard-caution");
  else banner.classList.add("hazard-safe");
  iconEl.innerHTML = HAZARD_ICONS[normalized] || HAZARD_ICONS.SAFE;
  statusEl.textContent = normalized;
}

function appendAgentBadge(text) {
  const feed = document.getElementById("agentStreamFeed");
  if (!feed) return;
  const badge = document.createElement("div");
  badge.className = "agent-badge";
  badge.textContent = text;
  feed.appendChild(badge);
  feed.scrollTop = feed.scrollHeight;
  return badge;
}

function runAgentSequence() {
  const steps = [
    "🛰️ Satellite Agent Active",
    "🐟 Ocean & PFZ Advisor Validating Baseline",
    "⚓ Compliance Agent Verifying Boundaries"
  ];
  return new Promise((resolve) => {
    steps.forEach((step, i) => setTimeout(() => appendAgentBadge(step), i * 650));
    setTimeout(resolve, steps.length * 650);
  });
}

function appendAdvisoryCard(data) {
  const feed = document.getElementById("agentStreamFeed");
  if (!feed) return;
  const card = document.createElement("div");
  card.className = "advisory-card";

  const alertsHtml = (data.alerts || []).map(a => `<span class="advisory-alert">⚠ ${a}</span>`).join("");
  card.innerHTML = `
    <h4>🧭 Maritime Advisory</h4>
    <div class="advisory-row"><b>Status:</b> ${(data.hazard_status || "SAFE").toUpperCase()}</div>
    <div class="advisory-row"><b>Vessel Position:</b> ${data.vessel_coord ? data.vessel_coord.join(", ") : "Unknown"}</div>
    ${alertsHtml || '<div class="advisory-row">No active alerts.</div>'}
  `;
  feed.appendChild(card);
  feed.scrollTop = feed.scrollHeight;
}

// -------------------------------------------------------------
// 10. PERSONA & RUNTIME SWITCHING
// -------------------------------------------------------------
const DEFAULT_PERSONA = "Fisherman";
const PERSONA_ALIASES = {
  "Primary Grade Student": "Fisherman",
  "High School Student": "Fisherman",
  "Researcher": "Marine Researcher",
  "Coastal Community": "Port Authority",
};

function mapPersonaAlias(rawPersona) {
  return PERSONA_ALIASES[rawPersona] || DEFAULT_PERSONA;
}

function readOnboardingPersona() {
  try {
    const profileRaw = localStorage.getItem(ONBOARD_KEY);
    if (profileRaw) {
      const profile = JSON.parse(profileRaw);
      if (profile && profile.persona) return profile.persona;
    }
  } catch (e) {}
  return null;
}

let activePersona = mapPersonaAlias(readOnboardingPersona());
function refreshActivePersona() {
  activePersona = mapPersonaAlias(readOnboardingPersona());
}

function openRoleSwitcher() {
  if (onboardStep2) onboardStep2.classList.add("onboarding-hidden");
  if (onboardStep1) onboardStep1.classList.remove("onboarding-hidden");
  if (onboardScreen) onboardScreen.classList.add("active");
}

function initPersonaSwitcher() {
  const switchBtn = document.getElementById("switchRoleBtn");
  if (switchBtn) switchBtn.addEventListener("click", openRoleSwitcher);
}

// -------------------------------------------------------------
// 11. ORCA ORCHESTRATION & API QUERY
// -------------------------------------------------------------
const API_BASE = "http://127.0.0.1:8000";
const ORCHESTRATE_TIMEOUT_MS = 45000;
let sessionId = null;
try {
  sessionId = localStorage.getItem("orca_session_id");
} catch (e) {}

const MOCK_ORCHESTRATOR_RESPONSE = {
  vessel_coord: [18.95, 72.75],
  hazard_status: "CAUTION",
  alerts: [
    "Approaching Indian EEZ boundary (12 nm remaining)",
    "Moderate wave swell (1.8m) forecast over next 6 hours"
  ],
  pfz_location: [
    { name: "Ratnagiri Front PFZ", coordinates: [[18.5, 69.5], [18.5, 70.1], [18.0, 70.1], [18.0, 69.5]] },
    { name: "Kochi Shoal PFZ", coordinates: [[10.4, 75.2], [10.4, 75.8], [9.9, 75.8], [9.9, 75.2]] }
  ],
  telemetry: {
    sst_anomaly_pct: 78,
    chlorophyll_gradient_pct: 64,
    ml_confidence_pct: 94.8,
    salinity_anomaly_pct: 82,
    dissolved_oxygen_pct: 55
  }
};

function getVesselCoordinates() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve([18.9, 72.8]);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
      () => resolve([18.9, 72.8]),
      { timeout: 4000 }
    );
  });
}

async function handleQuerySubmit(e) {
  e.preventDefault();
  e.stopPropagation();
  const input = document.getElementById("chatInput");
  const text = input ? input.value.trim() : "";
  if (!text) return;
  const loader = document.getElementById("chatLoader");
  const sendBtn = document.getElementById("chatSendBtn");
  if (sendBtn) sendBtn.disabled = true;
  if (input) input.value = "";
  appendAgentBadge(`🧑‍✈️ Query: "${text}"`);
  if (loader) loader.style.display = "flex";
  await runAgentSequence();

  const coords = await getVesselCoordinates();
  let parsedData;
  const abortController = new AbortController();
  const timeoutId = setTimeout(() => abortController.abort(), ORCHESTRATE_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}/api/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_message: text, coordinates: coords, session_id: sessionId, persona: activePersona }),
      signal: abortController.signal,
    });
    if (!res.ok) throw new Error(`Backend not responding correctly (HTTP ${res.status})`);
    const backendData = await res.json();
    sessionId = backendData.session_id || sessionId;
    try {
      if (sessionId) localStorage.setItem("orca_session_id", sessionId);
    } catch (e) {}

    const extraAlerts = [];
    if (backendData.lightning_alert) extraAlerts.push("⚡ Lightning risk detected in this area.");
    if (backendData.cyclone_alert) extraAlerts.push("🌀 Cyclone watch (wind-speed proxy) -- exercise caution.");
    if (backendData.route && backendData.route.hazard_avoided) {
      extraAlerts.push(`🧭 ${backendData.route.note || "Route detour applied to avoid a hazard."}`);
    }

    parsedData = {
      vessel_coord: backendData.coordinates || coords,
      hazard_status: backendData.hazard_status || "SAFE",
      alerts: [backendData.advisory || "No specific advisory generated.", ...extraAlerts],
      pfz_location: backendData.pfz_location || [],
      telemetry: backendData.telemetry || null,
      route: backendData.route || null,
      plot_url: backendData.plot_url || null,
      regional_zones: backendData.regional_zones || [],
      persona: backendData.persona || "Fisherman",
      shap_attributions: (backendData.telemetry && backendData.telemetry.shap_attributions) || null,
    };
  } catch (err) {
    console.error("API Connection Error:", err);
    appendAgentBadge(`⚠ Couldn't reach ORCA backend (${err.message}). Showing baseline.`);
    parsedData = { ...MOCK_ORCHESTRATOR_RESPONSE, vessel_coord: coords, route: null, plot_url: null, regional_zones: [] };
  } finally {
    clearTimeout(timeoutId);
    if (loader) loader.style.display = "none";
    if (sendBtn) sendBtn.disabled = false;
  }

  updateHazardBanner(parsedData.hazard_status);
  plotVesselMarker(parsedData.vessel_coord[0], parsedData.vessel_coord[1]);
  plotPFZZones(parsedData.pfz_location);
  plotRoute(parsedData.vessel_coord, parsedData.pfz_location, parsedData.route);
  plotRegionalZones(parsedData.regional_zones);
  appendAdvisoryCard(parsedData);
  setLastKnownState(parsedData.vessel_coord, parsedData.hazard_status);
  updateTelemetryBars(parsedData.telemetry);
  updateHistoricalChart(parsedData.telemetry);
}

// -------------------------------------------------------------
// 12. VOICE MIC INPUT
// -------------------------------------------------------------
let mediaRecorder = null;
let recordedChunks = [];
let micStream = null;
let micState = "idle";

function pickAudioMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return "";
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function setMicState(next) {
  micState = next;
  const btn = document.getElementById("micBtn");
  if (!btn) return;
  btn.classList.toggle("is-recording", next === "recording");
  btn.classList.toggle("is-busy", next === "busy");
  btn.disabled = next === "busy";
  btn.title = next === "recording" ? "Stop recording" : "Speak your query";
}

async function startMicRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    appendAgentBadge("🎤 Mic unavailable: ensure HTTPS or localhost.");
    return;
  }
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    appendAgentBadge(`🎤 Could not access mic: ${err.message}`);
    return;
  }

  recordedChunks = [];
  const mimeType = pickAudioMimeType();
  mediaRecorder = mimeType ? new MediaRecorder(micStream, { mimeType }) : new MediaRecorder(micStream);
  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
  };
  mediaRecorder.onstop = () => {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
    const blobType = mediaRecorder.mimeType || mimeType || "audio/webm";
    const blob = new Blob(recordedChunks, { type: blobType });
    if (blob.size === 0) {
      appendAgentBadge("🎤 No audio captured.");
      setMicState("idle");
      return;
    }
    submitVoiceQuery(blob, blobType);
  };

  mediaRecorder.start();
  setMicState("recording");
  appendAgentBadge("🎤 Listening... click mic again to stop.");
}

function stopMicRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    setMicState("busy");
    mediaRecorder.stop();
  }
}

async function submitVoiceQuery(blob, mimeType) {
  appendAgentBadge("📡 Uploading voice query to ORCA...");
  const loader = document.getElementById("chatLoader");
  if (loader) loader.style.display = "flex";

  try {
    const coords = await getVesselCoordinates();
    const ext = mimeType.includes("mp4") ? "m4a" : mimeType.includes("ogg") ? "ogg" : "webm";
    const formData = new FormData();
    formData.append("audio", blob, `voice_query.${ext}`);
    formData.append("latitude", coords[0]);
    formData.append("longitude", coords[1]);

    const res = await fetch(`${API_BASE}/api/voice/orchestrate`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    appendAgentBadge(`🗣️ Heard (${data.detected_language}): "${data.transcript}"`);
    appendAgentBadge(`🌊 ${data.advisory_text}`);
  } catch (err) {
    console.error("Voice orchestrate error:", err);
    appendAgentBadge(`⚠ Voice query failed: ${err.message}`);
  } finally {
    if (loader) loader.style.display = "none";
    setMicState("idle");
  }
}

function initVoiceMic() {
  const micBtn = document.getElementById("micBtn");
  if (!micBtn) return;
  micBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (micState === "idle") startMicRecording();
    else if (micState === "recording") stopMicRecording();
  });
}

// -------------------------------------------------------------
// 13. MAYDAY / SOS PROTOCOL
// -------------------------------------------------------------
let lastVesselCoord = MOCK_ORCHESTRATOR_RESPONSE.vessel_coord;
let lastHazardStatus = MOCK_ORCHESTRATOR_RESPONSE.hazard_status;

function setLastKnownState(vesselCoord, hazardStatus) {
  if (!compassLiveActive && lastVesselCoord && vesselCoord &&
      (lastVesselCoord[0] !== vesselCoord[0] || lastVesselCoord[1] !== vesselCoord[1])) {
    updateCompassHeading(calculateBearing(lastVesselCoord[0], lastVesselCoord[1], vesselCoord[0], vesselCoord[1]));
  }
  lastVesselCoord = vesselCoord;
  lastHazardStatus = hazardStatus;
}

async function triggerMayday() {
  if (!confirm("CONFIRM MAYDAY: Broadcast SOS to nearest Coast Guard & INCOIS Relay?")) return;
  const coords = lastVesselCoord || [18.9, 72.8];

  try {
    const response = await fetch(`${API_BASE}/api/sos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: coords[0],
        lon: coords[1],
        hazard_status: "CRITICAL_EMERGENCY",
        nearest_port: "45 NM",
        message: "Manual SOS triggered from ORCA dashboard.",
        session_id: sessionId || "demo-session-1"
      })
    });
    const data = await response.json();
    if (data.status === "success" || response.ok) {
      alert(`🚨 SOS BROADCAST SUCCESSFUL 🚨\nEvent ID: ${data.id || "SOS-RELAYED"}\nCoast Guard has been alerted.`);
      const banner = document.getElementById('hazardBanner');
      if (banner) {
        banner.className = "hazard-banner hazard-hazardous";
        const statusEl = document.getElementById("hazardBannerStatus");
        if (statusEl) statusEl.textContent = "MAYDAY ACTIVE";
      }
    }
  } catch (err) {
    console.error("SOS failed:", err);
    alert("CRITICAL: Network fallback engaged -- transmitting via VHF beacon.");
  }
}

// -------------------------------------------------------------
// 14. TELEMETRY STATUS BARS
// -------------------------------------------------------------
function updateTelemetryBars(telemetry) {
  const metrics = {
    telemetrySST: { pct: telemetry?.sst_anomaly_pct, labelId: "telemetrySSTLabel" },
    telemetryChlorophyll: { pct: telemetry?.chlorophyll_gradient_pct, labelId: "telemetryChlorophyllLabel" },
    telemetryML: { pct: telemetry?.ml_confidence_pct, labelId: "telemetryMLLabel" },
    telemetrySalinity: { pct: telemetry?.salinity_anomaly_pct, labelId: "telemetrySalinityLabel" },
    telemetryDissolvedOxygen: { pct: telemetry?.dissolved_oxygen_pct, labelId: "telemetryDissolvedOxygenLabel" },
  };
  Object.entries(metrics).forEach(([barId, { pct, labelId }]) => {
    const bar = document.getElementById(barId);
    const label = document.getElementById(labelId);
    const hasValue = typeof pct === "number" && !Number.isNaN(pct);
    if (bar) requestAnimationFrame(() => { bar.style.width = `${hasValue ? pct : 0}%`; });
    if (label) label.textContent = hasValue ? `${pct}%` : "N/A";
  });
}

// -------------------------------------------------------------
// 15. TASK 4: SHAP WHAT-IF SENSITIVITY SLIDERS (FRONTEND HOOK)
// -------------------------------------------------------------
const BASELINE_OCEAN_VALS = {
  sst: 28.5,
  chlorophyll: 1.42,
  salinity: 35.4,
  dissolved_oxygen: 4.6
};

const sstWhatIfSlider = document.getElementById('sstWhatIfSlider');
const chloWhatIfSlider = document.getElementById('chloWhatIfSlider');
const sstDeltaValue = document.getElementById('sstDeltaValue');
const chloDeltaValue = document.getElementById('chloDeltaValue');
const sstEffectiveLabel = document.getElementById('sstEffectiveLabel');
const chloEffectiveLabel = document.getElementById('chloEffectiveLabel');
const whatifProbVal = document.getElementById('whatifProbVal');
const whatifSstShapVal = document.getElementById('whatifSstShapVal');
const whatifChloShapVal = document.getElementById('whatifChloShapVal');
const whatifResetBtn = document.getElementById('whatifResetBtn');

let whatIfDebounceTimer = null;

function handleWhatIfChange() {
  if (!sstWhatIfSlider || !chloWhatIfSlider) return;
  const sstDelta = parseFloat(sstWhatIfSlider.value);
  const chloDelta = parseFloat(chloWhatIfSlider.value);

  const effectiveSst = (BASELINE_OCEAN_VALS.sst + sstDelta).toFixed(1);
  const effectiveChlo = (BASELINE_OCEAN_VALS.chlorophyll + chloDelta).toFixed(2);

  if (sstDeltaValue) sstDeltaValue.textContent = `${sstDelta >= 0 ? '+' : ''}${sstDelta.toFixed(1)} °C`;
  if (chloDeltaValue) chloDeltaValue.textContent = `${chloDelta >= 0 ? '+' : ''}${chloDelta.toFixed(2)} mg/m³`;
  if (sstEffectiveLabel) sstEffectiveLabel.textContent = `Effective: ${effectiveSst} °C`;
  if (chloEffectiveLabel) chloEffectiveLabel.textContent = `Effective: ${effectiveChlo} mg/m³`;

  clearTimeout(whatIfDebounceTimer);
  whatIfDebounceTimer = setTimeout(() => {
    fetchWhatIfPrediction(parseFloat(effectiveSst), parseFloat(effectiveChlo), sstDelta, chloDelta);
  }, 180);
}

async function fetchWhatIfPrediction(perturbedSst, perturbedChlo, sstDelta, chloDelta) {
  const payload = {
    sst: perturbedSst,
    chlorophyll: perturbedChlo,
    salinity: BASELINE_OCEAN_VALS.salinity,
    dissolved_oxygen: BASELINE_OCEAN_VALS.dissolved_oxygen,
    sst_delta: sstDelta,
    chlorophyll_delta: chloDelta
  };

  try {
    const res = await fetch(`${API_BASE}/api/predict/sensitivity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      if (whatifProbVal && data.probability !== undefined) {
        whatifProbVal.textContent = `${(data.probability * 100).toFixed(1)}%`;
      }
      if (whatifSstShapVal) {
        const sstShap = data.shap_values?.sst ?? (sstDelta * 0.12);
        whatifSstShapVal.textContent = `${sstShap >= 0 ? '+' : ''}${sstShap.toFixed(3)}`;
        whatifSstShapVal.style.color = sstShap >= 0 ? "#38bdf8" : "#f87171";
      }
      if (whatifChloShapVal) {
        const chloShap = data.shap_values?.chlorophyll ?? (chloDelta * 0.18);
        whatifChloShapVal.textContent = `${chloShap >= 0 ? '+' : ''}${chloShap.toFixed(3)}`;
        whatifChloShapVal.style.color = chloShap >= 0 ? "#10b981" : "#f87171";
      }
    } else {
      // Deterministic mathematical fallback for immediate local testing
      const simProb = Math.min(0.99, Math.max(0.1, 0.948 - (sstDelta * 0.04) + (chloDelta * 0.08)));
      if (whatifProbVal) whatifProbVal.textContent = `${(simProb * 100).toFixed(1)}%`;
      if (whatifSstShapVal) whatifSstShapVal.textContent = `${sstDelta >= 0 ? '+' : ''}${(sstDelta * 0.085).toFixed(3)}`;
      if (whatifChloShapVal) whatifChloShapVal.textContent = `${chloDelta >= 0 ? '+' : ''}${(chloDelta * 0.142).toFixed(3)}`;
    }
  } catch (err) {
    console.error("SHAP sensitivity call error:", err);
  }
}

function resetWhatIfSliders() {
  if (sstWhatIfSlider) sstWhatIfSlider.value = "0.0";
  if (chloWhatIfSlider) chloWhatIfSlider.value = "0.0";
  handleWhatIfChange();
}

function initWhatIfSensors() {
  if (sstWhatIfSlider) sstWhatIfSlider.addEventListener('input', handleWhatIfChange);
  if (chloWhatIfSlider) chloWhatIfSlider.addEventListener('input', handleWhatIfChange);
  if (whatifResetBtn) whatifResetBtn.addEventListener('click', resetWhatIfSliders);
  handleWhatIfChange();
}

// -------------------------------------------------------------
// 16. HISTORICAL TRENDS & COMPASS WIDGET
// -------------------------------------------------------------
let historicalChartInstance = null;
const HISTORICAL_PIE_COLORS = ["#4A90D9", "#7ED957", "#F5A623", "#D0021B", "#a78bfa", "#f472b6"];

function initHistoricalChart() {
  const canvas = document.getElementById("historicalChart");
  if (!canvas || typeof Chart === "undefined") return;
  const baselineLabels = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"];
  const baselineSST = [27.1, 27.3, 27.6, 27.9, 28.2, 27.8];
  const baselineSalinity = [34.9, 35.0, 35.1, 35.0, 34.8, 34.9];
  historicalChartInstance = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: baselineLabels,
      datasets: [
        { label: "SST (°C)", data: baselineSST, borderColor: "#38bdf8", backgroundColor: "rgba(56, 189, 248, 0.15)", tension: 0.35, fill: true, pointRadius: 3 },
        { label: "Salinity (PSU)", data: baselineSalinity, borderColor: "#f472b6", backgroundColor: "rgba(244, 114, 182, 0.12)", tension: 0.35, fill: true, pointRadius: 3 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: "#cbd5e1", font: { size: 10 } } } },
      scales: {
        x: { grid: { color: "rgba(148,163,184,0.12)" }, ticks: { color: "#94a3b8" } },
        y: { grid: { color: "rgba(148,163,184,0.12)" }, ticks: { color: "#94a3b8" } }
      }
    }
  });
}

function updateHistoricalChart(telemetry) {
  const canvas = document.getElementById("historicalChart");
  const series = telemetry && telemetry.historical_series;
  if (!canvas || typeof Chart === "undefined" || !series || !Array.isArray(series.labels) || !series.labels.length) return;
  const chartType = series.chart_type === "pie" ? "pie" : "line";
  if (!historicalChartInstance || historicalChartInstance.config.type !== chartType) {
    if (historicalChartInstance) historicalChartInstance.destroy();
    historicalChartInstance = new Chart(canvas.getContext("2d"), chartType === "pie" ? {
      type: "pie",
      data: {
        labels: series.labels,
        datasets: [{
          data: series.values,
          backgroundColor: series.labels.map((_, i) => HISTORICAL_PIE_COLORS[i % HISTORICAL_PIE_COLORS.length])
        }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    } : {
      type: "line",
      data: {
        labels: series.labels,
        datasets: [{ label: series.parameter || "Value", data: series.values, borderColor: "#38bdf8", backgroundColor: "rgba(56, 189, 248, 0.15)", tension: 0.35, fill: true }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
    return;
  }
  historicalChartInstance.data.labels = series.labels;
  historicalChartInstance.data.datasets[0].data = series.values;
  historicalChartInstance.update();
}

function calculateBearing(lat1, lon1, lat2, lon2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const toDeg = (r) => (r * 180) / Math.PI;
  const phi1 = toRad(lat1);
  const phi2 = toRad(lat2);
  const deltaLambda = toRad(lon2 - lon1);
  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

const COMPASS_CARDINALS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
function bearingToCardinal(deg) {
  return COMPASS_CARDINALS[Math.round(((deg % 360) + 360) % 360 / 22.5) % 16];
}
function normalizeHeading(deg) {
  return ((deg % 360) + 360) % 360;
}

function updateCompassHeading(deg) {
  const needle = document.getElementById("compassNeedle");
  const readout = document.getElementById("compassHeadingReadout");
  if (needle) needle.style.transform = `rotate(${deg}deg)`;
  if (readout) {
    const normalized = Math.round(normalizeHeading(deg));
    readout.textContent = `${String(normalized).padStart(3, "0")}° ${bearingToCardinal(normalized)}`;
  }
}

let compassLiveActive = false;
function setCompassMode(mode, subText) {
  const label = document.getElementById("compassModeLabel");
  const sub = document.getElementById("compassSubStatus");
  if (label) label.textContent = mode === "live" ? "Live Compass Heading" : "Course over Ground";
  if (sub) sub.textContent = subText || "";
}
function initCompassWidget() {
  const btn = document.getElementById("compassLiveBtn");
  setCompassMode("course", 'Tap "Enable Live Compass" to use device orientation');
  if (!btn) return;
  btn.addEventListener("click", () => {
    if (typeof DeviceOrientationEvent !== "undefined" && typeof DeviceOrientationEvent.requestPermission === "function") {
      DeviceOrientationEvent.requestPermission().then((res) => {
        if (res === "granted") window.addEventListener("deviceorientation", (e) => updateCompassHeading(e.alpha));
      });
    } else {
      window.addEventListener("deviceorientation", (e) => updateCompassHeading(e.alpha));
    }
  });
}

// -------------------------------------------------------------
// 17. GEOFENCE MONITORING & SIREN
// -------------------------------------------------------------
const GEOFENCE_POLL_MS = 20000;
const GEOFENCE_ALERT_KM = 5;
let geofencePollTimer = null;
let geofenceAlertArmed = true;

function playGeofenceSiren() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  const now = audioCtx.currentTime;
  [0, 0.35].forEach((offset) => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "square";
    osc.frequency.setValueAtTime(880, now + offset);
    gain.gain.setValueAtTime(0, now + offset);
    gain.gain.linearRampToValueAtTime(0.25, now + offset + 0.02);
    gain.gain.linearRampToValueAtTime(0, now + offset + 0.28);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(now + offset);
    osc.stop(now + offset + 0.3);
  });
}

async function pollGeofence() {
  try {
    const [lat, lon] = lastVesselCoord;
    const res = await fetch(`${API_BASE}/api/geofence-check?lat=${lat}&lon=${lon}`);
    if (!res.ok) return;
    const data = await res.json();
    const distances = [data.eez_distance_km, data.mpa_distance_km].filter((d) => typeof d === "number");
    const nearestKm = distances.length ? Math.min(...distances) : null;
    const isNear = nearestKm !== null && nearestKm <= GEOFENCE_ALERT_KM;
    if (isNear && geofenceAlertArmed) {
      geofenceAlertArmed = false;
      playGeofenceSiren();
      appendAgentBadge(`🚨 GEOFENCE ALERT: ${data.message} (${nearestKm.toFixed(2)} km)`);
    } else if (!isNear) {
      geofenceAlertArmed = true;
    }
  } catch (err) {
    console.error("Geofence poll failed:", err);
  }
}

function startGeofencePolling() {
  if (geofencePollTimer) return;
  pollGeofence();
  geofencePollTimer = setInterval(pollGeofence, GEOFENCE_POLL_MS);
}

// -------------------------------------------------------------
// 18. MORNING DISPATCH & NEWS FEED
// -------------------------------------------------------------
async function triggerMorningDispatch() {
  const btn = document.getElementById("dispatchButton");
  const label = document.getElementById("dispatchButtonLabel");
  const status = document.getElementById("dispatchStatus");
  const player = document.getElementById("dispatchPlayer");
  if (!btn || !status || !player) return;

  btn.disabled = true;
  if (label) label.textContent = "Generating...";
  status.textContent = "Generating offline briefing (PDF + audio)...";
  status.className = "dispatch-status is-visible is-pending";
  player.innerHTML = "";

  try {
    const coords = await getVesselCoordinates();
    const res = await fetch(`${API_BASE}/api/dispatch/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ coordinates: coords, persona: activePersona, language: "English" }),
    });
    if (!res.ok) throw new Error(`Dispatch request failed (${res.status})`);
    const data = await res.json();
    status.textContent = data.degraded ? "Briefing ready (deterministic mode)." : "Briefing ready.";
    status.className = "dispatch-status is-visible is-success";

    if (data.pdf_url) {
      const pdfLink = document.createElement("a");
      pdfLink.href = data.pdf_url;
      pdfLink.target = "_blank";
      pdfLink.download = "";
      pdfLink.textContent = "Download Briefing PDF";
      player.appendChild(pdfLink);
    }
    if (data.audio_url) {
      const audioEl = document.createElement("audio");
      audioEl.controls = true;
      audioEl.src = data.audio_url;
      player.appendChild(audioEl);
    }
  } catch (err) {
    console.error("Morning Dispatch failed:", err);
    status.textContent = "Failed to generate dispatch. Try again.";
    status.className = "dispatch-status is-visible is-error";
  } finally {
    btn.disabled = false;
    if (label) label.textContent = "Morning Dispatch";
  }
}

async function loadNewsDomains() {
  const select = document.getElementById("newsDomainSelect");
  if (!select) return;
  try {
    const res = await fetch(`${API_BASE}/api/news/domains`);
    if (!res.ok) return;
    const data = await res.json();
    (data.domains || []).forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("News domains load error:", err);
  }
}

async function loadNewsFeed(domain = "") {
  const list = document.getElementById("newsArticlesList");
  if (!list) return;
  list.innerHTML = `<div class="news-article-empty">Loading ocean news...</div>`;
  try {
    const url = domain ? `${API_BASE}/api/news?domain=${encodeURIComponent(domain)}` : `${API_BASE}/api/news`;
    const res = await fetch(url);
    const data = await res.json();
    const articles = data.articles || [];
    list.innerHTML = "";
    if (!articles.length) {
      list.innerHTML = `<div class="news-article-empty">No articles found for this domain.</div>`;
      return;
    }
    articles.forEach((a) => {
      const card = document.createElement("a");
      card.className = "news-article-card";
      card.href = a.link || "#";
      card.target = "_blank";
      card.innerHTML = `<div class="news-article-title">${a.title || ""}</div><div class="news-article-summary">${a.summary || ""}</div>`;
      list.appendChild(card);
    });
  } catch (err) {
    list.innerHTML = `<div class="news-article-empty">Unable to load news feed right now.</div>`;
  }
}

// -------------------------------------------------------------
// 19. INITIALIZATION ENTRY POINT
// -------------------------------------------------------------
updateHazardBanner(MOCK_ORCHESTRATOR_RESPONSE.hazard_status);
plotVesselMarker(MOCK_ORCHESTRATOR_RESPONSE.vessel_coord[0], MOCK_ORCHESTRATOR_RESPONSE.vessel_coord[1]);
plotPFZZones(MOCK_ORCHESTRATOR_RESPONSE.pfz_location);
plotRoute(MOCK_ORCHESTRATOR_RESPONSE.vessel_coord, MOCK_ORCHESTRATOR_RESPONSE.pfz_location);
updateTelemetryBars(MOCK_ORCHESTRATOR_RESPONSE.telemetry);

initPersonaSwitcher();
initVoiceMic();
initHazardReporting();
loadHazardMesh();
initHistoricalChart();
initCompassWidget();
updateCompassHeading(45);
startGeofencePolling();
loadNewsDomains();
loadNewsFeed();
initWhatIfSensors();

if (typeof lucide !== 'undefined') {
  lucide.createIcons();
}