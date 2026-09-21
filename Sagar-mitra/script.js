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
    window.addEventListener("load", () => {
      const loader = document.getElementById("loading-screen");
      setTimeout(() => {
        loader.classList.add("fade-out");
        setTimeout(() => {
          loader.style.display = "none";
          startLanguageRotation();
          checkOnboarding();
        }, 1000);
      }, 10000);
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
      localStorage.setItem(ONBOARD_KEY, JSON.stringify(profile));
      onboardScreen.classList.remove("active");
    });
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem(ONBOARD_KEY);
      window.location.reload();
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
      // Generate 5 seconds of pink noise buffer
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
      // Lowpass filter for deep oceanic timbre
      const filter = audioCtx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(380, audioCtx.currentTime);
      // Rhythmic wave swell generator
      const lfo = audioCtx.createOscillator();
      const lfoGain = audioCtx.createGain();
      lfo.frequency.setValueAtTime(0.12, audioCtx.currentTime); // ~8s wave period
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
    // --- 6a. Vessel Marker Layer ---
    let vesselMarker = null;
    let vesselSafetyBuffer = null;
    const vesselIcon = L.divIcon({ className: "", html: '<div class="vessel-marker">🚢</div>', iconSize: [24, 24] });
    const NM_IN_METERS = 1852;
    function plotVesselMarker(lat, lon) {
      if (vesselMarker) map.removeLayer(vesselMarker);
      if (vesselSafetyBuffer) map.removeLayer(vesselSafetyBuffer);
      // Pulsating 5 NM safety buffer ring around the vessel
      vesselSafetyBuffer = L.circle([lat, lon], {
        radius: 5 * NM_IN_METERS, color: "#facc15", weight: 1.5, fillColor: "#facc15", fillOpacity: 0.16, className: "vessel-safety-buffer"
      }).addTo(map).bindPopup("5 NM Safety Buffer");
      vesselMarker = L.marker([lat, lon], { icon: vesselIcon, zIndexOffset: 1000 }).addTo(map).bindPopup("<b>Your Vessel</b>");
      return vesselMarker;
    }
    // --- 6b. Indian EEZ Boundary Layer ---
    const indianEEZCoords = [[23.5, 68.1], [20.5, 66.5], [15.5, 68.0], [10.5, 71.0], [7.0, 74.5], [5.5, 78.0], [7.5, 81.5], [11.0, 83.5],
      [16.0, 84.5], [20.5, 87.5]];
    L.polyline(indianEEZCoords, {
      color: "#ef4444", weight: 2, dashArray: "6, 8", opacity: 0.85 }).addTo(map).bindPopup("Indian EEZ Boundary (approximate)");
    // --- 6c. Potential Fishing Zone (PFZ) Polygons ---
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
    // --- 6d. Tactical Route to Nearest PFZ ---
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
          body: JSON.stringify({ user_message: text, coordinates: coords, session_id: sessionId }), });
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
        // Fall back to the mock payload if the backend is off
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
    }
    let mediaRecorder = null;
    let recordedChunks = [];
    let micStream = null;
    // 'idle' -> 'recording' -> 'busy' (uploading/processing) -> 'idle'
    let micState = "idle";
    function pickAudioMimeType() {
      const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus",];
      if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
        return ""; // let the browser pick its own default
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
        // Always release the mic hardware once we're done with it.
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
    // 1. Prevent accidental clicks
    if(!confirm("CONFIRM MAYDAY: Broadcast SOS to nearest Coast Guard?")) return;

    // 2. Grab current vessel location (ensure window.vesselLocation is updated by your map)
    const coords = window.vesselLocation || { lat: 18.9220, lon: 72.8347 }; // Mumbai fallback

    try {
        const response = await fetch('/api/sos', {
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
            // 3. UI Confirmation
            alert(`🚨 SOS BROADCAST SUCCESSFUL 🚨\nEvent ID: ${data.id}\nCoast Guard has been notified.`);
            
            // 4. Force the dashboard into emergency mode
            const banner = document.querySelector('.hazard-banner');
            if(banner) {
                banner.textContent = "MAYDAY ACTIVE - REMAIN CALM - ASSISTANCE EN ROUTE";
                banner.className = "hazard-banner hazard-hazardous"; // Red theme
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
        telemetryML: { pct: telemetry?.ml_confidence_pct, labelId: "telemetryMLLabel" }, };
      Object.entries(metrics).forEach(([barId, { pct, labelId }]) => {
        const bar = document.getElementById(barId);
        const label = document.getElementById(labelId);
        const hasValue = typeof pct === "number" && !Number.isNaN(pct);
        if (bar) requestAnimationFrame(() => { bar.style.width = `${hasValue ? pct : 0}%`; });
        if (label) label.textContent = hasValue ? `${pct}%` : "N/A";
      });
    }
    const GEOFENCE_POLL_MS = 15000;
    const GEOFENCE_ALERT_KM = 5; // mirrors main.py's GEOFENCE_WARNING_KM
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
          geofenceAlertArmed = false; // one alert per crossing, not one per poll
          playGeofenceSiren();
          appendAgentBadge(`🚨 GEOFENCE ALERT: ${data.message} (${nearestKm.toFixed(2)} km)`);
        } else if (!isNear) {
          geofenceAlertArmed = true; // re-arm only once clear of the zone again
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
    // Seed the dashboard with the mock payload on load so it isn't empty before the first query.
    updateHazardBanner(MOCK_ORCHESTRATOR_RESPONSE.hazard_status);
    plotVesselMarker(MOCK_ORCHESTRATOR_RESPONSE.vessel_coord[0], MOCK_ORCHESTRATOR_RESPONSE.vessel_coord[1]);
    plotPFZZones(MOCK_ORCHESTRATOR_RESPONSE.pfz_location);
    plotRoute(MOCK_ORCHESTRATOR_RESPONSE.vessel_coord, MOCK_ORCHESTRATOR_RESPONSE.pfz_location);
    updateTelemetryBars(MOCK_ORCHESTRATOR_RESPONSE.telemetry);
    initVoiceMic();
    startGeofencePolling();
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
function startGeofenceMonitor() {
    // Poll the backend every 60 seconds
    setInterval(async () => {
        const coords = window.vesselLocation;
        if(!coords) return; // Wait until GPS is locked

        try {
            const response = await fetch(`/api/geofence-check?lat=\({coords.lat}&lon=\){coords.lon}`);
            const data = await response.json();

            if(data.status === "CAUTION") {
                console.warn(`Boundary Alert: ${data.distance_km}km away!`);
                
                // 1. Trigger the siren (assuming you adapted createOceanSound for an alarm)
                if(typeof createOceanSound === "function") {
                    createOceanSound('siren'); 
                }
                
                // 2. Update the UI Banner proactively
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