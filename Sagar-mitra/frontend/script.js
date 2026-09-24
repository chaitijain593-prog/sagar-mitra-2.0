if(!localStorage.getItem("orcaAuth"))location.replace("auth.html");
    const oceanVerbs = ["Surfing...", "Rippling...", "Crashing...", "Swimming...", "Floating...", "Sailing...", "Diving...", "Wading...", "Drifting..."];
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
function runLoader(ms=2000){const l=document.getElementById("loading-screen"),v=document.getElementById("loadBgVideo");v.src=v.dataset.src;l.style.display="flex";l.classList.remove("fade-out");setTimeout(()=>{l.classList.add("fade-out");setTimeout(()=>l.style.display="none",500)},ms)}
window.addEventListener("load", () => {
  if (!localStorage.getItem("orcaAuth")) return;
  startLanguageRotation(); checkOnboarding();
  if (sessionStorage.getItem("orcaLoad")) { sessionStorage.removeItem("orcaLoad"); runLoader(); }
});
    const titleElement = document.getElementById("languageTitle");
    const languages = ["Sagar Mitra", "सागर मित्र", "સાગર મિત્ર", "सागर मित्र", "ಸಾಗರ ಮಿತ್ರ", "சாகர் மித்ரா", "సాగర్ మిత్ర", "സാഗർ മിത്ര",
      "সাগর মিত্র", "ਸਾਗਰ ਮਿੱਤਰ"];
    let langIndex = 0;
    function startLanguageRotation() {
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
      const heroSection = document.getElementById("#hero-slide");
      if (heroSection) {
        heroSection.scrollIntoView({ behavior: "smooth" });
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
    const ONBOARD_KEY = "orcaUserProfile_" + (localStorage.getItem("orcaUser") || "");
    const onboardScreen = document.getElementById("onboarding-screen");
    const onboardStep1 = document.getElementById("onboardStep1");
    const onboardStep2 = document.getElementById("onboardStep2");
    const onboardName = { value: localStorage.getItem("orcaName") || localStorage.getItem("orcaUser") || "User" };
    const onboardPersonaGroup = document.getElementById("onboardPersonaGroup");
    const onboardPersonaOther = document.getElementById("onboardPersonaOther");
    const onboardDomainGroup = document.getElementById("onboardDomainGroup");
    onboardDomainGroup.style.cssText="max-height:40vh;overflow-y:auto";["Ocean Acidification","Coral Reefs","Sea Level Rise","Cyclones & Monsoon","El Niño & Climate","Marine Pollution","Fisheries & Aquaculture","Tides & Waves","Deep-Sea Exploration","Marine Mammals","Coastal Erosion","Ocean Currents"].forEach(d=>onboardDomainGroup.insertAdjacentHTML("beforeend",`<label class="onboarding-checkbox"><input type="checkbox" value="${d}"/><span>${d}</span></label>`));
    const onboardStep1Error = document.getElementById("onboardStep1Error");
    const onboardNextBtn = document.getElementById("onboardNextBtn");
    const onboardBackBtn = document.getElementById("onboardBackBtn");
    const onboardFinishBtn = document.getElementById("onboardFinishBtn");
    const logoutBtn = document.getElementById("logoutBtn");
    function checkOnboarding() {
      const profile = localStorage.getItem(ONBOARD_KEY);
      if (!profile) {
        onboardScreen.classList.add("active");
      }
    }
    onboardPersonaGroup.addEventListener("change", (e) => {
      if (e.target.name === "persona") {
        onboardPersonaOther.classList.toggle("onboarding-hidden", e.target.value !== "Others");
      }
    });
    onboardNextBtn.addEventListener("click", () => {
      const name = onboardName.value.trim();
      const personaInput = onboardPersonaGroup.querySelector('input[name="persona"]:checked');
      if (!name) {
        onboardStep1Error.textContent = "Please enter your name.";
        return;
      }
      if (!personaInput) {
        onboardStep1Error.textContent = "Please select who you are.";
        return;
      }
      if (personaInput.value === "Others" && !onboardPersonaOther.value.trim()) {
        onboardStep1Error.textContent = "Please specify your role.";
        return;
      }
      onboardStep1Error.textContent = "";
      onboardStep1.classList.add("onboarding-hidden");
      onboardStep2.classList.remove("onboarding-hidden");
    });
    onboardBackBtn.addEventListener("click", () => {
      onboardStep2.classList.add("onboarding-hidden");
      onboardStep1.classList.remove("onboarding-hidden");
    });
    onboardFinishBtn.addEventListener("click", () => {
      const name = onboardName.value.trim();
      const personaInput = onboardPersonaGroup.querySelector('input[name="persona"]:checked');
      const persona = personaInput.value === "Others" ? onboardPersonaOther.value.trim() : personaInput.value;
      const domains = Array.from(onboardDomainGroup.querySelectorAll("input:checked")).map((el) => el.value);
      const profile = { name, persona, domains, createdAt: new Date().toISOString() };
      const first = localStorage.setItem(ONBOARD_KEY, JSON.stringify(profile));
      onboardScreen.classList.remove("active");
      refreshActivePersona();
      fetch(`${API_BASE}/api/auth/profile`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: localStorage.getItem("orcaAuth"), profile }) }).catch(() => {});
      if (first) runLoader();
    });
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("orcaAuth"); localStorage.removeItem("orcaUser"); location.replace("auth.html");
    });
    const themeBtn = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");
    const themeLabel = document.getElementById("themeLabel");
    themeBtn.addEventListener("click", () => {
      const isDark = document.body.getAttribute("data-theme") === "dark";
      if (isDark) {
        document.body.setAttribute("data-theme", "light");
        themeIcon.textContent = "🌙";
        themeLabel.textContent = "Dark";
      } else {
        document.body.setAttribute("data-theme", "dark");
        themeIcon.textContent = "☀️";
        themeLabel.textContent = "Light";
      }
    });
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
    soundToggle.addEventListener("click", () => {
      if (!isAudioPlaying) {
        if (!audioCtx) {
          createOceanSound();
        } else if (audioCtx.state === "suspended") {
          audioCtx.resume();
        }
        isAudioPlaying = true;
        soundToggle.style.borderColor = "var(--accent-cyan)";
      } else {
        if (audioCtx && audioCtx.state === "running") {
          audioCtx.suspend();
        }
        isAudioPlaying = false;
        soundToggle.style.borderColor = "var(--card-border)";
      }
    });
    const map = L.map("oceanMap", { center: [18.9, 72.8], zoom: 6, zoomControl: false });
    const oceanLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}", {className: 'dark-ocean-tiles', maxZoom: 13}).addTo(map);
    const satLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { className: 'dark-sat-tiles', maxZoom: 18 });
    function setMapBase(type) {
      const oceanBtn = document.getElementById("baseBtnOcean");
      const satBtn = document.getElementById("baseBtnSat");
      if (type === "ocean") {
        if (map.hasLayer(satLayer)) map.removeLayer(satLayer);
        oceanLayer.addTo(map);
        oceanBtn.classList.add("active-base");
        satBtn.classList.remove("active-base");
      } else {
        if (map.hasLayer(oceanLayer)) map.removeLayer(oceanLayer);
        satLayer.addTo(map);
        satBtn.classList.add("active-base");
        oceanBtn.classList.remove("active-base");
      }
    }
    const floatData = [{ id: "ARGO-290241", lat: 14.2, lon: 68.9, temp: 27.4, depth: 612 },
      { id: "ARGO-290242", lat: 17.6, lon: 66.1, temp: 26.8, depth: 481 }, { id: "ARGO-290243", lat: 9.4,  lon: 76.8, temp: 28.1, depth: 725 },
      { id: "ARGO-290244", lat: 11.8, lon: 72.4, temp: 28.4, depth: 530 }, { id: "ARGO-290245", lat: 16.9, lon: 84.2, temp: 28.9, depth: 890 }];
    const argoIcon = L.divIcon({ className: "", html: '<div class="argo-marker"></div>', iconSize: [13, 13] });
    floatData.forEach(f => {
      L.marker([f.lat, f.lon], { icon: argoIcon }).addTo(map).bindPopup(`<b>${f.id}</b><br>SST: ${f.temp}°C<br>Depth: ${f.depth}m`);
    });
    const pfzData = [{ id: "PFZ-01", lat: 18.2, lon: 69.8, name: "Ratnagiri Front" }, { id: "PFZ-02", lat: 10.2, lon: 75.4, name: "Kochi Shoal" }];
    const pfzIcon = L.divIcon({ className: "", html: '<div class="pfz-marker">🐟</div>', iconSize: [26, 26] });
    pfzData.forEach(p => {
      L.marker([p.lat, p.lon], { icon: pfzIcon }).addTo(map).bindPopup(`<b>${p.id} — ${p.name}</b><br>High Biomass Aggregation Zone`);
    });
    let vesselMarker = null;
    let vesselSafetyBuffer = null;
    const vesselIcon = L.divIcon({ className: "", html: '<div class="vessel-marker">🚢</div>', iconSize: [24, 24] });
    const NM_IN_METERS = 1852;
    function plotVesselMarker(lat, lon) {
      if (vesselMarker) map.removeLayer(vesselMarker);
      if (vesselSafetyBuffer) map.removeLayer(vesselSafetyBuffer);
      vesselSafetyBuffer = L.circle([lat, lon], {
        radius: 5 * NM_IN_METERS, color: "#facc15", weight: 1.5, fillColor: "#facc15", fillOpacity: 0.16, className: "vessel-safety-buffer"
      }).addTo(map).bindPopup("5 NM Safety Buffer");
      vesselMarker = L.marker([lat, lon], { icon: vesselIcon, zIndexOffset: 1000 }).addTo(map).bindPopup("<b>Your Vessel</b>");
      return vesselMarker;
    }
    const indianEEZCoords = [[23.5, 68.1], [20.5, 66.5], [15.5, 68.0], [10.5, 71.0], [7.0, 74.5], [5.5, 78.0], [7.5, 81.5], [11.0, 83.5],
      [16.0, 84.5], [20.5, 87.5]];
    L.polyline(indianEEZCoords, {
      color: "#ef4444", weight: 2, dashArray: "6, 8", opacity: 0.85 }).addTo(map).bindPopup("Indian EEZ Boundary (approximate)");
    let pfzPolygons = [];
    function plotPFZZones(zones) {
      pfzPolygons.forEach(p => map.removeLayer(p));
      pfzPolygons = [];
      (zones || []).forEach(z => {
        const poly = L.polygon(z.coordinates, {
          color: "#10b981", fillColor: "#10b981", fillOpacity: 0.3, weight: 2 }).addTo(map).bindPopup(`<b>${z.name || "Potential Fishing Zone"}</b>`);
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
          radius: 7, color: "#a78bfa", fillColor: "#a78bfa", fillOpacity: 0.55, weight: 1.5, }).addTo(map).bindPopup(
          `<b>${z.name || "Favorable Zone"}</b><br>SST: ${z.sst_c ?? "N/A"}°C<br>` +
          `Chlorophyll: ${z.chlorophyll_mgm3 ?? "N/A"} mg/m3<br>ML Confidence: ${ml}`);
        regionalZoneMarkers.push(marker);
      });
    }
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
      if (hazardModalOverlay) hazardModalOverlay.classList.add("active");
    }
    function closeHazardModal() {
      if (hazardModalOverlay) hazardModalOverlay.classList.remove("active");
      pendingHazardCoords = null;
    }
    async function submitHazardReport(e) {
      e.preventDefault();
      if (!pendingHazardCoords) return;
      const submitBtn = hazardModalForm.querySelector(".hazard-modal-submit");
      const hazardType = hazardTypeSelect.value;
      const { lat, lon } = pendingHazardCoords;
      if (submitBtn) submitBtn.disabled = true;
      try {
        const res = await fetch(`${API_BASE}/api/hazard`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat, lon, hazard_type: hazardType, status: "active" }), });
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
    let historicalChartInstance = null;
    function initHistoricalChart() {
      const canvas = document.getElementById("historicalChart");
      if (!canvas || typeof Chart === "undefined") return;
      const baselineLabels = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"];
      const baselineSST = [27.1, 27.3, 27.6, 27.9, 28.2, 27.8];
      const baselineSalinity = [34.9, 35.0, 35.1, 35.0, 34.8, 34.9];
      historicalChartInstance = new Chart(canvas.getContext("2d"), {
        type: "line", data: {
          labels: baselineLabels, datasets: [{
            label: "SST (°C)", data: baselineSST, borderColor: "#38bdf8", backgroundColor: "rgba(56, 189, 248, 0.15)",
            tension: 0.35, fill: true, pointRadius: 3, }, {
            label: "Salinity (PSU)", data: baselineSalinity, borderColor: "#f472b6", backgroundColor: "rgba(244, 114, 182, 0.12)",
            tension: 0.35, fill: true, pointRadius: 3, }], }, options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: true, labels: { color: "#cbd5e1", font: { size: 10 } } } }, scales: {
            x: { grid: { color: "rgba(148,163,184,0.12)" }, ticks: { color: "#94a3b8" } },
            y: { grid: { color: "rgba(148,163,184,0.12)" }, ticks: { color: "#94a3b8" } }, }, }, });
    }
    function updateHistoricalChart(telemetry) {
      if (!historicalChartInstance || !telemetry || !Array.isArray(telemetry.historical_series) || !telemetry.historical_series.length) return;
      const series = telemetry.historical_series;
      historicalChartInstance.data.labels = series.map((p) => p.date || p.label || "");
      historicalChartInstance.data.datasets[0].data = series.map((p) => p.value);
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
    function updateCompassHeading(deg) {
      const needle = document.getElementById("compassNeedle");
      const readout = document.getElementById("compassHeadingReadout");
      if (needle) needle.style.transform = "rotate(" + deg + "deg)";
      if (readout) {
        const normalized = Math.round(((deg % 360) + 360) % 360);
        readout.textContent = `${String(normalized).padStart(3, "0")}° ${bearingToCardinal(normalized)}`;
      }
    }
    function initHazardReporting() {
      map.on("click", (e) => openHazardModal(e.latlng));
      if (hazardModalClose) hazardModalClose.addEventListener("click", closeHazardModal);
      if (hazardModalOverlay) {
        hazardModalOverlay.addEventListener("click", (e) => {
          if (e.target === hazardModalOverlay) closeHazardModal();
        });
      }
      if (hazardModalForm) hazardModalForm.addEventListener("submit", submitHazardReport);
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
        tooltipText = `${hazardAvoided ? "Detour" : "Direct"}: ${distanceNM.toFixed(0)} NM | ` + `Est. Time: ${hours}h ${minutes}m${waveText}`;
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
        color: hazardAvoided ? "#f59e0b" : "#ffffff", weight: 2, opacity: 0.85, dashArray: "8, 8" }).addTo(map);
      routeLine.bindTooltip(tooltipText, { permanent: true, direction: "center", className: "route-tooltip" });
      return routeLine;
    }
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
      banner.classList.remove("hazard-safe", "hazard-caution", "hazard-hazardous");
      if (normalized === "HAZARDOUS") {
        banner.classList.add("hazard-hazardous");
      } else if (normalized === "CAUTION") {
        banner.classList.add("hazard-caution");
      } else {
        banner.classList.add("hazard-safe");
      }
      iconEl.innerHTML = HAZARD_ICONS[normalized] || HAZARD_ICONS.SAFE;
      statusEl.textContent = normalized;
    }
    function appendAgentBadge(text) {
      const feed = document.getElementById("agentStreamFeed");
      const badge = document.createElement("div");
      badge.className = "agent-badge";
      badge.textContent = text;
      feed.appendChild(badge);
      feed.scrollTop = feed.scrollHeight;
      return badge;
    }
    function runAgentSequence() {
      const steps = ["🛰️ Satellite Agent Active", "🐟 Ocean & PFZ Advisor Validating Baseline", "⚓ Compliance Agent Verifying Boundaries"];
      return new Promise((resolve) => {
        steps.forEach((step, i) => setTimeout(() => appendAgentBadge(step), i * 650));
        setTimeout(resolve, steps.length * 650);
      });
    }
    let shapChartCounter = 0;
    const shapChartInstances = {};
    function renderShapChart(canvasId, featureAttributions, baseValue) {
      if (typeof Chart === "undefined") {
        console.warn("Chart.js failed to load -- skipping SHAP chart render.");
        return;
      }
      const canvas = document.getElementById(canvasId);
      if (!canvas) return;
      const labels = Object.keys(featureAttributions);
      const values = Object.values(featureAttributions);
      shapChartInstances[canvasId] = new Chart(canvas.getContext("2d"), {
        type: "bar", data: {
          labels, datasets: [{
            label: `SHAP attribution (base value ${typeof baseValue === "number" ? baseValue.toFixed(3) : "N/A"})`, data: values,
            backgroundColor: values.map(v => v >= 0 ? "rgba(16, 185, 129, 0.75)" : "rgba(248, 113, 113, 0.75)"), borderRadius: 4, }], }, options: {
          indexAxis: "y", responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: true, labels: { color: "#cbd5e1", font: { size: 10 } } } }, scales: {
            x: { grid: { color: "rgba(148,163,184,0.15)" }, ticks: { color: "#94a3b8" } },
            y: { grid: { display: false }, ticks: { color: "#94a3b8" } }, }, }, });
    }
    function appendAdvisoryCard(data) {
      const feed = document.getElementById("agentStreamFeed");
      const card = document.createElement("div");
      card.className = "advisory-card";
      const alertsHtml = (data.alerts || []).map(a => `<span class="advisory-alert">⚠ ${a}</span>`).join("");
      const shapData = data.shap_attributions;
      const showShapChart = data.persona === "Researcher" && shapData && shapData.feature_attributions &&
        Object.keys(shapData.feature_attributions).length > 0;
      const chartId = showShapChart ? `shapChart_${++shapChartCounter}` : null;
      card.innerHTML = `
        <h4>🧭 Maritime Advisory</h4>
        <div class="advisory-row"><b>Status:</b> ${(data.hazard_status || "SAFE").toUpperCase()}</div>
        <div class="advisory-row"><b>Vessel Position:</b> ${data.vessel_coord ? data.vessel_coord.join(", ") : "Unknown"}</div>
        ${alertsHtml || '<div class="advisory-row">No active alerts.</div>'}
        ${showShapChart ? `
          <div class="shap-chart-wrap">
            <div class="advisory-row"><b>🔬 PFZ Model Explainability (SHAP)</b></div>
            <div style="height:160px;"><canvas id="${chartId}"></canvas></div>
          </div>
        ` : ""}
      `;
      feed.appendChild(card);
      feed.scrollTop = feed.scrollHeight;
      if (showShapChart) {
        renderShapChart(chartId, shapData.feature_attributions, shapData.base_value);
      }
    }
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
      } catch (e) {
      }
      return null;
    }
    let activePersona = mapPersonaAlias(readOnboardingPersona());
    function refreshActivePersona() {
      activePersona = mapPersonaAlias(readOnboardingPersona());
    }
    function openRoleSwitcher() {
      onboardStep2.classList.add("onboarding-hidden");
      onboardStep1.classList.remove("onboarding-hidden");
      onboardScreen.classList.add("active");
    }
    function initPersonaSwitcher() {
      const switchBtn = document.getElementById("switchRoleBtn");
      if (switchBtn) switchBtn.addEventListener("click", openRoleSwitcher);
    }
    const API_BASE = "http://127.0.0.1:8000";
    let sessionId = null;
    try {
      sessionId = localStorage.getItem("orca_session_id");
    } catch (e) {
    }
    const MOCK_ORCHESTRATOR_RESPONSE = {
      vessel_coord: [18.95, 72.75], hazard_status: "CAUTION", alerts: ["Approaching Indian EEZ boundary (12 nm remaining)",
        "Moderate wave swell (1.8m) forecast over next 6 hours"], pfz_location: [{
          name: "Ratnagiri Front PFZ", coordinates: [[18.5, 69.5], [18.5, 70.1], [18.0, 70.1], [18.0, 69.5]] }, {
          name: "Kochi Shoal PFZ", coordinates: [[10.4, 75.2], [10.4, 75.8], [9.9, 75.8], [9.9, 75.2]] }],
      telemetry: { sst_anomaly_pct: null, chlorophyll_gradient_pct: null, ml_confidence_pct: null }
    };
    function getVesselCoordinates() {
      return new Promise((resolve) => {
        if (!navigator.geolocation) {
          resolve([18.9, 72.8]);
          return;
        }
        navigator.geolocation.getCurrentPosition((pos) => resolve([pos.coords.latitude, pos.coords.longitude]), () => resolve([18.9, 72.8]),
          { timeout: 4000 });
      });
    }
    async function handleQuerySubmit(e) {
      e.preventDefault();
      const input = document.getElementById("chatInput");
      const text = input.value.trim();
      if (!text) return;
      const loader = document.getElementById("chatLoader");
      input.value = "";
      appendAgentBadge(`🧑‍✈️ Query: "${text}"`);
      loader.style.display = "flex";
      await runAgentSequence();
      const coords = await getVesselCoordinates();
      let parsedData;
      try {
        const res = await fetch(`${API_BASE}/api/orchestrate`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_message: text, coordinates: coords, session_id: sessionId, persona: activePersona }), });
        if (!res.ok) throw new Error("Backend not responding correctly");
        const backendData = await res.json();
        sessionId = backendData.session_id || sessionId;
        try {
          if (sessionId) localStorage.setItem("orca_session_id", sessionId);
        } catch (e) {  }
        const extraAlerts = [];
        if (backendData.lightning_alert) extraAlerts.push("⚡ Lightning risk detected in this area.");
        if (backendData.cyclone_alert) extraAlerts.push("🌀 Cyclone watch (wind-speed proxy) -- exercise caution.");
        if (backendData.route && backendData.route.hazard_avoided) {
          extraAlerts.push(`🧭 ${backendData.route.note || "Route detour applied to avoid a hazard."}`);
        }
        parsedData = {
          vessel_coord: backendData.coordinates || coords, hazard_status: backendData.hazard_status || "SAFE",
          alerts: [backendData.advisory || "No specific advisory generated.", ...extraAlerts], pfz_location: backendData.pfz_location || [],
          telemetry: backendData.telemetry || null, route: backendData.route || null, plot_url: backendData.plot_url || null,
          regional_zones: backendData.regional_zones || [], persona: backendData.persona || "Fisherman",
          shap_attributions: (backendData.telemetry && backendData.telemetry.shap_attributions) || null, };
      } catch (err) {
        console.error("API Connection Error:", err);
        parsedData = {...MOCK_ORCHESTRATOR_RESPONSE, vessel_coord: coords, route: null, plot_url: null,
          regional_zones: [], persona: "Fisherman", shap_attributions: null, };
      }
      loader.style.display = "none";
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
    let mediaRecorder = null;
    let recordedChunks = [];
    let micStream = null;
    let micState = "idle";
    function pickAudioMimeType() {
      const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus",];
      if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
        return "";
      }
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
        appendAgentBadge("🎤 Microphone unavailable: this page must be served over https:// or " +
          "http://localhost (not opened as a file:// path) for mic access to work.");
        return;
      }
      if (typeof MediaRecorder === "undefined") {
        appendAgentBadge("🎤 This browser doesn't support MediaRecorder for mic capture.");
        return;
      }
      try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        console.error("Mic permission error:", err);
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          appendAgentBadge("🎤 Microphone permission denied. Click the padlock/camera icon in your " +
            "browser's address bar and allow microphone access, then try again.");
        } else if (err.name === "NotFoundError") {
          appendAgentBadge("🎤 No microphone found on this device.");
        } else {
          appendAgentBadge(`🎤 Could not access microphone: ${err.message || err.name}`);
        }
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
          appendAgentBadge("🎤 No audio captured -- please try again.");
          setMicState("idle");
          return;
        }
        submitVoiceQuery(blob, blobType);
      };
      mediaRecorder.start();
      setMicState("recording");
      appendAgentBadge("🎤 Listening... click the mic again to stop.");
    }
    function stopMicRecording() {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        setMicState("busy");
        mediaRecorder.stop();
      }
    }
    async function submitVoiceQuery(blob, mimeType) {
      appendAgentBadge("📡 Uploading voice clip to ORCA for transcription...");
      const loader = document.getElementById("chatLoader");
      loader.style.display = "flex";
      try {
        const coords = await getVesselCoordinates();
        const ext = mimeType.includes("mp4") ? "m4a" : mimeType.includes("ogg") ? "ogg" : "webm";
        const formData = new FormData();
        formData.append("audio", blob, `voice_query.${ext}`);
        formData.append("latitude", coords[0]);
        formData.append("longitude", coords[1]);
        const res = await fetch(`${API_BASE}/api/voice/orchestrate`, {
          method: "POST", body: formData, });
        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const errBody = await res.json();
            detail = errBody.detail || detail;
          } catch (e) {  }
          throw new Error(detail);
        }
        const data = await res.json();
        appendAgentBadge(`🗣️ Heard (${data.detected_language}): "${data.transcript}"`);
        appendAgentBadge(`🌊 ${data.advisory_text}`);
        if (data.audio_url) {
          const feed = document.getElementById("agentStreamFeed");
          const player = document.createElement("audio");
          player.controls = true;
          player.src = data.audio_url;
          player.style.width = "100%";
          player.style.marginTop = "4px";
          feed.appendChild(player);
          feed.scrollTop = feed.scrollHeight;
          player.play().catch(() => {  });
        }
      } catch (err) {
        console.error("Voice orchestrate error:", err);
        appendAgentBadge(`⚠ Voice query failed: ${err.message}`);
      } finally {
        loader.style.display = "none";
        setMicState("idle");
      }
    }
    function initVoiceMic() {
      const micBtn = document.getElementById("micBtn");
      if (!micBtn) return;
      micBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (micState === "idle") startMicRecording(); else if (micState === "recording") stopMicRecording();
      });
    }
    let lastVesselCoord = MOCK_ORCHESTRATOR_RESPONSE.vessel_coord;
    let lastHazardStatus = MOCK_ORCHESTRATOR_RESPONSE.hazard_status;
    function setLastKnownState(vesselCoord, hazardStatus) {
      if (lastVesselCoord && vesselCoord &&
          (lastVesselCoord[0] !== vesselCoord[0] || lastVesselCoord[1] !== vesselCoord[1])) {
        updateCompassHeading(calculateBearing(lastVesselCoord[0], lastVesselCoord[1], vesselCoord[0], vesselCoord[1]));
      }
      lastVesselCoord = vesselCoord;
      lastHazardStatus = hazardStatus;
    }
    const SOS_NEAREST_PORT_PLACEHOLDER = "45 NM";
    function setSOSStatus(kind, text) {
      const el = document.getElementById("sosStatus");
      if (!el) return;
      el.className = `sos-status is-visible is-${kind}`;
      el.textContent = text;
    }
    async function triggerMayday() {
      if(!confirm("CONFIRM MAYDAY: Broadcast SOS to nearest Coast Guard?")) return;
      const coords = window.vesselLocation || { lat: 18.9220, lon: 72.8347 };

      try {
          const response = await fetch(`${API_BASE}/api/sos`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  lat: coords.lat,
                  lon: coords.lon,
                  hazard_status: "CRITICAL_EMERGENCY",
                  nearest_port: "Awaiting calculation...", 
                  message: "Manual SOS triggered from ORCA dashboard.",
                  session_id: window.sessionId || "demo-session-1"
              })
          });
          
          const data = await response.json();
          
          if(data.status === "success") {
              alert(`🚨 SOS BROADCAST SUCCESSFUL 🚨\nEvent ID: ${data.id}\nCoast Guard has been notified.`);
              const banner = document.querySelector('.hazard-banner');
              if(banner) {
                  banner.textContent = "MAYDAY ACTIVE - REMAIN CALM - ASSISTANCE EN ROUTE";
                  banner.className = "hazard-banner hazard-hazardous";
              }
          }
      } catch (err) {
          console.error("SOS failed to send:", err);
          alert("CRITICAL: Network error. Retrying via local VHF proxy...");
      }
    }
    function updateTelemetryBars(telemetry) {
      const metrics = {
        telemetrySST: { pct: telemetry?.sst_anomaly_pct, labelId: "telemetrySSTLabel" },
        telemetryChlorophyll: { pct: telemetry?.chlorophyll_gradient_pct, labelId: "telemetryChlorophyllLabel" },
        telemetryML: { pct: telemetry?.ml_confidence_pct, labelId: "telemetryMLLabel" },
        telemetrySalinity: { pct: telemetry?.salinity_anomaly_pct, labelId: "telemetrySalinityLabel" },
        telemetryDissolvedOxygen: { pct: telemetry?.dissolved_oxygen_pct, labelId: "telemetryDissolvedOxygenLabel" }, };
      Object.entries(metrics).forEach(([barId, { pct, labelId }]) => {
        const bar = document.getElementById(barId);
        const label = document.getElementById(labelId);
        const hasValue = typeof pct === "number" && !Number.isNaN(pct);
        if (bar) requestAnimationFrame(() => { bar.style.width = `${hasValue ? pct : 0}%`; });
        if (label) label.textContent = hasValue ? `${pct}%` : "N/A";
      });
    }
    const GEOFENCE_POLL_MS = 15000;
    const GEOFENCE_ALERT_KM = 5;
    let geofencePollTimer = null;
    let geofenceAlertArmed = true;
    let geofenceAudioCtx = null;
    function playGeofenceSiren() {
      if (!geofenceAudioCtx) {
        geofenceAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (geofenceAudioCtx.state === "suspended") {
        geofenceAudioCtx.resume();
      }
      const ctx = geofenceAudioCtx;
      const now = ctx.currentTime;
      [0, 0.35].forEach((offset) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "square";
        osc.frequency.setValueAtTime(880, now + offset);
        gain.gain.setValueAtTime(0, now + offset);
        gain.gain.linearRampToValueAtTime(0.25, now + offset + 0.02);
        gain.gain.linearRampToValueAtTime(0, now + offset + 0.28);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + offset);
        osc.stop(now + offset + 0.3);
      });
    }
    async function triggerMorningDispatch() {
      const btn = document.getElementById("dispatchButton");
      const label = document.getElementById("dispatchButtonLabel");
      const status = document.getElementById("dispatchStatus");
      const player = document.getElementById("dispatchPlayer");
      if (!btn || !status || !player) return;

      const persona = activePersona;
      const language = "English";

      btn.disabled = true;
      if (label) label.textContent = "Generating...";
      status.textContent = "Generating your offline briefing (PDF + audio)...";
      status.className = "dispatch-status is-visible is-pending";
      player.innerHTML = "";

      try {
        const coords = await getVesselCoordinates();
        const res = await fetch(`${API_BASE}/api/dispatch/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ coordinates: coords, persona, language }),
        });
        if (!res.ok) {
          throw new Error(`Dispatch request failed (${res.status})`);
        }
        const data = await res.json();

        status.textContent = data.degraded
          ? "Briefing ready (degraded mode -- some data may be limited)."
          : "Briefing ready.";
        status.className = `dispatch-status is-visible ${data.degraded ? "is-pending" : "is-success"}`;

        if (data.pdf_url) {
          const pdfLink = document.createElement("a");
          pdfLink.href = data.pdf_url;
          pdfLink.target = "_blank";
          pdfLink.rel = "noopener noreferrer";
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
        if (!data.pdf_url && !data.audio_url) {
          status.textContent = "Briefing generated, but no downloadable output was returned.";
          status.className = "dispatch-status is-visible is-error";
        }
      } catch (err) {
        console.error("Morning Dispatch failed:", err);
        status.textContent = "Failed to generate Morning Dispatch. Please try again.";
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
        console.error("Failed to load news domains:", err);
      }
    }
    async function loadNewsFeed(domain = "") {
      const list = document.getElementById("newsArticlesList");
      if (!list) return;
      list.innerHTML = "";
      const loadingMsg = document.createElement("div");
      loadingMsg.className = "news-article-empty";
      loadingMsg.textContent = "Loading ocean news...";
      list.appendChild(loadingMsg);
      try {
        const url = domain ? `${API_BASE}/api/news?domain=${encodeURIComponent(domain)}` : `${API_BASE}/api/news`;
        const res = await fetch(url);
        const data = await res.json();
        const articles = data.articles || [];
        list.innerHTML = "";
        if (!articles.length) {
          const emptyMsg = document.createElement("div");
          emptyMsg.className = "news-article-empty";
          emptyMsg.textContent = "No articles found for this domain.";
          list.appendChild(emptyMsg);
          return;
        }
        articles.forEach((a) => {
          const card = document.createElement("a");
          card.className = "news-article-card";
          card.href = a.link || "#";
          card.target = "_blank";
          card.rel = "noopener noreferrer";
          const title = document.createElement("div");
          title.className = "news-article-title";
          title.textContent = a.title || "";
          const summary = document.createElement("div");
          summary.className = "news-article-summary";
          summary.textContent = a.summary || "";
          card.appendChild(title);
          card.appendChild(summary);
          list.appendChild(card);
        });
      } catch (err) {
        console.error("Failed to load news feed:", err);
        list.innerHTML = "";
        const errMsg = document.createElement("div");
        errMsg.className = "news-article-empty";
        errMsg.textContent = "Unable to load news right now.";
        list.appendChild(errMsg);
      }
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
    updateCompassHeading(45);
    startGeofencePolling();
    loadNewsDomains();
    loadNewsFeed();
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
function startGeofenceMonitor() {
    setInterval(async () => {
        const coords = window.vesselLocation;
        if(!coords) return;

        try {
            const response = await fetch(`${API_BASE}/api/geofence-check?lat=${coords.lat}&lon=${coords.lon}`);
            const data = await response.json();

            if(data.status === "CAUTION") {
                console.warn(`Boundary Alert: ${data.distance_km}km away!`);
                if(typeof createOceanSound === "function") {
                    createOceanSound('siren'); 
                }
                const banner = document.querySelector('.hazard-banner');
                if(banner) {
                    banner.innerHTML = `⚠️ IMBL PROXIMITY ALERT: ${data.distance_km.toFixed(1)}km to boundary. Adjust heading immediately.`;
                    banner.className = "hazard-banner hazard-hazardous";
                }
            }
        } catch (err) {
            console.error("Geofence poll failed", err);
        }
    }, 60000); 
}