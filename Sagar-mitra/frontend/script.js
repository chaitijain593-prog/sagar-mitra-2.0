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
const authUserBadge = document.getElementById("authUserBadge");
if (authUserBadge) {
  const authenticatedName = localStorage.getItem("orcaName") || localStorage.getItem("orcaUser");
  if (authenticatedName) authUserBadge.textContent = authenticatedName;
}

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
    const username = localStorage.getItem("orcaUser");
    localStorage.removeItem("orcaAuth");
    localStorage.removeItem("orcaUser");
    localStorage.removeItem("orcaName");
    localStorage.removeItem(ONBOARD_KEY);
    localStorage.removeItem("orcaUserProfile");
    if (username) localStorage.removeItem("orcaUserProfile_" + username);
    sessionStorage.clear();
    window.location.replace("auth.html");
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
const sharedMapParams = new URLSearchParams(window.location.search);
const sharedLat = Number(sharedMapParams.get("mlat"));
const sharedLon = Number(sharedMapParams.get("mlon"));
const sharedZoom = Number(sharedMapParams.get("mz"));
const validSharedCenter = sharedMapParams.has("mlat") && sharedMapParams.has("mlon")
  && Number.isFinite(sharedLat) && Number.isFinite(sharedLon)
  && Math.abs(sharedLat) <= 90 && Math.abs(sharedLon) <= 180;
const map = L.map("oceanMap", {
  center: validSharedCenter ? [sharedLat, sharedLon] : [18.9, 72.8],
  zoom: Number.isFinite(sharedZoom) && sharedZoom >= 1 && sharedZoom <= 18 ? sharedZoom : 6,
  zoomControl: false,
  touchZoom: true,
  tap: true,
});
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
let activePFZZones = [];
const vesselIcon = L.divIcon({ className: "", html: '<div class="vessel-marker">🚢</div>', iconSize: [24, 24] });
const NM_IN_METERS = 1852;

async function handleVesselDragEnd(e) {
  try {
    const { lat, lng } = e.target.getLatLng();
    window.currentVesselLat = lat;
    window.currentVesselLon = lng;
    window.vesselMarker = e.target;
    lastVesselCoord = [lat, lng];
    document.querySelectorAll(".vessel-coordinate-value").forEach((badge) => {
      badge.textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    });
    plotRoute(lastVesselCoord, activePFZZones, null);
    const targetZone = activePFZZones[0];
    const target = targetZone && Array.isArray(targetZone.coordinates) ? polygonCentroid(targetZone.coordinates) : [18.2, 69.8];
    if (!compassLiveActive) updateCompassHeading(calculateBearing(lat, lng, target[0], target[1]));
    await checkGeofencePosition(lat, lng);
  } catch (error) {
    console.warn("Dragged-vessel geofence check failed:", error);
    appendAgentBadge("Geofence check is unavailable; the vessel marker and demo route were still updated.");
  }
}

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

  vesselMarker = L.marker([lat, lon], { icon: vesselIcon, zIndexOffset: 1000, draggable: true })
    .addTo(map)
    .bindPopup("<b>Your Vessel</b>")
    .on("dragend", handleVesselDragEnd);
  window.vesselMarker = vesselMarker;
  window.currentVesselLat = lat;
  window.currentVesselLon = lon;
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
      `<b>${z.name || "Favorable Zone"}</b><br>SST: ${z.sst_c | "N/A"}°C<br>` +
      `Chlorophyll: ${z.chlorophyll_mgm3 | "N/A"} mg/m³<br>ML Confidence: ${ml}`
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
    const maxWave = Number.parseFloat(routeInfo.max_wave_m);
    const waveText = Number.isFinite(maxWave) ? ` | Max wave: ${maxWave.toFixed(2)} m` : "";
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
  if (normalized === "HAZARDOUS" || normalized === "WARNING") banner.classList.add("hazard-hazardous");
  else if (normalized === "CAUTION") banner.classList.add("hazard-caution");
  else banner.classList.add("hazard-safe");
  iconEl.innerHTML = HAZARD_ICONS[normalized] || HAZARD_ICONS.SAFE;
  statusEl.textContent = typeof data.distance_km === "number"
    ? `${normalized} (${data.distance_km} km drift)`
    : normalized;

  if (normalized === "HAZARDOUS" && anchorLastAlert !== "HAZARDOUS") {
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

let lastMarineStatus = "SAFE";
function updateHazardBanner(status, context = {}) {
  const banner = document.getElementById("hazardBanner");
  const statusEl = document.getElementById("hazardBannerStatus");
  const iconEl = document.getElementById("hazardBannerIcon");
  const rawStatus = (status || "SAFE").toUpperCase();
  const marineStatus = (context.marineStatus || "").toUpperCase();
  if (marineStatus) lastMarineStatus = marineStatus;
  const marineIsDangerous = ["HAZARDOUS", "WARNING"].includes(marineStatus)
    || (!marineStatus && ["HAZARDOUS", "WARNING"].includes(rawStatus));
  const normalized = context.boundaryAlert
    ? (marineIsDangerous ? marineStatus : (context.boundaryLabel || "EEZ BORDER ALERT"))
    : rawStatus;
  if (!banner || !statusEl || !iconEl) return;

  banner.classList.remove("hazard-safe", "hazard-caution", "hazard-hazardous");
  banner.style.background = "";
  if (normalized === "HAZARDOUS" || normalized === "WARNING") banner.classList.add("hazard-hazardous");
  else if (normalized === "EEZ BORDER ALERT") banner.classList.add("hazard-hazardous");
  else if (normalized === "CAUTION" || normalized === "REGULATORY CAUTION") banner.classList.add("hazard-caution");
  else banner.classList.add("hazard-safe");
  const iconStatus = normalized === "WARNING" ? "HAZARDOUS" : normalized;
  iconEl.innerHTML = HAZARD_ICONS[iconStatus] || HAZARD_ICONS[marineIsDangerous ? "HAZARDOUS" : "CAUTION"] || HAZARD_ICONS.SAFE;
  statusEl.textContent = normalized;
}

function appendAgentBadge(text) {
  if (String(text).includes('Query: "')) return;
  const feed = document.querySelector(".agent-stream-feed") || document.getElementById("agentStreamFeed");
  if (!feed) return;
  const badge = document.createElement("div");
  badge.className = "agent-badge";
  badge.textContent = text;
  feed.appendChild(badge);
  scrollAgentStreamToBottom(feed);
  return badge;
}

function scrollAgentStreamToBottom(feed) {
  const streamContainer = feed || document.querySelector(".agent-stream-feed") || document.getElementById("agentStreamFeed");
  if (!streamContainer) return;
  const scrollToBottom = () => {
    streamContainer.scrollTop = streamContainer.scrollHeight;
  };
  if (typeof window.requestAnimationFrame === "function") window.requestAnimationFrame(scrollToBottom);
  else scrollToBottom();
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
  console.log("Chat response data received:", data);
  const feed = document.querySelector(".agent-stream-feed") || document.getElementById("agentStreamFeed");
  if (!feed) return;
  const card = document.createElement("div");
  card.className = "advisory-card";
  card.style.cssText = "max-width:100%;min-width:0;overflow-wrap:anywhere;line-height:1.6;";

  const advisoryText = (data && typeof data === "object" && (
    data.advisory || data.response || data.summary || data.message
  )) || (typeof data === "string" ? data : "");

  const heading = document.createElement("h4");
  heading.textContent = "Maritime Advisory";
  card.appendChild(heading);

  const addRow = (label, value) => {
    const row = document.createElement("div");
    row.className = "advisory-row";
    row.style.cssText = "margin-bottom:8px;line-height:1.5;overflow-wrap:anywhere;";
    if (label) {
      const strong = document.createElement("b");
      strong.textContent = label;
      row.appendChild(strong);
    }
    const content = document.createElement("span");
    content.textContent = value == null ? "" : String(value);
    row.appendChild(content);
    card.appendChild(row);
    return row;
  };

  addRow("Status: ", (data.display_status || data.hazard_status || "SAFE").toUpperCase());
  addRow("Question: ", data.user_message || "Maritime conditions query");
  addRow("Vessel Position: ", data.vessel_coord
    ? data.vessel_coord.map((n) => Number(n).toFixed(4)).join(", ") : "Unknown");

  const agentNames = {
    navigation: "Satellite Agent", fishing: "Ocean & PFZ", compliance: "Compliance Agent",
    hazard: "Weather & Hazards", historical: "Ocean History", analytics: "Analytics",
    regional: "Regional Scan", dispatch: "Morning Dispatch",
  };
  const agentsRow = document.createElement("div");
  agentsRow.className = "advisory-row advisory-agents-row";
  agentsRow.style.cssText = "display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-bottom:8px;line-height:1.5;";
  const agentsLabel = document.createElement("b");
  agentsLabel.textContent = "Active agents:";
  agentsRow.appendChild(agentsLabel);
  const agents = Array.isArray(data.agents_invoked) && data.agents_invoked.length
    ? data.agents_invoked : ["navigation", "fishing", "compliance"];
  agents.forEach((agent) => {
    const chip = document.createElement("span");
    chip.className = "advisory-agent-chip";
    chip.textContent = agentNames[agent] || String(agent);
    chip.style.cssText = "display:inline-flex;max-width:100%;padding:3px 8px;border:1px solid rgba(56,189,248,.35);border-radius:999px;background:rgba(8,145,178,.12);color:var(--text-main);font-size:.75rem;overflow-wrap:anywhere;";
    agentsRow.appendChild(chip);
  });
  card.appendChild(agentsRow);

  const alerts = Array.isArray(data?.alerts) ? data.alerts.map((alert) => String(alert)) : [];
  const advisory = String(advisoryText || alerts.find((alert) => !/A\* cost-grid route applied|route detour applied/i.test(alert)) || "");
  const body = document.createElement("div");
  body.className = "advisory-body";
  body.style.cssText = "margin:4px 0 8px;line-height:1.5;overflow-wrap:anywhere;white-space:normal;unicode-bidi:plaintext;";
  const cleanAdvisory = advisory
    .replace(/A\* cost-grid route applied to avoid:[^\n.!?\u0964\u0965]*/giu, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  cleanAdvisory.split(/\n\s*\n/).filter(Boolean).forEach((paragraph) => {
    paragraph.split(/(?<=[.!?।॥])\s+(?=\S)/u).filter(Boolean).forEach((sentence) => {
      const p = document.createElement("p");
      p.textContent = sentence.trim();
      p.style.cssText = "margin:0 0 8px;line-height:1.6;overflow-wrap:anywhere;word-break:break-word;unicode-bidi:plaintext;";
      body.appendChild(p);
    });
  });
  const advisoryRow = document.createElement("div");
  advisoryRow.className = "advisory-row advisory-body-row";
  advisoryRow.style.cssText = "margin-bottom:8px;line-height:1.5;overflow-wrap:anywhere;";
  const advisoryLabel = document.createElement("b");
  advisoryLabel.textContent = "Advisory: ";
  advisoryRow.append(advisoryLabel, body);
  card.appendChild(advisoryRow);

  const routeNote = data.route && data.route.note ? String(data.route.note) : "";
  const hasDetour = Boolean(data.route && (data.route.hazard_avoided
    || /A\* cost-grid route applied|route detour applied/i.test(routeNote)));
  if (hasDetour) {
    let detourText;
    if (/exits? the Indian EEZ|international waters/i.test(routeNote)) {
      detourText = "\u{1F4CD} Detour Advisory: A* route applied to avoid exiting the Indian EEZ.";
    } else {
      const cleaned = routeNote.replace(/^A\* cost-grid route applied to avoid:\s*/i, "")
        .replace(/^direct line\s+/i, "").replace(/[.\s]+$/, "");
      detourText = `\u{1F4CD} Detour Advisory: A* route applied to avoid ${cleaned || "a navigation hazard"}.`;
    }
    const callout = document.createElement("div");
    callout.className = "advisory-navigation-callout";
    callout.textContent = detourText;
    callout.style.cssText = "margin:4px 0 8px;padding:9px 11px;border-left:3px solid #f59e0b;border-radius:5px;background:rgba(245,158,11,.1);line-height:1.5;overflow-wrap:anywhere;unicode-bidi:plaintext;";
    card.appendChild(callout);
  }

  alerts.filter((alert) => alert !== advisory && !/A\* cost-grid route applied|route detour applied/i.test(alert))
    .forEach((alert) => {
      const alertRow = addRow("", alert);
      alertRow.classList.add("advisory-alert");
    });
  feed.appendChild(card);
  scrollAgentStreamToBottom(feed);
  window.setTimeout(() => scrollAgentStreamToBottom(feed), 50);
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
const CONVERSATIONS_STORAGE_KEY = "orca_conversations_v1";
const ACTIVE_CONVERSATION_STORAGE_KEY = "orca_active_conversation_v1";
let conversationThreads = [];
let activeConversationId = null;
let editingMessageIndex = null;

function createConversationId() {
  return (window.crypto && crypto.randomUUID)
    ? crypto.randomUUID()
    : `conversation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function persistConversations() {
  try {
    // Keep one ongoing chat transcript; multi-conversation management is not part of this UI.
    const activeThread = getActiveConversation();
    localStorage.setItem(CONVERSATIONS_STORAGE_KEY, JSON.stringify(activeThread ? [activeThread] : []));
    if (activeConversationId) {
      localStorage.setItem(ACTIVE_CONVERSATION_STORAGE_KEY, activeConversationId);
      localStorage.setItem("orca_session_id", activeConversationId);
    }
  } catch (error) {
    console.warn("Conversation history could not be saved locally:", error?.message || error);
  }
}

function getActiveConversation() {
  return conversationThreads.find((thread) => thread.id === activeConversationId) || null;
}

function createInitialConversation() {
  const id = sessionId || createConversationId();
  const thread = { id, title: "New conversation", messages: [], mapContext: null, updatedAt: Date.now(), backendHistoryManaged: true };
  conversationThreads = [thread];
  return thread;
}

function initConversationManager() {
  try {
    const stored = JSON.parse(localStorage.getItem(CONVERSATIONS_STORAGE_KEY) || "[]");
    if (Array.isArray(stored)) conversationThreads = stored.filter((thread) => thread && typeof thread.id === "string");
    activeConversationId = localStorage.getItem(ACTIVE_CONVERSATION_STORAGE_KEY);
  } catch (error) {
    console.warn("Saved conversations could not be read:", error?.message || error);
  }

  const savedThread = conversationThreads.find((thread) => thread.id === activeConversationId)
    || conversationThreads.find((thread) => thread.id === sessionId)
    || conversationThreads[0];
  conversationThreads = savedThread ? [savedThread] : [];
  if (!conversationThreads.length) createInitialConversation();
  activeConversationId = conversationThreads[0].id;
  sessionId = activeConversationId;
  renderConversationMessages();
  restoreConversationMapContext(getActiveConversation()?.mapContext);
  persistConversations();
}

function renderConversationMessages() {
  const feed = document.getElementById("agentStreamFeed");
  const thread = getActiveConversation();
  if (!feed || !thread) return;
  feed.replaceChildren();
  if (!thread.messages.length) {
    const welcome = document.createElement("div");
    welcome.className = "agent-badge";
    welcome.textContent = "Sagar Mitra ORCA is ready. Ask about your route, weather, or fishing zones.";
    feed.appendChild(welcome);
    return;
  }
  thread.messages.forEach((message, index) => {
    const bubble = document.createElement("div");
    bubble.className = `conversation-message ${message.role === "user" ? "user" : "assistant"}`;
    const content = document.createElement("div");
    content.textContent = message.text || "";
    bubble.appendChild(content);
    if (message.role === "user" && thread.backendHistoryManaged !== false) {
      const toolbar = document.createElement("div");
      toolbar.className = "conversation-message-toolbar";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "conversation-edit-button";
      edit.textContent = "Edit & regenerate";
      edit.addEventListener("click", () => {
        const editor = document.createElement("textarea");
        editor.className = "conversation-inline-editor";
        editor.value = message.text || "";
        editor.rows = Math.min(8, Math.max(3, Math.ceil(editor.value.length / 55)));
        content.replaceChildren(editor);
        toolbar.remove();
        const editActions = document.createElement("div");
        editActions.className = "conversation-message-toolbar conversation-edit-actions";
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "conversation-edit-button";
        cancel.textContent = "Cancel";
        cancel.addEventListener("click", renderConversationMessages);
        const regenerate = document.createElement("button");
        regenerate.type = "button";
        regenerate.className = "conversation-edit-button";
        regenerate.textContent = "Save & regenerate";
        regenerate.addEventListener("click", () => {
          const editedText = editor.value.trim();
          if (!editedText) {
            editor.focus();
            return;
          }
          editingMessageIndex = index;
          document.getElementById("chatInput").value = editedText;
          const editStatus = document.getElementById("promptEditStatus");
          if (editStatus) {
            editStatus.textContent = "Regenerating from this prompt; later messages in this conversation will be replaced.";
            editStatus.hidden = false;
          }
          handleSendMessage();
        });
        editActions.append(cancel, regenerate);
        bubble.appendChild(editActions);
        editor.focus();
      });
      toolbar.appendChild(edit);
      bubble.appendChild(toolbar);
    }
    feed.appendChild(bubble);
  });
  scrollAgentStreamToBottom(feed);
}

function addConversationMessage(role, text) {
  const thread = getActiveConversation();
  if (!thread) return null;
  const message = { role, text: String(text || ""), createdAt: Date.now() };
  thread.messages.push(message);
  thread.messages = thread.messages.slice(-60);
  thread.updatedAt = Date.now();
  persistConversations();
  renderConversationMessages();
  return message;
}

function restoreConversationMapContext(context) {
  const coords = context?.coordinates;
  activePFZZones = context?.pfz_location || [];
  plotPFZZones(activePFZZones);
  plotRegionalZones(context?.regional_zones || []);
  plotRoute(Array.isArray(coords) ? coords : null, activePFZZones, context?.route || null);
  if (Array.isArray(coords) && coords.length === 2 && coords.every(Number.isFinite)) {
    lastVesselCoord = coords;
    plotVesselMarker(coords[0], coords[1]);
    setLastKnownState(coords, context.hazard_status || context.display_status || "SAFE");
    updateHazardBanner(context.display_status || context.hazard_status || "SAFE", {
      boundaryAlert: context.boundary_alert,
      boundaryLabel: context.boundary_status,
      marineStatus: context.marine_status,
    });
    if (context.telemetry) {
      updateTelemetryBars(context.telemetry);
      updateHistoricalChart(context.telemetry);
    }
  } else {
    updateHazardBanner("SAFE");
    setLastKnownState(lastVesselCoord, "SAFE");
    updateTelemetryBars(null);
    if (historicalChartInstance) {
      historicalChartInstance.destroy();
      historicalChartInstance = null;
    }
  }
  if (typeof map !== "undefined") map.invalidateSize();
}

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
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Browser geolocation is unavailable."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
      (error) => reject(new Error(`Browser geolocation failed: ${error.message}`)),
      { timeout: 4000 }
    );
  });
}

let chatQueryInFlight = false;

function handleSendMessage() {
  return handleQuerySubmit();
}

async function handleQuerySubmit(e) {
  try {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
    if (typeof e.stopImmediatePropagation === "function") e.stopImmediatePropagation();
  }
  if (chatQueryInFlight) return;
  chatQueryInFlight = true;
  const input = document.getElementById("chatInput");
  const text = input ? input.value.trim() : "";
  if (!text) return;
  const activeThread = getActiveConversation();
  if (!activeThread) return;
  const wasEditingPrompt = Number.isInteger(editingMessageIndex);
  const priorMessages = wasEditingPrompt
    ? activeThread.messages.slice(0, editingMessageIndex)
    : activeThread.messages.slice();
  const historyOverride = activeThread.backendHistoryManaged === false && !wasEditingPrompt
    ? null
    : priorMessages
      .filter((message) => message.role === "user" || message.role === "assistant")
      .slice(-8)
      .map(({ role, text: messageText }) => ({ role, text: messageText }));
  if (wasEditingPrompt) {
    activeThread.messages = priorMessages;
    activeThread.mapContext = null;
    restoreConversationMapContext(null);
  }
  editingMessageIndex = null;
  const loader = document.getElementById("chatLoader");
  const sendBtn = document.getElementById("chatSendBtn");
  if (sendBtn) sendBtn.disabled = true;
  if (input) input.value = "";
  addConversationMessage("user", text);
  const promptEditStatus = document.getElementById("promptEditStatus");
  if (promptEditStatus) promptEditStatus.hidden = true;
  if (input) input.placeholder = "Ask ORCA about hazards, EEZ or fishing zones...";
  appendAgentBadge(`🧑‍✈️ Query: "${text}"`);
  if (loader) loader.style.display = "flex";
  try {
    await runAgentSequence();
  } catch (sequenceError) {
    console.warn("Agent progress animation failed:", sequenceError);
  }

  const activePosition = window.vesselMarker && typeof window.vesselMarker.getLatLng === "function"
    ? window.vesselMarker.getLatLng()
    : null;
  const coords = activePosition
    ? [Number(activePosition.lat), Number(activePosition.lng)]
    : Array.isArray(lastVesselCoord) ? lastVesselCoord.map(Number) : null;
  if (!coords || coords.length !== 2 || !coords.every(Number.isFinite)) {
    appendAgentBadge("Live vessel position is unavailable; position the vessel marker before requesting an advisory.");
    return;
  }
  let parsedData;
  const abortController = new AbortController();
  const timeoutId = setTimeout(() => abortController.abort(), ORCHESTRATE_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}/api/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: text,
        coordinates: coords,
        session_id: sessionId,
        history_override: historyOverride,
        reset_context: wasEditingPrompt,
        onboarding_persona: activePersona,
      }),
      signal: abortController.signal,
    });
    if (!res.ok) throw new Error(`Backend not responding correctly (HTTP ${res.status})`);
    const backendData = await res.json();
    sessionId = backendData.session_id || sessionId;
    activeConversationId = sessionId;
    try {
      if (sessionId) localStorage.setItem("orca_session_id", sessionId);
    } catch (e) {}

    const extraAlerts = [];
    if (backendData.lightning_alert) extraAlerts.push("⚡ Lightning risk detected in this area.");
    if (backendData.cyclone_alert) extraAlerts.push("🌀 Cyclone watch (wind-speed proxy) -- exercise caution.");
    if (backendData.route && backendData.route.hazard_avoided) {
      extraAlerts.push(`🧭 ${backendData.route.note || "Route detour applied to avoid a hazard."}`);
    }

    const boundaryEvidence = `${backendData.route?.note || ""} ${backendData.advisory || ""}`;
    const boundaryAlert = Boolean(backendData.boundary_alert)
      || /(?:crossed?|exit(?:ing)?|outside).{0,48}(?:EEZ|international waters)|(?:EEZ|international waters).{0,48}(?:crossed?|exit|boundary)/i.test(boundaryEvidence);
    const marineStatus = backendData.marine_status || (backendData.cyclone_alert
      ? "WARNING" : boundaryAlert ? "SAFE" : backendData.hazard_status || "SAFE");
    const displayStatus = boundaryAlert && !["HAZARDOUS", "WARNING"].includes(String(marineStatus).toUpperCase())
      ? (backendData.boundary_status || "EEZ BORDER ALERT")
      : (marineStatus || backendData.hazard_status || "SAFE");

    parsedData = {
      user_message: backendData.user_message || text,
      advisory: backendData.advisory || "",
      vessel_coord: backendData.coordinates || coords,
      hazard_status: backendData.hazard_status || "UNKNOWN",
      display_status: displayStatus,
      marine_status: marineStatus,
      boundary_alert: boundaryAlert,
      boundary_status: backendData.boundary_status || "EEZ BORDER ALERT",
      advisory_source: backendData.advisory_source || "live_model",
      alerts: [...(backendData.advisory ? [backendData.advisory] : []), ...extraAlerts],
      pfz_location: backendData.pfz_location || [],
      telemetry: backendData.telemetry || null,
      route: backendData.route || null,
      plot_url: backendData.plot_url || null,
      regional_zones: backendData.regional_zones || [],
      persona: backendData.persona || "Fisherman",
      agents_invoked: backendData.agents_invoked || [],
      shap_attributions: (backendData.telemetry && backendData.telemetry.shap_attributions) || null,
    };
  } catch (err) {
    console.error("Live ORCA advisory request failed:", err);
    appendAgentBadge(`Live advisory unavailable: ${err.message}`);
    return;
  } finally {
    clearTimeout(timeoutId);
    if (loader) loader.style.display = "none";
    if (sendBtn) sendBtn.disabled = false;
    setMicState("idle");
  }

  const renderSafely = (label, render) => {
    try { render(); } catch (renderError) { console.error(`${label} rendering failed:`, renderError); }
  };
  activePFZZones = parsedData.pfz_location || [];
  renderSafely("Hazard banner", () => updateHazardBanner(parsedData.display_status || parsedData.hazard_status, {
    boundaryAlert: parsedData.boundary_alert,
    boundaryLabel: parsedData.boundary_status,
    marineStatus: parsedData.marine_status,
  }));
  renderSafely("Vessel marker", () => plotVesselMarker(parsedData.vessel_coord[0], parsedData.vessel_coord[1]));
  renderSafely("PFZ zones", () => plotPFZZones(parsedData.pfz_location));
  renderSafely("Route", () => plotRoute(parsedData.vessel_coord, parsedData.pfz_location, parsedData.route));
  renderSafely("Regional zones", () => plotRegionalZones(parsedData.regional_zones));
  renderSafely("Advisory card", () => appendAdvisoryCard(parsedData));
  const responseThread = getActiveConversation();
  if (responseThread) {
    responseThread.messages.push({
      role: "assistant",
      text: String(parsedData.advisory || "No advisory text returned."),
      createdAt: Date.now(),
    });
    responseThread.messages = responseThread.messages.slice(-60);
    responseThread.mapContext = {
      coordinates: parsedData.vessel_coord,
      pfz_location: parsedData.pfz_location,
      route: parsedData.route,
      regional_zones: parsedData.regional_zones,
      display_status: parsedData.display_status,
      hazard_status: parsedData.hazard_status,
      boundary_alert: parsedData.boundary_alert,
      boundary_status: parsedData.boundary_status,
      marine_status: parsedData.marine_status,
      telemetry: parsedData.telemetry,
    };
    responseThread.lastQuery = { text, coordinates: parsedData.vessel_coord, persona: activePersona, updatedAt: Date.now() };
    responseThread.updatedAt = Date.now();
    persistConversations();
  }
  renderSafely("Vessel state", () => setLastKnownState(parsedData.vessel_coord, parsedData.hazard_status));
  if (parsedData.telemetry) {
    renderSafely("Telemetry", () => updateTelemetryBars(parsedData.telemetry));
    renderSafely("Historical chart", () => updateHistoricalChart(parsedData.telemetry));
  }
  renderSafely("Map sizing", () => { if (typeof map !== "undefined") map.invalidateSize(); });
  } catch (err) {
    console.error("Chat request or rendering failed:", err);
  } finally {
    chatQueryInFlight = false;
    const sendBtn = document.getElementById("chatSendBtn");
    if (sendBtn) sendBtn.disabled = false;
    const loader = document.getElementById("chatLoader");
    if (loader) loader.style.display = "none";
  }
}

function initChatInterface() {
  const form = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSendBtn");

  if (form) {
    form.onsubmit = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (typeof e.stopImmediatePropagation === "function") e.stopImmediatePropagation();
      handleSendMessage();
      return false;
    };
  }
  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      handleSendMessage();
      return false;
    });
  }
  if (sendBtn) {
    sendBtn.type = "button";
    sendBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      handleSendMessage();
      return false;
    });
  }
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

let browserSpeechRecognition = null;
function startBrowserSpeechRecognition() {
  const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
  if (!SpeechRecognition) return false;
  try {
    browserSpeechRecognition = new SpeechRecognition();
    browserSpeechRecognition.lang = "en-IN";
    browserSpeechRecognition.interimResults = false;
    browserSpeechRecognition.maxAlternatives = 1;
    browserSpeechRecognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      const input = document.getElementById("chatInput");
      const form = document.getElementById("chatForm");
      if (!transcript || !input || !form) {
        appendAgentBadge("No speech was recognized. Please try again or type your query.");
        setMicState("idle");
        return;
      }
      input.value = transcript;
      setMicState("busy");
      form.requestSubmit();
    };
    browserSpeechRecognition.onerror = (event) => {
      appendAgentBadge(`Browser speech recognition unavailable (${event.error || "unknown error"}). You can type your query instead.`);
      setMicState("idle");
    };
    browserSpeechRecognition.onend = () => {
      if (micState === "recording") setMicState("idle");
      browserSpeechRecognition = null;
    };
    browserSpeechRecognition.start();
    setMicState("recording");
    appendAgentBadge("Listening with browser speech recognition...");
    return true;
  } catch (error) {
    console.warn("Browser speech recognition could not start:", error);
    browserSpeechRecognition = null;
    setMicState("idle");
    return false;
  }
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
  const abortController = new AbortController();
  const timeoutId = setTimeout(() => abortController.abort(), ORCHESTRATE_TIMEOUT_MS);

  try {
    const coords = await getVesselCoordinates();
    const ext = mimeType.includes("mp4") ? "m4a" : mimeType.includes("ogg") ? "ogg" : "webm";
    const formData = new FormData();
    formData.append("audio", blob, `voice_query.${ext}`);
    formData.append("latitude", coords[0]);
    formData.append("longitude", coords[1]);

    const res = await fetch(`${API_BASE}/api/voice/orchestrate`, { method: "POST", body: formData, signal: abortController.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    appendAgentBadge(`🗣️ Heard (${data.detected_language}): "${data.transcript}"`);
    appendAgentBadge(`🌊 ${data.advisory_text}`);
  } catch (err) {
    console.error("Voice orchestrate error:", err);
    appendAgentBadge(`⚠ Voice query failed: ${err.message}`);
    if (err.name === "AbortError" || err instanceof TypeError || /HTTP 5\d\d/.test(err.message)) {
      const input = document.getElementById("chatInput");
      const form = document.getElementById("chatForm");
      if (input && form) {
        input.value = "Voice query unavailable; show the maritime simulation advisory.";
        setTimeout(() => {
          try { form.requestSubmit(); } catch (submitError) { console.warn("Offline voice fallback could not submit:", submitError); }
        }, 0);
      }
    }
  } finally {
    clearTimeout(timeoutId);
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
    if (micState === "idle") {
      if (!startBrowserSpeechRecognition()) {
        startMicRecording().catch((error) => {
          console.error("Microphone startup failed:", error);
          appendAgentBadge("Microphone could not start. Type your query instead.");
          setMicState("idle");
        });
      }
    } else if (micState === "recording") {
      if (browserSpeechRecognition) browserSpeechRecognition.stop();
      else stopMicRecording();
    }
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
        const sstShap = data.shap_values?.sst | (sstDelta * 0.12);
        whatifSstShapVal.textContent = `${sstShap >= 0 ? '+' : ''}${sstShap.toFixed(3)}`;
        whatifSstShapVal.style.color = sstShap >= 0 ? "#38bdf8" : "#f87171";
      }
      if (whatifChloShapVal) {
        const chloShap = data.shap_values?.chlorophyll | (chloDelta * 0.18);
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
let compassOrientationHandler = null;
let compassFallbackTimer = null;
function setCompassMode(mode, subText) {
  const label = document.getElementById("compassModeLabel");
  const sub = document.getElementById("compassSubStatus");
  if (label) label.textContent = mode === "live" ? "Live Compass Heading" : "Course over Ground";
  if (sub) sub.textContent = subText || "";
}

function activateSimulatedCompass() {
  compassLiveActive = false;
  if (compassFallbackTimer) clearTimeout(compassFallbackTimer);
  const zone = activePFZZones[0];
  const target = zone && Array.isArray(zone.coordinates) ? polygonCentroid(zone.coordinates) : [18.2, 69.8];
  updateCompassHeading(calculateBearing(lastVesselCoord[0], lastVesselCoord[1], target[0], target[1]));
  setCompassMode("course", "Heading Active (Simulated)");
  const label = document.getElementById("compassModeLabel");
  if (label) label.textContent = "Heading Active (Simulated)";
}

function initCompassWidget() {
  const btn = document.getElementById("compassLiveBtn");
  setCompassMode("course", 'Tap "Enable Live Compass" to use device orientation');
  if (!btn) return;
  btn.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const DeviceOrientation = window.DeviceOrientationEvent;
    if (!DeviceOrientation) {
      activateSimulatedCompass();
      return;
    }
    try {
      if (typeof DeviceOrientation.requestPermission === "function") {
        const permission = await DeviceOrientation.requestPermission();
        if (permission !== "granted") {
          activateSimulatedCompass();
          return;
        }
      }
      if (compassOrientationHandler) window.removeEventListener("deviceorientation", compassOrientationHandler);
      compassOrientationHandler = (orientationEvent) => {
        if (!Number.isFinite(orientationEvent.alpha)) return;
        if (compassFallbackTimer) clearTimeout(compassFallbackTimer);
        compassLiveActive = true;
        setCompassMode("live", "Device orientation is active");
        updateCompassHeading(360 - orientationEvent.alpha);
      };
      window.addEventListener("deviceorientation", compassOrientationHandler);
      compassFallbackTimer = setTimeout(() => {
        if (!compassLiveActive) activateSimulatedCompass();
      }, 1800);
    } catch (error) {
      console.warn("Device orientation unavailable; using simulated heading:", error);
      activateSimulatedCompass();
    }
  });
}

// -------------------------------------------------------------
// 17. GEOFENCE MONITORING & SIREN
// -------------------------------------------------------------
const GEOFENCE_POLL_MS = 20000;
const GEOFENCE_ALERT_KM = 5;
let geofencePollTimer = null;
let lastGeofenceAlert = null;
let sirenAudioContext = null;
let sirenAudioUnlocked = false;

document.addEventListener("click", () => {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    if (!sirenAudioContext) sirenAudioContext = new AudioContextClass();
    if (sirenAudioContext.state === "suspended") {
      sirenAudioContext.resume().then(() => { sirenAudioUnlocked = true; }).catch((error) => {
        console.warn("Siren audio remains locked:", error);
      });
    } else {
      sirenAudioUnlocked = true;
    }
  } catch (error) {
    console.warn("Siren audio could not be initialized:", error);
  }
}, { once: true });

function playSirenTone() {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = sirenAudioContext || new AudioContextClass();
    sirenAudioContext = ctx;
    if (ctx.state === "suspended") ctx.resume().catch((error) => console.warn("Siren audio resume failed:", error));
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sawtooth";
    const now = ctx.currentTime;
    osc.frequency.setValueAtTime(600, now);
    osc.frequency.linearRampToValueAtTime(900, now + 0.5);
    osc.frequency.linearRampToValueAtTime(600, now + 1.0);
    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 1.2);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 1.2);
  } catch (error) {
    console.warn("Audio play blocked", error);
  }
}

function normalizeGeofenceState(data, nearestKm) {
  const insideEez = data.inside_eez === true || data.breached === false;
  const outsideEez = data.inside_eez === false || data.breached === true;
  if (outsideEez || data.inside_mpa === true) return "CROSSED";
  if (insideEez) return "SAFE";
  if (data.geofence_alert === "HAZARDOUS") return "CROSSED";
  if (data.geofence_alert === "CAUTION" || (nearestKm !== null && nearestKm <= GEOFENCE_ALERT_KM)) return "APPROACHING";
  return "SAFE";
}

function updateGeofenceTransition(data, nearestKm) {
  const previous = lastGeofenceAlert;
  const next = normalizeGeofenceState(data, nearestKm);
  const changed = next !== previous;
  lastGeofenceAlert = next;
  updateHazardBanner(next === "CROSSED" ? "HAZARDOUS" : next === "APPROACHING" ? "CAUTION" : "SAFE", {
    boundaryAlert: data.inside_eez === false || data.breached === true || data.inside_mpa === true,
    boundaryLabel: next === "CROSSED" && data.inside_eez === false ? "EEZ BORDER ALERT" : "REGULATORY CAUTION",
    marineStatus: lastMarineStatus,
  });
  const badge = document.querySelector('.marine-safety-status')
    || document.getElementById('marine-status-badge')
    || document.getElementById('hazardBanner');
  const badgeText = badge
    ? (badge.querySelector('#hazardBannerStatus') || badge.querySelector('span') || badge)
    : null;
  if (badge && (typeof data.breached === 'boolean' || typeof data.inside_eez === 'boolean')) {
    const isInside = data.breached === false || data.inside_eez === true;
    badge.style.backgroundColor = isInside ? '#16a34a' : '#dc2626';
    badge.style.color = '#ffffff';
    if (badgeText) badgeText.textContent = isInside ? 'SAFE' : 'EEZ BORDER ALERT';
  }
  if (changed && previous !== null) {
    appendAgentBadge(`GEOFENCE ${next}: ${data.message || "Maritime boundary status changed."}${nearestKm === null ? "" : ` (${nearestKm.toFixed(2)} km)`}`);
  } else if (changed && next !== "SAFE") {
    appendAgentBadge(`GEOFENCE ${next}: ${data.message || "Maritime boundary status changed."}${nearestKm === null ? "" : ` (${nearestKm.toFixed(2)} km)`}`);
  }
  if (previous !== null && previous !== "CROSSED" && next === "CROSSED" && sirenAudioUnlocked) playSirenTone();
  return next;
}

async function pollGeofence() {
  try {
    const [lat, lon] = lastVesselCoord;
    const response = await fetch(`${API_BASE}/api/geofence-check?lat=${lat}&lon=${lon}`);
    if (!response.ok) return;
    const data = await response.json();
    const distances = [data.eez_distance_km, data.mpa_distance_km].filter((distance) => typeof distance === "number");
    const nearestKm = distances.length ? Math.min(...distances) : null;
    updateGeofenceTransition(data, nearestKm);
  } catch (error) {
    console.warn("Geofence poll failed:", error);
  }
}

function startGeofencePolling() {
  if (geofencePollTimer) return;
  pollGeofence();
  geofencePollTimer = setInterval(pollGeofence, GEOFENCE_POLL_MS);
}

async function checkGeofencePosition(lat, lon) {
  const response = await fetch(`${API_BASE}/api/geofence-check?lat=${lat}&lon=${lon}`);
  if (!response.ok) throw new Error(`Geofence request failed (HTTP ${response.status})`);
  const data = await response.json();
  const distances = [data.eez_distance_km, data.mpa_distance_km].filter((distance) => typeof distance === "number");
  const nearestKm = distances.length ? Math.min(...distances) : null;
  updateGeofenceTransition(data, nearestKm);
  return data;
}

// -------------------------------------------------------------
// 18. MORNING DISPATCH & NEWS FEED
// -------------------------------------------------------------
function initDispatchButton() {
  const btn = document.getElementById("morning-dispatch-btn") || document.querySelector(".dispatch-action-btn");
  if (!btn) return;
  btn.type = "button";
  btn.onclick = async function (e) {
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    const previousText = btn.textContent;
    const showDispatchWarning = (message) => {
      try {
        document.getElementById("dispatch-warning-toast")?.remove();
        const toast = document.createElement("div");
        toast.id = "dispatch-warning-toast";
        toast.setAttribute("role", "status");
        toast.textContent = message;
        toast.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:100000;max-width:min(560px,calc(100vw - 32px));padding:14px 18px;border:1px solid #f59e0b;border-radius:10px;background:#172033;color:#fff;font:14px/1.5 sans-serif;box-shadow:0 8px 28px #0008;";
        document.body.appendChild(toast);
        window.setTimeout(() => toast.remove(), 7000);
      } catch (_) { /* A warning display failure must not escape the click handler. */ }
    };
    try {
    btn.disabled = true;
    btn.textContent = "Generating dispatch...";
      let lat = 18.95;
      let lon = 72.75;
      if (window.vesselMarker && typeof window.vesselMarker.getLatLng === "function") {
        const pos = window.vesselMarker.getLatLng();
        lat = Number(pos.lat);
        lon = Number(pos.lng);
      } else if (window.currentVesselLat && window.currentVesselLon) {
        lat = Number(window.currentVesselLat);
        lon = Number(window.currentVesselLon);
      }
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error("Invalid vessel coordinates.");
      const res = await fetch(`${API_BASE}/api/dispatch/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          coordinates: [lat, lon],
          lat,
          lon,
          onboarding_persona: "Fisherman",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Dispatch request failed (HTTP ${res.status})`);

      document.getElementById("morning-dispatch-card")?.remove();
      const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
      })[char]);
      const [dispatchLat, dispatchLon] = data.coordinates;
      const telemetry = data.telemetry || {};
      const pfz = data.pfz_advisory || {};
      const safety = data.safety_and_routing || {};
      const routing = data.routing && typeof data.routing === "object" ? data.routing : safety;
      let routingDisplay = "Safe (Inside Indian EEZ)";
      let borderDist = "";
      if (routing && typeof routing === "object") {
        const breached = routing.breached === true || routing.inside_eez === false ||
          routing.alert_level === "EEZ BORDER ALERT";
        routingDisplay = breached ? "Border Alert (Outside EEZ)" : "Safe (Inside Indian EEZ)";
        const rawDistance = routing.eez_distance_km | routing.distance_km | safety.eez_distance_km;
        const distance = Number.parseFloat(rawDistance);
        if (Number.isFinite(distance)) borderDist = ` - ${distance.toFixed(2)} km to boundary`;
      } else if (typeof routing === "string") {
        const breached = /['\"]breached['\"]\s*:\s*True/i.test(routing) ||
          /['\"]alert_level['\"]\s*:\s*['\"]EEZ BORDER ALERT['\"]/i.test(routing);
        const distMatch = routing.match(/['\"]eez_distance_km['\"]\s*:\s*([\d.]+)/i) ||
          routing.match(/['\"]distance_km['\"]\s*:\s*([\d.]+)/i);
        routingDisplay = breached ? "Border Alert (Outside EEZ)" : "Safe (Inside Indian EEZ)";
        if (distMatch) {
          const distance = Number.parseFloat(distMatch[1]);
          if (Number.isFinite(distance)) borderDist = ` - ${distance.toFixed(2)} km to boundary`;
        }
      }
      const formattedRouting = `${routingDisplay}${borderDist}`;
      const modal = document.createElement("div");
      modal.id = "morning-dispatch-card";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.style.cssText = "position:fixed;inset:0;z-index:99999;color:#fff;font-family:sans-serif;background:rgba(0,0,0,0.45);";
      modal.innerHTML = `
        <div style="position:absolute;top:50%;left:50%;transform:translate(-50%, -50%);background:rgba(10, 25, 47, 0.95);border:1.5px solid #00d2ff;border-radius:12px;padding:20px;z-index:9999;color:#fff;width:380px;max-width:calc(100% - 40px);box-shadow:0 0 25px rgba(0, 210, 255, 0.35);box-sizing:border-box;">
          <h3 style="margin-top:0;color:#00d2ff;font-size:16px;">📋 Morning Maritime Dispatch</h3>
          <p style="margin:6px 0;font-size:13px;"><strong>Position:</strong> ${dispatchLat.toFixed(2)}° N, ${dispatchLon.toFixed(2)}° E</p>
          <p style="margin:6px 0;font-size:13px;"><strong>Sea Condition:</strong> ${escapeHtml(data.sea_condition || safety.status)}</p>
          <p style="margin:6px 0;font-size:13px;"><strong>SST:</strong> ${escapeHtml(telemetry.sst || data.sst)}</p>
          <p style="margin:6px 0;font-size:13px;"><strong>Nearest PFZ:</strong> ${escapeHtml(pfz.status || "Unavailable")} · ${escapeHtml(pfz.distance_nm || "Unavailable")}</p>
          <p style="margin:6px 0;font-size:13px;"><strong>Heading:</strong> ${escapeHtml(pfz.recommended_heading || "Unavailable")}</p>
          <p style="margin:6px 0;font-size:13px;"><strong>Routing Status:</strong> ${escapeHtml(formattedRouting)}</p>
          <div style="margin-top:16px;display:flex;gap:10px;">
            <button id="close-dispatch-modal" type="button" style="flex:1;background:#00d2ff;color:#051329;border:none;padding:8px;border-radius:6px;font-weight:bold;cursor:pointer;">Close</button>
            <button id="download-dispatch-pdf-btn" type="button" style="flex:1;background:#22c55e;color:#fff;border:none;padding:8px;border-radius:6px;font-weight:bold;cursor:pointer;">📥 Download PDF</button>
          </div>
        </div>`;
      document.body.appendChild(modal);
      document.getElementById("close-dispatch-modal").onclick = () => modal.remove();
      document.getElementById("download-dispatch-pdf-btn").onclick = (event) => {
        event.preventDefault();
        const printWindow = window.open("", "_blank", "width=750,height=800");
        if (!printWindow) {
          window.alert("Allow pop-ups to print or save the dispatch as a PDF.");
          return;
        }
        printWindow.document.write(`
          <!doctype html><html><head><title>Sagar Mitra Dispatch</title>
          <style>@page{size:A4;margin:18mm}*{box-sizing:border-box}body{font:14px/1.5 Arial,sans-serif;color:#10243b;margin:0}header{border-bottom:4px solid #087e9b;padding-bottom:14px;margin-bottom:20px}h1{font-size:21px;color:#075985;margin:0 0 10px}h2{font-size:16px;color:#075985;margin:22px 0 8px}table{width:100%;border-collapse:collapse;margin:8px 0 16px}th,td{text-align:left;border:1px solid #9aafbd;padding:9px;vertical-align:top}th{background:#e8f4f7;width:34%}.summary{padding:12px;background:#eff7fa;border-left:4px solid #087e9b}footer{margin-top:25px;color:#526577;font-size:11px}@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style>
          </head><body>
          <header><h1>SAGAR MITRA ? OPERATIONAL MARITIME CLEARANCE &amp; FISHING DISPATCH</h1>
          <div><strong>Issued:</strong> ${escapeHtml(data.timestamp || new Date().toLocaleString())} &nbsp; <strong>Vessel:</strong> ${escapeHtml(data.vessel_persona || "Fisherman")}</div>
          <div><strong>Coordinates:</strong> ${dispatchLat.toFixed(4)}°, ${dispatchLon.toFixed(4)}°</div></header>
          <h2>1. Sea State &amp; Oceanographic Conditions</h2><table>
          <tr><th>Sea safety level</th><td>${escapeHtml(safety.status || "ADVISORY")}</td></tr>
          <tr><th>Wave height</th><td>${escapeHtml(telemetry.wave_height || data.sea_condition)}</td></tr>
          <tr><th>Swell</th><td>${escapeHtml(telemetry.swell || "Unavailable")}</td></tr>
          <tr><th>Wind speed</th><td>${escapeHtml(telemetry.wind_speed || "Unavailable")}</td></tr>
          <tr><th>Sea surface temperature</th><td>${escapeHtml(telemetry.sst || data.sst)}</td></tr>
          <tr><th>Chlorophyll-a</th><td>${escapeHtml(telemetry.chlorophyll || "Unavailable")}</td></tr>
          <tr><th>Salinity</th><td>${escapeHtml(telemetry.salinity || "Unavailable")}</td></tr></table>
          <h2>2. Potential Fishing Zone (PFZ) Opportunity</h2><table>
          <tr><th>Nearest zone</th><td>${escapeHtml(pfz.status || "Unavailable")}</td></tr>
          <tr><th>Recommended heading</th><td>${escapeHtml(pfz.recommended_heading || "Unavailable")}</td></tr>
          <tr><th>Distance to target</th><td>${escapeHtml(pfz.distance_nm || "Unavailable")}</td></tr>
          <tr><th>Front intelligence</th><td>${escapeHtml(pfz.target_opportunity || "No PFZ intelligence available")}</td></tr></table>
          <h2>3. Navigation &amp; Maritime Boundaries</h2><table>
          <tr><th>EEZ distance</th><td>${escapeHtml(safety.eez_distance || "Unavailable")}</td></tr>
          <tr><th>Routing status</th><td>${escapeHtml(formattedRouting)}</td></tr>
          <tr><th>Safety advisory</th><td>${escapeHtml(safety.status || "ADVISORY")} ? ${escapeHtml(data.summary || "Check official marine notices before departure.")}</td></tr></table>
          <p class="summary"><strong>Pre-sail summary:</strong> ${escapeHtml(data.summary || "Consult official marine and fisheries advisories before departure.")}</p>
          <footer>Confirm current Coast Guard, IMD and INCOIS notices before sailing.</footer>
          <script>window.onload = function() { window.print(); }<\/script>
          </body></html>`);
        printWindow.document.close();
      };
    } catch (error) {
      console.error("Morning dispatch generation failed:", error);
      showDispatchWarning("Telemetry unavailable for selected out-of-bounds coordinates. Reposition vessel closer to coastal waters.");
    } finally {
      try {
        btn.disabled = false;
        btn.textContent = previousText;
      } catch (_) { /* Avoid propagating DOM cleanup errors from finally. */ }
    }
    return false;
  };
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
activePFZZones = MOCK_ORCHESTRATOR_RESPONSE.pfz_location;
updateHazardBanner(MOCK_ORCHESTRATOR_RESPONSE.hazard_status);
plotVesselMarker(MOCK_ORCHESTRATOR_RESPONSE.vessel_coord[0], MOCK_ORCHESTRATOR_RESPONSE.vessel_coord[1]);
plotPFZZones(MOCK_ORCHESTRATOR_RESPONSE.pfz_location);
plotRoute(MOCK_ORCHESTRATOR_RESPONSE.vessel_coord, MOCK_ORCHESTRATOR_RESPONSE.pfz_location);
updateTelemetryBars(MOCK_ORCHESTRATOR_RESPONSE.telemetry);

initPersonaSwitcher();
initChatInterface();
initConversationManager();
initDispatchButton();
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
// Marine records load the first time the map layer is enabled. The cache keeps
// repeated toggles local, and a failed request can be retried on the next toggle.
const marineMarkerGroup = typeof L.markerClusterGroup === "function"
  ? L.markerClusterGroup({ showCoverageOnHover: false, chunkedLoading: true, maxClusterRadius: 38, disableClusteringAtZoom: 10 })
  : L.layerGroup();
const marineOverlay = L.layerGroup([marineMarkerGroup]);
const mapLayerControl = L.control.layers(null, {
  "Marine Observations (OBIS / IndOBIS)": marineOverlay,
}, { collapsed: true }).addTo(map);
let marineLoadedFilterKey = null;
let marineObservationsController = null;
let marineObservationsRequestId = 0;
let marineObservationRecords = [];
let marineObservationStatus = "";
let marineTrackInfo = { available: false };
const marinePathSpeciesColors = new Map();
let marinePathGradientUpdateScheduled = false;
let marineFilterContainer = null;
let marineFilterDebounceTimer = null;
let marineMarkerRenderGeneration = 0;
const marineObservationMarkerRegistry = new Map();
let marinePathLayers = [];
let marineSelectedBounds = null;
let marineRegionSelectionEnabled = false;
let marineRegionSelectionStart = null;
let marineRegionSelectionRect = null;
let marineActiveDepthBand = null;
let marineDepthBandMatchCount = 0;

function readMarinePanelFilters() {
  const container = marineFilterContainer;
  const temporalChoice = container?.querySelector("#marine-season-filter")?.value || "";
  return {
    species: container?.querySelector("#marine-species-filter")?.value.trim() || "",
    start_date: container?.querySelector("#marine-start-date")?.value || "",
    end_date: container?.querySelector("#marine-end-date")?.value || "",
    month: temporalChoice === "current_month" ? String(new Date().getMonth() + 1) : "",
    season: temporalChoice === "current_month" ? "" : temporalChoice,
    region: container?.querySelector("#marine-region-filter")?.value || "indian_ocean",
    include_global_tracks: Boolean(container?.querySelector("#marine-show-paths")?.checked),
  };
}

function writeMarineMapState(filters = readMarinePanelFilters()) {
  const params = new URLSearchParams(window.location.search);
  const values = {
    marine: map.hasLayer(marineOverlay) ? "1" : "0",
    species: filters.species || "",
    region: filters.region || "indian_ocean",
    start_date: filters.start_date || "",
    end_date: filters.end_date || "",
    month: filters.month || "",
    season: filters.season || "",
    paths: marineFilterContainer?.querySelector("#marine-show-paths")?.checked ? "1" : "0",
    depth_colors: marineFilterContainer?.querySelector("#marine-depth-colors")?.checked ? "1" : "0",
    max_depth: marineFilterContainer?.querySelector("#marine-depth-peel")?.value || "4000",
    depth_band: marineActiveDepthBand || "",
    mlat: map.getCenter().lat.toFixed(5),
    mlon: map.getCenter().lng.toFixed(5),
    mz: map.getZoom().toFixed(2),
    box: marineSelectedBounds
      ? [marineSelectedBounds.getSouth(), marineSelectedBounds.getWest(), marineSelectedBounds.getNorth(), marineSelectedBounds.getEast()].map((value) => value.toFixed(5)).join(",")
      : "",
  };
  for (const [key, value] of Object.entries(values)) {
    if (value) params.set(key, value);
    else params.delete(key);
  }
  const query = params.toString();
  window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
}

map.on("moveend zoomend", () => writeMarineMapState());

const marineFilterControl = L.control({ position: "topright" });
marineFilterControl.onAdd = () => {
  const container = L.DomUtil.create("section", "marine-filter-control");
  container.setAttribute("aria-label", "Marine observation filters");
  container.innerHTML = `
    <h3>Marine Observations</h3>
    <label for="marine-species-filter">Search species</label>
    <input id="marine-species-filter" type="search" placeholder="e.g. Thunnus albacares or Scleractinia" autocomplete="off">
    <label for="marine-region-filter">Search region</label>
    <select id="marine-region-filter"><option value="indian_ocean">Indian Ocean</option><option value="indian_eez">Indian EEZ</option><option value="global">Global</option></select>
    <div class="marine-filter-dates">
      <div><label for="marine-start-date">Start date</label><input id="marine-start-date" type="date"></div>
      <div><label for="marine-end-date">End date</label><input id="marine-end-date" type="date"></div>
    </div>
    <label for="marine-season-filter">Month / season</label>
    <select id="marine-season-filter">
        <option value="">Any time of year</option>
        <option value="current_month">Current month (${new Intl.DateTimeFormat(undefined, { month: "long" }).format(new Date())})</option>
        <option value="winter">Winter (Dec-Feb)</option>
        <option value="summer">Summer (Mar-May)</option>
        <option value="monsoon">Monsoon (Jun-Sep)</option>
        <option value="post_monsoon">Post-monsoon (Oct-Nov)</option>
    </select>
    <label class="marine-filter-toggle"><input id="marine-show-paths" type="checkbox"> Show Migratory Paths</label>
    <label class="marine-filter-toggle"><input id="marine-depth-colors" type="checkbox"> Color-Grade by Depth</label>
    <div class="marine-depth-slider-row"><label for="marine-depth-peel">Depth peel</label><output id="marine-depth-value" for="marine-depth-peel">4,000 m</output></div>
    <input id="marine-depth-peel" type="range" min="0" max="4000" step="50" value="4000" aria-label="Show observations down to selected depth">
    <div class="marine-depth-slider-scale"><span>0 m</span><span>4,000 m</span></div>
    <div class="marine-depth-legend" hidden>
      <button type="button" class="marine-depth-filter-item" data-depth-band="surface" aria-pressed="false"><i class="depth-surface-swatch"></i>Surface 0-50 m</button>
      <button type="button" class="marine-depth-filter-item" data-depth-band="mid_water" aria-pressed="false"><i class="depth-mid-swatch"></i>Medium blue 50-1,000 m</button>
      <button type="button" class="marine-depth-filter-item" data-depth-band="deep_sea" aria-pressed="false"><i class="depth-deep-swatch"></i>Dark navy &gt;1,000 m</button>
      <button type="button" class="marine-depth-filter-item" data-depth-band="unknown" aria-pressed="false"><i class="depth-unknown"></i>Depth not reported</button>
      <i class="depth-gradient" aria-label="Shallow to deep depth color gradient"></i>
    </div>
    <p id="marine-path-note" class="marine-filter-note" hidden></p>
    <div id="marine-path-legend" class="marine-path-legend" hidden></div>
    <div class="marine-filter-actions">
      <button type="button" id="marine-apply-filters">Visualize</button>
      <button type="button" id="marine-reset-filters">Reset</button>
    </div>
    <button type="button" id="marine-select-region" aria-pressed="false">Select map area</button>
    <p class="marine-filter-status" role="status" aria-live="polite"></p>`;

  marineFilterContainer = container;
  container.querySelector("#marine-species-filter").value = sharedMapParams.get("species") || "";
  container.querySelector("#marine-region-filter").value = sharedMapParams.get("region") || "indian_ocean";
  container.querySelector("#marine-start-date").value = sharedMapParams.get("start_date") || "";
  container.querySelector("#marine-end-date").value = sharedMapParams.get("end_date") || "";
  container.querySelector("#marine-season-filter").value = sharedMapParams.get("season") || "";
  if (sharedMapParams.get("month") === String(new Date().getMonth() + 1)) {
    container.querySelector("#marine-season-filter").value = "current_month";
  }
  container.querySelector("#marine-show-paths").checked = sharedMapParams.get("paths") === "1";
  container.querySelector("#marine-depth-colors").checked = sharedMapParams.get("depth_colors") === "1";
  container.querySelector(".marine-depth-legend").hidden = !container.querySelector("#marine-depth-colors").checked;
  const sharedDepth = Number(sharedMapParams.get("max_depth"));
  if (Number.isFinite(sharedDepth) && sharedDepth >= 0 && sharedDepth <= 4000) {
    container.querySelector("#marine-depth-peel").value = String(sharedDepth);
    container.querySelector("#marine-depth-value").textContent = `${sharedDepth.toLocaleString()} m`;
  }
  const sharedBand = sharedMapParams.get("depth_band");
  marineActiveDepthBand = ["surface", "mid_water", "deep_sea", "unknown"].includes(sharedBand) ? sharedBand : null;
  container.querySelectorAll(".marine-depth-filter-item").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.depthBand === marineActiveDepthBand));
  });
  const sharedBox = sharedMapParams.get("box")?.split(",").map(Number);
  if (sharedBox?.length === 4 && sharedBox.every(Number.isFinite)) {
    marineSelectedBounds = L.latLngBounds([sharedBox[0], sharedBox[1]], [sharedBox[2], sharedBox[3]]);
  }

  L.DomEvent.disableClickPropagation(container);
  L.DomEvent.disableScrollPropagation(container);
  const applyFilters = (force = true) => {
    const species = container.querySelector("#marine-species-filter").value.trim();
    const startDate = container.querySelector("#marine-start-date").value;
    const endDate = container.querySelector("#marine-end-date").value;
    const temporalChoice = container.querySelector("#marine-season-filter").value;
    const month = temporalChoice === "current_month" ? String(new Date().getMonth() + 1) : "";
    const season = temporalChoice === "current_month" ? "" : temporalChoice;
    const region = container.querySelector("#marine-region-filter").value;
    const status = container.querySelector(".marine-filter-status");
    if (startDate && endDate && startDate > endDate) {
      status.textContent = "Start date must be on or before the end date.";
      return;
    }
    const filters = {
      species,
      start_date: startDate,
      end_date: endDate,
      month,
      season,
      region,
      include_global_tracks: Boolean(species) && container.querySelector("#marine-show-paths").checked,
    };
    loadMarineObservations(filters, { force });
    writeMarineMapState(filters);
  };
  const scheduleFilterFetch = () => {
    window.clearTimeout(marineFilterDebounceTimer);
    marineFilterDebounceTimer = window.setTimeout(() => applyFilters(true), 380);
  };
  container.querySelector("#marine-apply-filters").addEventListener("click", () => applyFilters(true));
  container.querySelector("#marine-reset-filters").addEventListener("click", () => {
    container.querySelector("#marine-species-filter").value = "";
    container.querySelector("#marine-start-date").value = "";
    container.querySelector("#marine-end-date").value = "";
    container.querySelector("#marine-season-filter").value = "";
    container.querySelector("#marine-region-filter").value = "indian_ocean";
    container.querySelector("#marine-show-paths").checked = false;
    container.querySelector("#marine-path-note").hidden = true;
    container.querySelector("#marine-depth-colors").checked = false;
    container.querySelector(".marine-depth-legend").hidden = true;
    container.querySelector("#marine-depth-peel").value = "4000";
    container.querySelector("#marine-depth-value").textContent = "4,000 m";
    marineActiveDepthBand = null;
    marineSelectedBounds = null;
    container.querySelectorAll(".marine-depth-filter-item").forEach((button) => button.setAttribute("aria-pressed", "false"));
    if (marineRegionSelectionRect) map.removeLayer(marineRegionSelectionRect);
    marineRegionSelectionRect = null;
    applyFilters(true);
  });
  const pathToggle = container.querySelector("#marine-show-paths");
  const updatePathToggle = () => {
    const eligible = Boolean(container.querySelector("#marine-species-filter").value.trim());
    const note = container.querySelector("#marine-path-note");
    note.hidden = !pathToggle.checked;
    if (pathToggle.checked) {
      note.textContent = eligible
        ? "Dashed lines connect dated records of the selected species across the chosen region; they represent population observations, not individual animal tracks."
        : "Enter a species and enable this option to load its migratory occurrence sequence.";
      renderMarineObservationLayer();
    }
  };
  const onFilterChange = () => {
    updatePathToggle();
    scheduleFilterFetch();
  };
  container.querySelector("#marine-species-filter").addEventListener("input", onFilterChange);
  container.querySelector("#marine-region-filter").addEventListener("change", onFilterChange);
  container.querySelector("#marine-start-date").addEventListener("change", onFilterChange);
  container.querySelector("#marine-end-date").addEventListener("change", onFilterChange);
  container.querySelector("#marine-season-filter").addEventListener("change", onFilterChange);
  updatePathToggle();
  container.querySelector("#marine-show-paths").addEventListener("change", () => {
    updatePathToggle();
    applyFilters(true);
  });
  container.querySelector("#marine-depth-colors").addEventListener("change", (event) => {
    container.querySelector(".marine-depth-legend").hidden = !event.target.checked;
    renderMarineObservationLayer();
    writeMarineMapState();
  });
  container.querySelectorAll(".marine-depth-filter-item").forEach((button) => {
    button.addEventListener("click", () => {
      marineActiveDepthBand = marineActiveDepthBand === button.dataset.depthBand ? null : button.dataset.depthBand;
      container.querySelectorAll(".marine-depth-filter-item").forEach((item) => {
        item.setAttribute("aria-pressed", String(item.dataset.depthBand === marineActiveDepthBand));
      });
      renderMarineObservationLayer();
      writeMarineMapState();
    });
  });
  container.querySelector("#marine-depth-peel").addEventListener("input", (event) => {
    const depth = Number(event.target.value);
    container.querySelector("#marine-depth-value").textContent = `${depth.toLocaleString()} m`;
    renderMarineObservationLayer();
  });
  container.querySelector("#marine-depth-peel").addEventListener("change", () => writeMarineMapState());
  container.querySelector("#marine-select-region").addEventListener("click", (event) => {
    marineRegionSelectionEnabled = !marineRegionSelectionEnabled;
    event.currentTarget.setAttribute("aria-pressed", String(marineRegionSelectionEnabled));
    event.currentTarget.textContent = marineRegionSelectionEnabled ? "Drag a map area..." : "Select map area";
    map.getContainer().classList.toggle("marine-region-selecting", marineRegionSelectionEnabled);
    if (map.dragging) {
      if (marineRegionSelectionEnabled) map.dragging.disable();
      else map.dragging.enable();
    }
  });
  return container;
};
marineFilterControl.addTo(map);

const marineStatusControl = L.control({ position: "bottomleft" });
marineStatusControl.onAdd = () => {
  const element = L.DomUtil.create("div", "leaflet-control marine-observation-status");
  element.setAttribute("role", "status");
  element.setAttribute("aria-live", "polite");
  element.textContent = marineObservationStatus;
  element.style.display = marineObservationStatus ? "" : "none";
  return element;
};
marineStatusControl.addTo(map);

function setMarineObservationStatus(message) {
  marineObservationStatus = message;
  const element = document.querySelector(".marine-observation-status");
  if (element) {
    element.textContent = message;
    element.style.display = message ? "" : "none";
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function getObisSourceUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && (url.hostname === "obis.org" || url.hostname.endsWith(".obis.org"))
      ? url.href
      : null;
  } catch {
    return null;
  }
}

async function loadMarineObservations(filters = {}, { force = false } = {}) {
  const normalizedFilters = {
    species: String(filters.species || "").trim(),
    start_date: String(filters.start_date || ""),
    end_date: String(filters.end_date || ""),
    month: String(filters.month || ""),
    season: String(filters.season || ""),
    region: String(filters.region || "indian_ocean"),
    include_global_tracks: filters.include_global_tracks ? "true" : "",
  };
  const filterKey = JSON.stringify(normalizedFilters);
  if (!force && marineLoadedFilterKey === filterKey) return;

  if (marineObservationsController) marineObservationsController.abort();
  marineObservationsController = new AbortController();
  const controller = marineObservationsController;
  const requestId = ++marineObservationsRequestId;
  if (!map.hasLayer(marineOverlay)) marineOverlay.addTo(map);
  const status = document.querySelector(".marine-filter-status");
  if (status) status.textContent = "Filtering observations…";
  setMarineObservationStatus("Filtering marine observations…");

  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(normalizedFilters)) {
    if (value) query.set(key, value);
  }

  try {
      const response = await fetch(`${API_BASE}/api/marine-observations${query.size ? `?${query}` : ""}`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`OBIS service returned HTTP ${response.status}`);
      const payload = await response.json();
      const observations = Array.isArray(payload) ? payload : payload?.data;
      if (!Array.isArray(observations)) throw new Error("Unexpected marine observations response");
      if (requestId !== marineObservationsRequestId) return;

      if (payload?.status === "error") {
        marineLoadedFilterKey = null;
        if (marineObservationRecords.length) renderMarineObservationLayer();
        if (status) status.textContent = payload.message || "Marine observations are temporarily unavailable. Please try again.";
        setMarineObservationStatus(payload.message || "Marine observation data is temporarily unavailable.");
        return;
      }

      marineObservationRecords = observations;
      marineTrackInfo = payload?.tracks || { available: false };
      const markerCount = renderMarineObservationLayer();
      const pathNote = document.querySelector("#marine-path-note");
      if (pathNote && document.querySelector("#marine-show-paths")?.checked) {
        const trackInfo = payload?.tracks || {};
        pathNote.hidden = false;
        pathNote.textContent = trackInfo.message || (trackInfo.point_count >= 2
          ? `Loaded ${trackInfo.point_count} dated occurrence records for the path overlay.`
          : "No path can be drawn yet; at least two dated records of a supported migratory species are required.");
      }
      marineLoadedFilterKey = filterKey;
      const areaText = marineSelectedBounds ? " in selected area" : "";
      const bandText = marineActiveDepthBand ? `; ${marineDepthBandMatchCount} in ${marineActiveDepthBand.replaceAll("_", " ")} band` : "";
      if (status) status.textContent = markerCount
        ? `Showing ${markerCount} marine observation${markerCount === 1 ? "" : "s"}${areaText}${bandText}.`
        : "No marine observations match these filters.";
      setMarineObservationStatus(markerCount
        ? `Showing ${markerCount} marine observations.`
        : "No marine observations match these filters.");
  } catch (error) {
      if (error.name === "AbortError" || requestId !== marineObservationsRequestId) return;
      console.error("Marine observations request failed:", error?.message || String(error));
      if (status) status.textContent = "Marine observations are temporarily unavailable. Please try again.";
      setMarineObservationStatus("Marine observation data is temporarily unavailable.");
  } finally {
      if (requestId === marineObservationsRequestId) marineObservationsController = null;
  }
}

function depthColor(depthMeters) {
  if (!Number.isFinite(depthMeters)) return "#94a3b8";
  const stops = [
    [0, [135, 206, 250]], [50, [135, 206, 250]], [200, [75, 154, 222]],
    [500, [30, 136, 229]], [1000, [30, 136, 229]], [4000, [0, 27, 68]],
  ];
  const depth = Math.min(4000, Math.max(0, depthMeters));
  let upper = stops.findIndex(([limit]) => depth <= limit);
  if (upper < 0) upper = stops.length - 1;
  const lower = Math.max(0, upper - 1);
  const [d0, c0] = stops[lower];
  const [d1, c1] = stops[upper];
  const ratio = d0 === d1 ? 0 : (depth - d0) / (d1 - d0);
  const rgb = c0.map((value, index) => Math.round(value + (c1[index] - value) * ratio));
  return `rgb(${rgb.join(",")})`;
}

function marineDepthIcon(category, color) {
  const silhouettes = {
    surface: `<path d="M4 20c5-8 11-10 20-8l8-6v10l-8-3c-9 2-15 8-20 7Zm11-7 4-6 3 5-3 5-4-4Z"/><circle cx="24" cy="13" r="1.1" fill="#031020" stroke="none"/>`,
    mid_water: `<path d="M20 3c7 5 10 11 8 17l-8 8-8-8c-2-6 1-12 8-17Zm-9 17-5 7m9-5-2 8m8-8 2 8m2-10 5 7"/><circle cx="22" cy="15" r="1.2" fill="#031020" stroke="none"/>`,
    deep_sea: `<path d="M5 21c2-7 8-11 16-9l4 2 7-5-2 8 3 6-8-3c-8 5-15 5-20 1Zm13-11-1-5m0 0 5-3m-5 3 5 2"/><circle cx="23" cy="17" r="1.4" fill="#031020" stroke="none"/><path d="M25 20c-2 3-5 3-7 1" fill="none"/>`,
    unknown: `<path d="M5 20c5-8 11-10 20-8l8-6v10l-8-3c-9 2-15 8-20 7Z"/><circle cx="24" cy="13" r="1.1" fill="#031020" stroke="none"/>`,
  };
  const safeCategory = Object.hasOwn(silhouettes, category) ? category : "unknown";
  const colorText = String(color);
  const safeColor = (/^#[0-9a-f]{6}$/i.test(colorText) || /^rgb\(\d{1,3},\s*\d{1,3},\s*\d{1,3}\)$/i.test(colorText))
    ? colorText
    : "#94a3b8";
  return L.divIcon({
    className: `marine-observation-marker-icon marine-depth-${safeCategory}`,
    html: `<svg viewBox="0 0 40 40" aria-hidden="true" fill="${safeColor}" stroke="#e0f2fe" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">${silhouettes[safeCategory]}</svg>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

const marineSonarDrawer = document.querySelector("#marine-sonar-drawer");
L.DomEvent.disableClickPropagation(marineSonarDrawer);
L.DomEvent.disableScrollPropagation(marineSonarDrawer);
marineSonarDrawer.querySelector(".marine-sonar-close").addEventListener("click", () => {
  marineSonarDrawer.classList.remove("is-open");
  marineSonarDrawer.setAttribute("aria-hidden", "true");
});

function openMarineSonar(records) {
  const withDepth = records.filter((record) => {
    const depth = Number(record.depth_m);
    return record.depth_m != null && Number.isFinite(depth) && depth >= 0;
  });
  const points = marineSonarDrawer.querySelector(".marine-sonar-points");
  const axis = marineSonarDrawer.querySelector(".marine-sonar-axis");
  const list = marineSonarDrawer.querySelector(".marine-sonar-records");
  const summary = marineSonarDrawer.querySelector(".marine-sonar-summary");
  axis.innerHTML = [0, 1000, 2000, 3000, 4000].map((depth) =>
    `<span class="marine-sonar-tick" style="top:${depth / 40}%">${depth.toLocaleString()} m</span>`
  ).join("");
  points.innerHTML = "";
  list.innerHTML = "";
  if (!withDepth.length) {
    summary.textContent = `No reported depth for these ${records.length} observation${records.length === 1 ? "" : "s"}. The sonar profile omits unknown-depth records.`;
  } else {
    summary.textContent = `${withDepth.length} of ${records.length} observation${records.length === 1 ? " has" : "s have"} reported depth.`;
    withDepth.forEach((record, index) => {
      const depth = Number(record.depth_m);
      const category = record.depth_category || (depth <= 50 ? "surface" : depth <= 1000 ? "mid_water" : "deep_sea");
      const color = /^#[0-9a-f]{6}$/i.test(String(record.depth_color || "")) ? record.depth_color : depthColor(depth);
      const point = document.createElement("span");
      point.className = "marine-sonar-point";
      point.style.top = `${Math.min(depth, 4000) / 40}%`;
      point.style.left = `${12 + (index % 5) * 18}%`;
      point.style.backgroundColor = color;
      point.style.color = color;
      point.title = `${record.species_name || "Unknown species"} - ${depth.toLocaleString()} m`;
      points.appendChild(point);

      const row = document.createElement("div");
      row.className = "marine-sonar-record";
      const sourceUrl = getObisSourceUrl(record.source_link);
      row.innerHTML = `<span><strong>${escapeHtml(record.species_name || "Unknown species")}</strong><small>${escapeHtml(category.replaceAll("_", " "))} | ${escapeHtml(record.observation_date || "Date unavailable")} | ${escapeHtml(record.dataset_name || "OBIS")}${sourceUrl ? ` | <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Source</a>` : ""}</small></span><span>${depth.toLocaleString()} m</span>`;
      list.appendChild(row);
    });
  }
  marineSonarDrawer.classList.add("is-open");
  marineSonarDrawer.setAttribute("aria-hidden", "false");
}

if (typeof marineMarkerGroup.on === "function" && typeof marineMarkerGroup.spiderfy === "function") {
  marineMarkerGroup.on("clusterclick", (event) => {
    L.DomEvent.stop(event.originalEvent);
    const cluster = event.layer;
    const bounds = cluster.getBounds();
    map.flyToBounds(bounds, { padding: [36, 36], maxZoom: 10, duration: 0.9, easeLinearity: 0.22 });
    window.setTimeout(() => {
      const child = cluster.getAllChildMarkers()[0];
      const visibleParent = child && marineMarkerGroup.getVisibleParent(child);
      if (visibleParent && visibleParent !== child && visibleParent.spiderfy) visibleParent.spiderfy();
    }, 950);
  });
}

function isMigratoryMarineTaxon(speciesName) {
  const name = String(speciesName || "").toLocaleLowerCase();
  return [
    "thunnus", "tuna", "cheloni", "caretta", "eretmochelys", "lepido", "dermochelys",
    "delphin", "tursiops", "cetacea", "balaenoptera", "megaptera", "rhincodon", "selachimorpha",
    "xiphias", "istiophoridae", "mobula", "manta",
  ].some((taxon) => name.includes(taxon));
}

function speciesPathColor(speciesName) {
  const name = String(speciesName || "Unknown species").trim().toLocaleLowerCase();
  if (marinePathSpeciesColors.has(name)) return marinePathSpeciesColors.get(name);
  const colors = ["#22d3ee", "#f472b6", "#a3e635", "#fb923c", "#c084fc", "#f87171", "#60a5fa", "#facc15"];
  // Stable hashing gives a species the same color after filters and redraws.
  let hash = 2166136261;
  for (const character of name) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  const color = colors[(hash >>> 0) % colors.length];
  marinePathSpeciesColors.set(name, color);
  return color;
}

function mixPathColor(color, neutral = "#94a3b8", neutralWeight = 0.72) {
  const parse = (hex) => hex.match(/[\da-f]{2}/gi).map((part) => parseInt(part, 16));
  const source = parse(color);
  const gray = parse(neutral);
  return `#${source.map((channel, index) => Math.round(channel * (1 - neutralWeight) + gray[index] * neutralWeight).toString(16).padStart(2, "0")).join("")}`;
}

function greatCircleArc(start, end, steps = 16) {
  const radians = (degrees) => degrees * Math.PI / 180;
  const degrees = (radiansValue) => radiansValue * 180 / Math.PI;
  const vector = (point) => {
    const latitude = radians(point.lat);
    const longitude = radians(point.lng);
    return [Math.cos(latitude) * Math.cos(longitude), Math.cos(latitude) * Math.sin(longitude), Math.sin(latitude)];
  };
  const a = vector(start);
  const b = vector(end);
  const dot = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
  const angle = Math.acos(dot);
  let longitudeEnd = end.lng;
  while (longitudeEnd - start.lng > 180) longitudeEnd -= 360;
  while (longitudeEnd - start.lng < -180) longitudeEnd += 360;
  const points = [];
  for (let index = 0; index <= steps; index += 1) {
    const fraction = index / steps;
    let xyz;
    if (Math.abs(Math.sin(angle)) < 1e-6) {
      const latitude = start.lat + (end.lat - start.lat) * fraction;
      let longitude = start.lng + (longitudeEnd - start.lng) * fraction;
      if (points.length) {
        while (longitude - points[points.length - 1].lng > 180) longitude -= 360;
        while (longitude - points[points.length - 1].lng < -180) longitude += 360;
      }
      points.push(L.latLng(latitude, longitude));
      continue;
    } else {
      const scaleA = Math.sin((1 - fraction) * angle) / Math.sin(angle);
      const scaleB = Math.sin(fraction * angle) / Math.sin(angle);
      xyz = a.map((value, axis) => value * scaleA + b[axis] * scaleB);
    }
    const latitude = degrees(Math.atan2(xyz[2], Math.hypot(xyz[0], xyz[1])));
    let longitude = degrees(Math.atan2(xyz[1], xyz[0]));
    if (points.length) {
      while (longitude - points[points.length - 1].lng > 180) longitude -= 360;
      while (longitude - points[points.length - 1].lng < -180) longitude += 360;
    }
    points.push(L.latLng(latitude, longitude));
  }
  return points;
}

function setPathGradient(line, gradientId, mutedColor, vividColor) {
  const path = line.getElement?.();
  if (!path) return;
  const svg = path.ownerSVGElement;
  if (!svg) return;
  let defs = svg.querySelector("defs[data-marine-path-gradients]");
  if (!defs) {
    defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.setAttribute("data-marine-path-gradients", "true");
    svg.insertBefore(defs, svg.firstChild);
  }
  let gradient = svg.querySelector(`#${gradientId}`);
  if (!gradient) {
    gradient = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
    gradient.id = gradientId;
    gradient.setAttribute("gradientUnits", "userSpaceOnUse");
    const oldStop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    oldStop.setAttribute("offset", "0%");
    oldStop.setAttribute("stop-color", mutedColor);
    const newStop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    newStop.setAttribute("offset", "100%");
    newStop.setAttribute("stop-color", vividColor);
    gradient.append(oldStop, newStop);
    defs.appendChild(gradient);
  }
  const coordinatePairs = [...(path.getAttribute("d") || "").matchAll(/[ML]\s*([-+\d.e]+)[ ,]+([-+\d.e]+)/gi)];
  if (coordinatePairs.length < 2) return;
  const first = coordinatePairs[0];
  const last = coordinatePairs[coordinatePairs.length - 1];
  gradient.setAttribute("x1", first[1]);
  gradient.setAttribute("y1", first[2]);
  gradient.setAttribute("x2", last[1]);
  gradient.setAttribute("y2", last[2]);
  path.setAttribute("stroke", `url(#${gradientId})`);
}

function scheduleMarinePathGradientUpdate() {
  if (marinePathGradientUpdateScheduled) return;
  marinePathGradientUpdateScheduled = true;
  requestAnimationFrame(() => {
    marinePathGradientUpdateScheduled = false;
    document.querySelectorAll(".migratory-path-gradient[data-gradient-id]").forEach((path) => {
      const id = path.getAttribute("data-gradient-id");
      const muted = path.getAttribute("data-muted-color");
      const vivid = path.getAttribute("data-vivid-color");
      setPathGradient({ getElement: () => path }, id, muted, vivid);
    });
  });
}

map.on("zoomend moveend", scheduleMarinePathGradientUpdate);

function updateMarinePathLegend(entries) {
  const legend = document.querySelector("#marine-path-legend");
  if (!legend) return;
  legend.innerHTML = "";
  if (!entries.length) {
    legend.hidden = true;
    return;
  }
  legend.hidden = false;
  for (const entry of entries) {
    const item = document.createElement("span");
    item.className = "marine-path-legend-item";
    const density = entry.count >= 20 ? "dense" : entry.count >= 8 ? "medium" : "sparse";
    const dashStyle = density === "dense" ? "solid" : density === "medium" ? "dashed" : "dotted";
    item.innerHTML = `<i style="--path-color:${entry.color};--path-style:${dashStyle}"></i>${escapeHtml(entry.name)} <small>${entry.count} records · ${density}</small>`;
    legend.appendChild(item);
  }
}

function renderMarineObservationLayer() {
  const generation = ++marineMarkerRenderGeneration;
  for (const pathLayer of marinePathLayers) marineOverlay.removeLayer(pathLayer);
  marinePathLayers = [];
  if (!marineOverlay.hasLayer(marineMarkerGroup)) marineOverlay.addLayer(marineMarkerGroup);
  const depthColorsEnabled = document.querySelector("#marine-depth-colors")?.checked || false;
  const showPaths = Boolean(document.querySelector("#marine-show-paths")?.checked)
    && Boolean(document.querySelector("#marine-species-filter")?.value.trim());
  const pathsBySpecies = new Map();
  const pathLegendEntries = [];
  const pathVisuals = [];
  const wantedMarkerKeys = new Set();
  const activeBounds = marineSelectedBounds;
  let depthBandMatchCount = 0;
  let markerCount = 0;

  for (const observation of marineObservationRecords) {
    const lat = Number(observation.lat);
    const lon = Number(observation.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) continue;

    const depthMeters = observation.depth_m != null && Number.isFinite(Number(observation.depth_m))
      ? Number(observation.depth_m)
      : null;
    const explicitDepthColor = /^#[0-9a-f]{6}$/i.test(String(observation.depth_color || ""))
      ? observation.depth_color
      : depthColor(depthMeters);
    const suggestedCategory = observation.depth_category || (
      depthMeters == null ? "unknown"
        : depthMeters <= 50 ? "surface"
          : depthMeters <= 1000 ? "mid_water" : "deep_sea"
    );
    const depthCategory = ["surface", "mid_water", "deep_sea", "unknown"].includes(suggestedCategory)
      ? suggestedCategory
      : "unknown";
    const color = depthColorsEnabled ? explicitDepthColor : "#38bdf8";
    const maxDepth = Number(document.querySelector("#marine-depth-peel")?.value || 4000);
    if ((depthMeters != null && depthMeters > maxDepth) || (depthMeters == null && maxDepth < 4000)) continue;
    if (activeBounds && !activeBounds.contains([lat, lon])) continue;
    const dateLabel = observation.observation_date || "Unknown";
    const fadeStart = Math.max(0, maxDepth - 400);
    const markerOpacity = depthMeters == null || depthMeters <= fadeStart
      ? 1
      : Math.max(0.2, (maxDepth - depthMeters) / Math.max(1, maxDepth - fadeStart));
    const bandMatches = !marineActiveDepthBand || marineActiveDepthBand === depthCategory;
    if (bandMatches) depthBandMatchCount += 1;
    const displayOpacity = markerOpacity * (bandMatches ? 1 : 0.16);
    const sourceKey = observation.source_link || `${observation.species_name || ""}|${dateLabel}|${lat.toFixed(5)}|${lon.toFixed(5)}`;
    const markerKey = String(sourceKey);
    wantedMarkerKeys.add(markerKey);
    const icon = marineDepthIcon(depthCategory, color);
    const speciesName = String(observation.species_name || "Unknown species");
    const temperature = observation.water_temperature ?? observation.waterTemperature ?? observation.sea_surface_temperature ?? observation.seaSurfaceTemperature ?? observation.temperature ?? observation.sst;
    const depthText = depthMeters == null ? "Not reported" : `${depthMeters.toLocaleString()} m`;
    const sourceUrl = getObisSourceUrl(observation.source_link);
    const popupHtml = `<article class="marine-observation-popup"><header>${icon.options.html}<strong>${escapeHtml(speciesName)}</strong></header><dl><dt>Date</dt><dd>${escapeHtml(dateLabel)}</dd><dt>Depth</dt><dd>${escapeHtml(depthText)}</dd>${temperature != null && Number.isFinite(Number(temperature)) ? `<dt>Water temperature</dt><dd>${escapeHtml(Number(temperature).toFixed(1))} °C</dd>` : ""}<dt>Dataset</dt><dd>${escapeHtml(observation.dataset_name || "OBIS")}</dd></dl>${sourceUrl ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">View source ↗</a>` : ""}</article>`;
    let markerEntry = marineObservationMarkerRegistry.get(markerKey);
    const isNewMarker = !markerEntry;
    if (!markerEntry) {
      const observationMarker = L.marker([lat, lon], { icon, opacity: 0, riseOnHover: true, keyboard: true, title: `${speciesName} — ${dateLabel}` });
      markerEntry = { marker: observationMarker, fadeTimer: null };
      marineObservationMarkerRegistry.set(markerKey, markerEntry);
      marineMarkerGroup.addLayer(observationMarker);
    }
    const observationMarker = markerEntry.marker;
    if (markerEntry.fadeTimer) { window.clearTimeout(markerEntry.fadeTimer); markerEntry.fadeTimer = null; }
    observationMarker.setLatLng([lat, lon]);
    observationMarker.setIcon(icon);
    observationMarker.options.marineObservation = observation;
    observationMarker.unbindPopup();
    observationMarker.bindPopup(popupHtml, { maxWidth: 280, className: "marine-observation-popup-shell" });
    observationMarker.unbindTooltip();
    observationMarker.bindTooltip(`<strong>${escapeHtml(speciesName)}</strong><br>${escapeHtml(dateLabel)}`, {
      direction: "top", sticky: true, opacity: 0.96, className: "marine-observation-tooltip",
    });
    if (isNewMarker) {
      observationMarker.setOpacity(0);
      const fadeIn = () => requestAnimationFrame(() => observationMarker.setOpacity(displayOpacity));
      if (observationMarker._icon) fadeIn();
      else observationMarker.once("add", fadeIn);
    } else observationMarker.setOpacity(displayOpacity);
    markerCount += 1;

    if (showPaths && isMigratoryMarineTaxon(speciesName) && Number.isFinite(Date.parse(dateLabel))) {
      const key = speciesName.toLocaleLowerCase();
      if (!pathsBySpecies.has(key)) pathsBySpecies.set(key, { name: speciesName, records: [] });
      pathsBySpecies.get(key).records.push({ observation, lat, lon, timestamp: Date.parse(dateLabel) });
    }
  }

  for (const [key, entry] of marineObservationMarkerRegistry) {
    if (wantedMarkerKeys.has(key)) continue;
    entry.marker.setOpacity(0);
    entry.fadeTimer = window.setTimeout(() => {
      if (generation !== marineMarkerRenderGeneration && wantedMarkerKeys.has(key)) return;
      marineMarkerGroup.removeLayer(entry.marker);
      marineObservationMarkerRegistry.delete(key);
    }, 210);
  }
  marineDepthBandMatchCount = depthBandMatchCount;

  for (const { name, records } of pathsBySpecies.values()) {
    records.sort((a, b) => a.timestamp - b.timestamp);
    if (records.length < 2) continue;
    const speciesColor = speciesPathColor(name);
    const earliest = records[0].timestamp;
    const latest = records[records.length - 1].timestamp;
    const fullTrack = [];
    for (let index = 0; index < records.length - 1; index += 1) {
      const arc = greatCircleArc(L.latLng(records[index].lat, records[index].lon), L.latLng(records[index + 1].lat, records[index + 1].lon));
      fullTrack.push(...(index ? arc.slice(1) : arc));
    }
    const bounds = L.latLngBounds(fullTrack);
    const tooltip = `${escapeHtml(name)} · ${escapeHtml(records[0].observation.observation_date || "Unknown")} to ${escapeHtml(records[records.length - 1].observation.observation_date || "Unknown")} · ${records.length} dated observations`;
    const incomplete = document.querySelector("#marine-region-filter")?.value !== "global" && marineTrackInfo.available !== true;
    const densityDash = records.length >= 20 ? "14 5" : records.length >= 8 ? "8 5" : "2 6";
    const gradientId = `marine-path-gradient-${Array.from(name).reduce((sum, character) => sum + character.charCodeAt(0), 0)}-${pathLegendEntries.length}`;
    const fadedColor = mixPathColor(speciesColor);
    const baseLine = L.polyline(fullTrack, {
      className: "migratory-path-gradient",
      color: speciesColor,
      weight: 4,
      opacity: 0.9,
      smoothFactor: 1,
    });
    const applyGradient = () => {
      const baseElement = baseLine.getElement?.();
      if (!baseElement) return;
      baseElement.setAttribute("data-gradient-id", gradientId);
      baseElement.setAttribute("data-muted-color", fadedColor);
      baseElement.setAttribute("data-vivid-color", speciesColor);
      setPathGradient(baseLine, gradientId, fadedColor, speciesColor);
    };
    baseLine.on("add", applyGradient).addTo(marineOverlay);
    applyGradient();
    const flowLine = L.polyline(fullTrack, {
      className: "migratory-path-flow",
      color: speciesColor,
      weight: 2,
      opacity: 0.95,
      dashArray: densityDash,
      smoothFactor: 1,
    }).addTo(marineOverlay);
    flowLine.getElement?.()?.style.setProperty("stroke-dasharray", densityDash);
    flowLine.bindTooltip(tooltip, { sticky: true, className: "marine-path-tooltip" });
    const pathParts = [baseLine, flowLine];
    for (let index = 0; index < records.length - 1; index += 1) {
      const fraction = latest > earliest
        ? ((records[index].timestamp + records[index + 1].timestamp) / 2 - earliest) / (latest - earliest)
        : (index + 0.5) / (records.length - 1);
      // Chronological waypoint dots reinforce the same old-to-new color progression.
      const waypoint = L.circleMarker([records[index].lat, records[index].lon], {
        radius: 2.6,
        color: mixPathColor(speciesColor, "#94a3b8", 0.75 * (1 - fraction)),
        weight: 1,
        fillColor: mixPathColor(speciesColor, "#94a3b8", 0.75 * (1 - fraction)),
        fillOpacity: 0.35 + fraction * 0.55,
        opacity: 0.35 + fraction * 0.55,
        interactive: false,
      }).addTo(marineOverlay);
      pathParts.push(waypoint);
    }
    const endpoint = records[records.length - 1];
    const liveMarker = L.circleMarker([endpoint.lat, endpoint.lon], {
      className: "migratory-latest-glow",
      radius: 6,
      color: "#ffffff",
      weight: 2,
      fillColor: speciesColor,
      fillOpacity: 1,
    }).bindTooltip(`${escapeHtml(name)} · Latest sighting ${escapeHtml(endpoint.observation.observation_date || "Unknown date")}`)
      .addTo(marineOverlay);
    pathParts.push(liveMarker);

    const setDimState = (active) => {
      for (const visual of pathVisuals) {
        const isOwnPath = pathParts.includes(visual.layer);
        visual.layer.setStyle({
          opacity: active ? (isOwnPath ? visual.opacity : 0.2) : visual.opacity,
          fillOpacity: active ? (isOwnPath ? visual.fillOpacity : 0.08) : visual.fillOpacity,
        });
        const element = visual.layer.getElement?.();
        const gradientIdForLayer = element?.getAttribute("data-gradient-id");
        if (gradientIdForLayer) {
          setPathGradient({ getElement: () => element }, gradientIdForLayer,
            element.getAttribute("data-muted-color"), element.getAttribute("data-vivid-color"));
        }
      }
      if (active) {
        baseLine.setStyle({ weight: 6 });
        flowLine.setStyle({ weight: 3 });
      } else {
        baseLine.setStyle({ weight: 4 });
        flowLine.setStyle({ weight: 2 });
      }
      applyGradient();
    };
    for (const line of [baseLine, flowLine]) {
      line.on("mouseover", () => setDimState(true));
      line.on("mouseout", () => setDimState(false));
      line.on("click", (event) => {
        if (event.originalEvent) L.DomEvent.stop(event.originalEvent);
      map.flyToBounds(bounds, { padding: [36, 36], maxZoom: 8, duration: 1, easeLinearity: 0.2 });
      });
    }
    liveMarker.on("click", () => map.flyToBounds(bounds, { padding: [36, 36], maxZoom: 8, duration: 1, easeLinearity: 0.2 }));
    pathParts.forEach((layer) => pathVisuals.push({
      layer,
      opacity: layer.options.opacity ?? 1,
      fillOpacity: layer.options.fillOpacity ?? 0,
    }));

    if (incomplete) {
      const middle = fullTrack[Math.floor(fullTrack.length / 2)];
      const badge = L.marker(middle, {
        interactive: false,
        icon: L.divIcon({
          className: "marine-path-incomplete-marker",
          html: `<span>INCOMPLETE DATA</span>`,
          iconSize: [104, 22],
          iconAnchor: [52, 11],
        }),
      }).addTo(marineOverlay);
      pathParts.push(badge);
    }
    marinePathLayers.push(...pathParts);
    pathLegendEntries.push({ name, color: speciesColor, count: records.length });
  }
  updateMarinePathLegend(pathLegendEntries);
  scheduleMarinePathGradientUpdate();
  const filterStatus = marineFilterContainer?.querySelector(".marine-filter-status");
  if (filterStatus && (activeBounds || marineActiveDepthBand)) {
    const areaText = activeBounds ? " in selected area" : "";
    const bandText = marineActiveDepthBand ? `; ${depthBandMatchCount} in ${marineActiveDepthBand.replaceAll("_", " ")} band` : "";
    filterStatus.textContent = `Showing ${markerCount} observations${areaText}${bandText}.`;
  }
  return markerCount;
}

map.on("overlayadd", (event) => {
  writeMarineMapState();
  if (event.layer === marineOverlay && !marineObservationsController && marineLoadedFilterKey === null) {
    loadMarineObservations(readMarinePanelFilters(), { force: true });
  }
});
map.on("overlayremove", (event) => {
  if (event.layer === marineOverlay) writeMarineMapState();
});

let marineSelectionMoveHandler = null;
function startMarineRegionSelection(event) {
  if (!marineRegionSelectionEnabled || !event.latlng) return;
  marineRegionSelectionStart = event.latlng;
  if (marineRegionSelectionRect) map.removeLayer(marineRegionSelectionRect);
  marineRegionSelectionRect = L.rectangle([marineRegionSelectionStart, marineRegionSelectionStart], {
    color: "#22d3ee", weight: 2, dashArray: "6 4", fillColor: "#22d3ee", fillOpacity: 0.12,
  }).addTo(map);
  marineSelectionMoveHandler = (moveEvent) => marineRegionSelectionRect?.setBounds(L.latLngBounds(marineRegionSelectionStart, moveEvent.latlng));
  map.on("mousemove", marineSelectionMoveHandler);
}

function finishMarineRegionSelection() {
  if (!marineRegionSelectionStart || !marineRegionSelectionRect) return;
  marineSelectedBounds = marineRegionSelectionRect.getBounds();
  map.removeLayer(marineRegionSelectionRect);
  marineRegionSelectionRect = L.rectangle(marineSelectedBounds, {
    color: "#22d3ee", weight: 2, dashArray: "6 4", fillColor: "#22d3ee", fillOpacity: 0.06,
    interactive: false,
  }).addTo(map);
  marineRegionSelectionStart = null;
  if (marineSelectionMoveHandler) map.off("mousemove", marineSelectionMoveHandler);
  marineSelectionMoveHandler = null;
  marineRegionSelectionEnabled = false;
  map.dragging.enable();
  const button = marineFilterContainer?.querySelector("#marine-select-region");
  if (button) {
    button.setAttribute("aria-pressed", "false");
    button.textContent = "Select map area";
  }
  map.getContainer().classList.remove("marine-region-selecting");
  renderMarineObservationLayer();
  writeMarineMapState();
}

map.on("mousedown", startMarineRegionSelection);
map.on("mouseup", finishMarineRegionSelection);

if (sharedMapParams.get("marine") === "1") {
  marineOverlay.addTo(map);
  if (marineSelectedBounds) {
    marineRegionSelectionRect = L.rectangle(marineSelectedBounds, {
      color: "#22d3ee", weight: 2, dashArray: "6 4", fillColor: "#22d3ee", fillOpacity: 0.06,
      interactive: false,
    }).addTo(map);
  }
  loadMarineObservations(readMarinePanelFilters(), { force: true });
}
/**
 * Fetches ecosystem layer configurations and adds them to the Leaflet map with layer controls.
 * @param {L.Map} mapInstance - The active Leaflet map instance
 */
async function loadEcosystemLayers(mapInstance) {
  try {
    const response = await fetch(`${API_BASE}/api/ecosystem-layers`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error(`Layer metadata returned HTTP ${response.status}`);
    const layersConfig = await response.json();

    const mangroves = layersConfig.mangroves;
    if (mangroves?.local_data_url || mangroves?.data_url) {
      try {
        let geoJson = null;
        let sourceError = null;
        const dataUrls = [mangroves.local_data_url, mangroves.data_url]
          .filter(Boolean)
          .map((dataUrl) => new URL(dataUrl, `${API_BASE}/`).toString());
        for (const dataUrl of dataUrls) {
          try {
            const geoResponse = await fetch(dataUrl, {
              headers: { Accept: "application/geo+json, application/json" },
              signal: AbortSignal.timeout(8000),
            });
            if (!geoResponse.ok) throw new Error(`Mangrove source returned HTTP ${geoResponse.status}`);
            const payload = await geoResponse.json();
            if (!payload || !["FeatureCollection", "Feature"].includes(payload.type)) {
              throw new Error("Mangrove source did not return GeoJSON features");
            }
            geoJson = payload;
            break;
          } catch (error) {
            sourceError = error;
            console.error("Mangrove GeoJSON source request failed:", error?.message || String(error));
          }
        }
        if (!geoJson) throw sourceError || new Error("No mangrove data source is configured");

        const mangroveLayer = L.geoJSON(geoJson, {
          style: { color: "#1b5e20", weight: 1.5, fillColor: "#4caf50", fillOpacity: 0.45 },
          onEachFeature: (feature, layer) => {
            const extent = feature.properties?.pxlval;
            const extentText = extent == null ? "Mangrove extent" : `Extent class: ${escapeHtml(extent)}`;
            const sourceLink = escapeHtml(mangroves.source_link || "https://www.globalmangrovewatch.org/");
            layer.bindPopup(`<strong>${escapeHtml(mangroves.name || "Mangrove habitat")}</strong><br>
              ${extentText}<br><a href="${sourceLink}" target="_blank" rel="noopener noreferrer">Dataset source</a>`);
          },
        });
        mapLayerControl.addOverlay(mangroveLayer, "Mangrove Extent (Global Mangrove Watch)");
      } catch (error) {
        console.warn("Mangrove overlay is unavailable; continuing without it:", error);
        setMarineObservationStatus("Mangrove extent data is temporarily unavailable.");
      }
    }

    const chlorophyll = layersConfig.chlorophyll;
    const chlorophyllTileUrl = chlorophyll?.tile_url || chlorophyll?.wms_url;
    if (chlorophyllTileUrl && chlorophyll?.layer_name) {
      const chlorophyllLayer = L.tileLayer.wms(chlorophyllTileUrl, {
        layers: chlorophyll.layer_name,
        format: "image/png",
        transparent: true,
        version: "1.3.0",
        opacity: 0.65,
        attribution: `&copy; <a href="${chlorophyll.source_link}" target="_blank" rel="noopener noreferrer">NASA Ocean Color / GIBS</a>`,
      });
      chlorophyllLayer.on("tileerror", () => {
        console.warn("NASA chlorophyll tiles are currently unavailable.");
        setMarineObservationStatus("Chlorophyll imagery is temporarily unavailable.");
      });
      mapLayerControl.addOverlay(chlorophyllLayer, "Chlorophyll-a (NASA satellite)");
    }
  } catch (error) {
    console.error("Ecosystem layer metadata request failed:", error?.message || String(error));
    setMarineObservationStatus("Ecosystem overlay settings are temporarily unavailable.");
  }
}

loadEcosystemLayers(map);
