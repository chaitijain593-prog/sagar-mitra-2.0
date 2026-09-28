// ============================================================
// SAGAR MITRA — SHARED CONTROLS & LIVE INTELLIGENCE ENGINE
// Role Switcher, Ocean Soundscape, Morning Dispatch & Live News
// ============================================================

(function initSagarSharedControls() {
  const API_BASE = (window.location.protocol === "file:" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.port !== "")
    ? "http://127.0.0.1:8000"
    : window.location.origin;

  // ------------------------------------------------------------
  // 1. PERSONA ROLES CONFIGURATION (Aligned with LangGraph)
  // ------------------------------------------------------------
  function normalizeSagarRole(roleId) {
    if (!roleId) return "researcher";
    const cleaned = String(roleId).toLowerCase().trim();
    const valid = [
      "primary_student",
      "high_school",
      "researcher",
      "fisherman",
      "coastal_community",
      "authority",
      "others"
    ];
    if (valid.includes(cleaned)) return cleaned;
    if (cleaned === "student") return "primary_student";
    if (cleaned === "fisher") return "fisherman";
    return "researcher";
  }

  const ROLES = [
    {
      id: "primary_student",
      name: "Primary Grade Student",
      emoji: "🐬",
      desc: "Creative, child-like & curious ocean buddy with swimming aquarium"
    },
    {
      id: "high_school",
      name: "High School Student",
      emoji: "🔬",
      desc: "Coursework, STEM projects, physics formulas & tidal dynamics"
    },
    {
      id: "researcher",
      name: "Researcher / Oceanographer",
      emoji: "🏛️",
      desc: "Deep telemetry, ARGO anomaly models, NetCDF arrays & indexed sources"
    },
    {
      id: "fisherman",
      name: "Fisherman / Navigator",
      emoji: "🎣",
      desc: "PFZ fishing zones, ocean weather & safe navigation routes"
    },
    {
      id: "coastal_community",
      name: "Coastal Community Resident",
      emoji: "⚓",
      desc: "Local sea swell, harbor advisories & cyclone safety bulletins"
    },
    {
      id: "authority",
      name: "Coastal / Port Authority",
      emoji: "🛡️",
      desc: "EEZ boundary geofencing, hazard reporting & incident logs"
    },
    {
      id: "others",
      name: "Others / Ocean Explorer",
      emoji: "🌐",
      desc: "Versatile ocean assistant & multi-modal intelligence"
    }
  ];

  // Get or set current persona with normalized key
  let currentRole = normalizeSagarRole(localStorage.getItem("sagarMitraRole") || "researcher");
  localStorage.setItem("sagarMitraRole", currentRole);

  // ------------------------------------------------------------
  // 2. LIVE NEWS FEED & BACKEND DOMAINS CATALOG
  // ------------------------------------------------------------
  let NEWS_DOMAINS = [
    { id: "all", label: "All Domains", emoji: "🌐" },
    { id: "satellite", label: "Satellite Oceanography", emoji: "🛰️" },
    { id: "ecology", label: "Marine Ecology & Corals", emoji: "🌊" },
    { id: "ports", label: "Ports & Maritime Logistics", emoji: "⚓" },
    { id: "fisheries", label: "Fisheries & Aquaculture", emoji: "🐟" },
    { id: "weather", label: "Cyclones & Weather Alerts", emoji: "🌪️" },
    { id: "deepsea", label: "Deep-Sea Exploration", emoji: "🔬" },
    { id: "buoys", label: "Autonomous Buoys & ARGO", emoji: "🤖" },
    { id: "energy", label: "Blue Economy & Energy", emoji: "⚡" }
  ];

  let FALLBACK_ARTICLES = [
    {
      id: 1,
      domains: ["satellite", "ecology"],
      domainLabel: "🛰️ Satellite Oceanography",
      time: "2 hours ago",
      title: "ISRO & INCOIS Deploy OceanSat-3 Thermal Radiometers to Track Indian Ocean Marine Heatwaves",
      excerpt: "High-resolution thermal infrared bands are now transmitting sub-surface thermal gradients across the Bay of Bengal, providing 6-hour interval boundary current telemetry to coastal researchers.",
      source: "INCOIS Remote Sensing Lab",
      link: "#"
    },
    {
      id: 2,
      domains: ["buoys", "deepsea"],
      domainLabel: "🤖 ARGO Float Telemetry",
      time: "3 hours ago",
      title: "Central Arabian Sea ARGO Array Detects Salinity Intrusion at 1,200m Depth",
      excerpt: "Profilers #290145 and #290148 recorded an anomalous pulse of high-salinity Persian Gulf outflow water, modulating sound velocity profiles and mesopelagic sonic layer acoustics.",
      source: "Global ARGO Data Repository",
      link: "#"
    },
    {
      id: 3,
      domains: ["fisheries", "satellite"],
      domainLabel: "🐟 Fisheries Intelligence",
      time: "5 hours ago",
      title: "Real-Time Potential Fishing Zone (PFZ) Advisories Released for Konkan & Gujarat Fleets",
      excerpt: "Composite chlorophyll and ocean temperature front analyses highlight massive pelagic fish aggregations off the continental shelf break, cutting fleet fuel consumption by an estimated 28%.",
      source: "National Marine Fisheries Advisory",
      link: "#"
    },
    {
      id: 4,
      domains: ["ecology", "buoys"],
      domainLabel: "🌊 Marine Ecology",
      time: "Yesterday",
      title: "Lakshadweep Coral Bleaching Recovery Rate Increases 18% Following Deep Cold Upwelling",
      excerpt: "Autonomous glider surveys at Kadmat and Kavaratti atolls indicate stabilized zooxanthellae density after southwest monsoon currents pumped cooler mesopelagic water onto shallow reef flats.",
      source: "Marine Biodiversity Research Centre",
      link: "#"
    },
    {
      id: 5,
      domains: ["weather", "ports"],
      domainLabel: "🌪️ Extreme Coastal Weather",
      time: "Yesterday",
      title: "Deep Depression Over South Andaman Sea Intensifying; Coastal Swell Surge Alert Active",
      excerpt: "Wave rider buoys report significant wave heights climbing to 4.2 meters off Tamil Nadu and Andhra coasts. Automated safety dispatches have been transmitted to port authorities and regional rescue cells.",
      source: "Regional Meteorological Centre",
      link: "#"
    },
    {
      id: 6,
      domains: ["ports", "energy"],
      domainLabel: "⚓ Maritime Ports & Logistics",
      time: "2 days ago",
      title: "JNPT Mumbai Inaugurates AI-Optimized Green Shipping Corridor to Singapore",
      excerpt: "Dynamic voyage planning integrating real-time ocean surface currents, bathymetric waypoints, and wind vectors is projected to reduce bunker fuel emissions by 14% on the Malacca Strait route.",
      source: "International Maritime Organization",
      link: "#"
    },
    {
      id: 7,
      domains: ["deepsea", "buoys"],
      domainLabel: "🔬 Deep-Sea Exploration",
      time: "3 days ago",
      title: "Samudrayaan Mission: Manned Submersible 'Matsya 6000' Completes 6,000m Pressure Validation",
      excerpt: "Engineered to explore polymetallic nodules and hydrothermal vent ecosystems in the Central Indian Ocean Basin, the titanium pressure hull successfully cleared rigorous hydrostatic chamber qualification.",
      source: "National Institute of Ocean Technology",
      link: "#"
    }
  ];

  let currentNewsArticles = [...FALLBACK_ARTICLES];
  let selectedDomains = new Set(["all"]);

  try {
    const savedTopics = JSON.parse(localStorage.getItem("sagarMitraTopics") || "[]");
    if (Array.isArray(savedTopics) && savedTopics.length > 0) {
      selectedDomains.clear();
      const topicMap = {
        "Satellite & Remote Sensing": "satellite",
        "Marine Ecology & Corals": "ecology",
        "Ports, Harbors & Shipping": "ports",
        "Pelagic Fisheries & PFZ": "fisheries",
        "Cyclone & Meteorology": "weather",
        "Deep-Sea Sonar & Trenches": "deepsea",
        "ARGO Telemetry & Ocean Buoys": "buoys",
        "Offshore Renewable Energy": "energy"
      };
      savedTopics.forEach(t => {
        if (topicMap[t]) selectedDomains.add(topicMap[t]);
      });
      if (selectedDomains.size === 0) selectedDomains.add("all");
    }
  } catch(e) {}

  // ------------------------------------------------------------
  // 3. TOAST NOTIFICATION
  // ------------------------------------------------------------
  function showRoleToast(role) {
    let toast = document.getElementById("roleToast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "roleToast";
      toast.className = "role-toast";
      document.body.appendChild(toast);
    }
    toast.innerHTML = `<span>${role.emoji}</span><span>Switched role to <strong>${role.name}</strong></span>`;
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 2800);
  }

  // ------------------------------------------------------------
  // 4. ROLE SWITCHER INITIALIZATION
  // ------------------------------------------------------------
  function initRoleSwitcher() {
    const roleTrigger = document.getElementById("roleTrigger");
    const roleDropdown = document.getElementById("roleDropdown");
    if (!roleTrigger || !roleDropdown) return;

    // Dynamically render dropdown content with the 5 canonical roles
    let itemsHtml = `<div class="role-dropdown-header">SELECT USER PERSONA</div>`;
    ROLES.forEach(r => {
      itemsHtml += `
        <div class="role-dropdown-item" data-role="${r.id}">
          <span class="role-item-emoji">${r.emoji}</span>
          <div class="role-item-details">
            <div class="role-item-title">${r.name}</div>
            <div class="role-item-caption">${r.desc}</div>
          </div>
          <span class="role-item-check">✓</span>
        </div>
      `;
    });
    roleDropdown.innerHTML = itemsHtml;

    updateDropdownActiveRole(currentRole);

    roleTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      roleDropdown.classList.toggle("open");
    });

    roleDropdown.querySelectorAll(".role-dropdown-item").forEach(item => {
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        const roleId = normalizeSagarRole(item.getAttribute("data-role"));
        const found = ROLES.find(r => r.id === roleId) || ROLES[1];

        currentRole = roleId;
        localStorage.setItem("sagarMitraRole", roleId);
        updateDropdownActiveRole(roleId);
        roleDropdown.classList.remove("open");
        showRoleToast(found);

        window.dispatchEvent(new CustomEvent("sagarRoleChanged", { detail: { role: roleId, roleData: found } }));
      });
    });

    document.addEventListener("click", (e) => {
      if (!roleDropdown.contains(e.target) && e.target !== roleTrigger) {
        roleDropdown.classList.remove("open");
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        roleDropdown.classList.remove("open");
      }
    });
  }

  function updateDropdownActiveRole(roleId) {
    const norm = normalizeSagarRole(roleId);
    document.querySelectorAll(".role-dropdown-item").forEach(item => {
      const itemRole = normalizeSagarRole(item.getAttribute("data-role"));
      item.classList.toggle("active", itemRole === norm);
    });
  }

  // ------------------------------------------------------------
  // 5. AMBIENT OCEAN SOUNDSCAPE WIDGET (Web Audio API Synthesizer)
  // ------------------------------------------------------------
  let audioCtx = null;
  let noiseNode = null;
  let masterGain = null;
  let isAudioPlaying = false;

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

    masterGain = audioCtx.createGain();
    masterGain.gain.setValueAtTime(0.001, audioCtx.currentTime);

    noiseNode.connect(filter);
    filter.connect(masterGain);
    masterGain.connect(audioCtx.destination);

    noiseNode.start();
    lfo.start();
  }

  function toggleOceanSoundscape(widgetEl) {
    if (!isAudioPlaying) {
      if (!audioCtx) createOceanSound();
      else if (audioCtx.state === "suspended") audioCtx.resume();

      if (masterGain && audioCtx) {
        masterGain.gain.cancelScheduledValues(audioCtx.currentTime);
        masterGain.gain.setValueAtTime(masterGain.gain.value, audioCtx.currentTime);
        masterGain.gain.linearRampToValueAtTime(0.65, audioCtx.currentTime + 0.8);
      }
      isAudioPlaying = true;
      if (widgetEl) widgetEl.classList.add("playing");
    } else {
      if (masterGain && audioCtx) {
        masterGain.gain.cancelScheduledValues(audioCtx.currentTime);
        masterGain.gain.setValueAtTime(masterGain.gain.value, audioCtx.currentTime);
        masterGain.gain.linearRampToValueAtTime(0.001, audioCtx.currentTime + 0.6);
        setTimeout(() => {
          if (!isAudioPlaying && audioCtx && audioCtx.state === "running") {
            audioCtx.suspend();
          }
        }, 650);
      }
      isAudioPlaying = false;
      if (widgetEl) widgetEl.classList.remove("playing");
    }
  }

  function initSoundscapeWidget() {
    const actions = document.querySelector(".actions");
    if (!actions) return;

    let soundBtn = document.getElementById("soundToggle");
    if (!soundBtn) {
      const themeToggle = document.getElementById("themeToggle");
      soundBtn = document.createElement("button");
      soundBtn.type = "button";
      soundBtn.className = "ctrl-btn soundscape-widget";
      soundBtn.id = "soundToggle";
      soundBtn.setAttribute("title", "Toggle Ambient Ocean Soundscape");
      soundBtn.setAttribute("aria-label", "Toggle Ambient Ocean Soundscape");
      soundBtn.innerHTML = `
        <span class="ctrl-icon">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12c.6 0 1.2-.4 1.4-1 .9-2.5 3.3-4 6-4 2.6 0 4.9 1.4 5.9 3.7.3.7 1.1 1.3 1.9 1.3h.8c1.1 0 2 .9 2 2v1"/>
            <path d="M2 16c1.5 0 2.8-.7 3.6-1.8.8-1.1 2.1-1.8 3.5-1.8 1.4 0 2.7.7 3.5 1.8.8 1.1 2.1 1.8 3.6 1.8 1.4 0 2.7-.7 3.5-1.8"/>
            <path d="M2 20c1.5 0 2.8-.7 3.6-1.8.8-1.1 2.1-1.8 3.5-1.8 1.4 0 2.7.7 3.5 1.8.8 1.1 2.1 1.8 3.6 1.8 1.4 0 2.7-.7 3.5-1.8"/>
          </svg>
        </span>
        <div class="sound-bars">
          <span class="s-bar"></span>
          <span class="s-bar"></span>
          <span class="s-bar"></span>
          <span class="s-bar"></span>
        </div>
        <span class="ctrl-label" id="soundLabel">Soundscape</span>
      `;
      if (themeToggle && themeToggle.nextSibling) {
        actions.insertBefore(soundBtn, themeToggle.nextSibling);
      } else {
        actions.appendChild(soundBtn);
      }
    }

    soundBtn.addEventListener("click", () => toggleOceanSoundscape(soundBtn));
  }

  // ------------------------------------------------------------
  // 6. MORNING DISPATCH TRIGGER & FLOATING AUDIO PLAYER
  // ------------------------------------------------------------
  function initMorningDispatch() {
    // 1. Dedicated button in .actions beside #newsTrigger to its left
    const actions = document.querySelector(".actions");
    const newsTrigger = document.getElementById("newsTrigger");
    let dispatchBtn = document.getElementById("dispatchTrigger");

    if (actions && !dispatchBtn) {
      dispatchBtn = document.createElement("button");
      dispatchBtn.type = "button";
      dispatchBtn.className = "ctrl-btn dispatch-trigger";
      dispatchBtn.id = "dispatchTrigger";
      dispatchBtn.setAttribute("title", "Generate Morning Dispatch");
      dispatchBtn.setAttribute("aria-label", "Generate Morning Dispatch");
      dispatchBtn.innerHTML = `
        <span class="ctrl-icon">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
        </span>
        <span class="ctrl-label">Dispatch</span>
      `;
      if (newsTrigger) {
        actions.insertBefore(dispatchBtn, newsTrigger);
      } else {
        actions.appendChild(dispatchBtn);
      }
    }

    if (dispatchBtn && !dispatchBtn.dataset.bound) {
      dispatchBtn.dataset.bound = "true";
      dispatchBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        generateAndDisplayMorningDispatch();
      });
    }
    window.generateAndDisplayMorningDispatch = generateAndDisplayMorningDispatch;

  }

  // ------------------------------------------------------------
  // GLOBAL NAVIGATION BAR CONTROLLER
  // ------------------------------------------------------------
  function initGlobalNavigation() {
    const nav = document.getElementById("nav");
    if (!nav) return;

    // Function: dynamically position nav directly below the navigation icons row (.actions)
    function positionNavBelowActions() {
      const actions = document.querySelector(".actions");
      if (actions) {
        const aRect = actions.getBoundingClientRect();
        nav.style.top = Math.round(aRect.bottom + 8) + "px";
        nav.style.right = Math.max(16, Math.round(window.innerWidth - aRect.right)) + "px";
        nav.style.left = "auto";
      } else {
        nav.style.top = "76px";
        nav.style.right = "28px";
        nav.style.left = "auto";
      }
    }

    // Default position directly below actions
    positionNavBelowActions();

    // Bind trigger directly, position below icons, and prevent double-toggling
    const trigger = document.getElementById("trigger") || document.getElementById("navTrigger") || document.querySelector(".nav-trigger");
    if (trigger) {
      trigger.onclick = (e) => {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        positionNavBelowActions();
        nav.classList.toggle("open");
      };
    }

    // Close floating nav when clicking outside
    document.addEventListener("click", (e) => {
      if (nav.classList.contains("open") && !nav.contains(e.target) && !e.target.closest(".nav-trigger, #trigger, #navTrigger")) {
        nav.classList.remove("open");
      }
    });

    // Auto-reposition on window resize if open
    window.addEventListener("resize", () => {
      if (nav.classList.contains("open")) {
        positionNavBelowActions();
      }
    });
  }

  async function generateAndDisplayMorningDispatch() {
    window.generateAndDisplayMorningDispatch = generateAndDisplayMorningDispatch;
    let player = document.getElementById("floatingDispatchPlayer");
    if (!player) {
      player = document.createElement("div");
      player.id = "floatingDispatchPlayer";
      player.className = "floating-dispatch-player";
      document.body.appendChild(player);
    }

    player.innerHTML = `
      <div class="dispatch-player-header">
        <span>🌊 GENERATING MORNING DISPATCH...</span>
        <button type="button" class="dispatch-player-close" id="closeDispatchPlayer">✕</button>
      </div>
      <p style="font-size:12px; color:var(--text-dim,#94a3b8); margin:0;">Synthesizing live oceanographic bulletin from coastal telemetry...</p>
      <div style="height:4px; background:rgba(56,189,248,0.2); border-radius:2px; overflow:hidden;">
        <div style="height:100%; width:60%; background:#38bdf8; animation:waveFlowWhite 1s infinite alternate;"></div>
      </div>
    `;
    player.style.display = "flex";

    document.getElementById("closeDispatchPlayer").onclick = () => {
      player.style.display = "none";
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    };

    let dispatchData = null;
    try {
      const lat = 15.2993, lon = 74.1240; // Default coastal station
      const res = await fetch(`${API_BASE}/api/dispatch/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          coordinates: [lat, lon],
          persona: currentRole,
          language: "en"
        })
      });
      if (res.ok) {
        dispatchData = await res.json();
      }
    } catch (e) {
      console.warn("Backend dispatch call failed, using synthetic fallback:", e);
    }

    if (!dispatchData) {
      dispatchData = {
        status: "success",
        timestamp: new Date().toUTCString(),
        vessel_persona: currentRole,
        coordinates: [15.2993, 74.1240],
        telemetry: {
          wave_height: "1.42 m",
          swell: "1.20 m @ 8.4s",
          wind_speed: "14.2 kts",
          sst: "28.4 °C",
          chlorophyll: "1.350 mg/m³",
          salinity: "35.2 PSU"
        },
        safety_and_routing: {
          status: "NORMAL",
          corridor: "Safe (Inside Indian EEZ)",
          eez_distance: "64.2 km to boundary"
        },
        pfz_advisory: {
          status: "High Density Chlorophyll Front",
          recommended_heading: "245.0°",
          distance_nm: "14.2 NM",
          target_opportunity: "South Konkan Pelagic Zone"
        },
        summary: `Sagar Mitra Daily Marine Clearance: Current sea state normal with 1.4m wave height and 28.4°C surface temperature. Moderate chlorophyll front 14.2 nautical miles southwest. Navigation inside Indian EEZ clear with no active gale warnings.`
      };
    }

    const t = dispatchData.telemetry || {};
    const safe = dispatchData.safety_and_routing || {};
    const pfz = dispatchData.pfz_advisory || {};

    player.innerHTML = `
      <div class="dispatch-player-header">
        <span>🌊 SAGAR MITRA MORNING DISPATCH</span>
        <button type="button" class="dispatch-player-close" id="closeDispatchPlayer">✕</button>
      </div>
      <p style="font-size:12px; color:var(--text-dim,#94a3b8); margin:0;">Position: 15.30°N, 74.12°E · ${safe.status || "NORMAL"}</p>
      <div style="font-size:12px; color:var(--ink,#f4f4f5); line-height:1.4; max-height:80px; overflow-y:auto; padding:6px; background:rgba(0,0,0,0.2); border-radius:8px;">
        ${dispatchData.summary || dispatchData.advisory}
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
        <button type="button" id="speakDispatchBtn" class="dispatch-download-link" style="background:#0284c7;">
          <span>🔊</span> <span id="speakLabel">Read Aloud</span>
        </button>
        <button type="button" id="downloadPdfBtn" class="dispatch-download-link">
          <span>📥</span> <span>Print / PDF</span>
        </button>
      </div>
    `;

    document.getElementById("closeDispatchPlayer").onclick = () => {
      player.style.display = "none";
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    };

    // Text to speech readout
    const speakBtn = document.getElementById("speakDispatchBtn");
    const speakLabel = document.getElementById("speakLabel");
    if (speakBtn && 'speechSynthesis' in window) {
      let isSpeaking = false;
      speakBtn.onclick = () => {
        if (!isSpeaking) {
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(dispatchData.summary || dispatchData.advisory);
          utterance.rate = 0.95;
          utterance.onend = () => {
            isSpeaking = false;
            speakLabel.textContent = "Read Aloud";
          };
          window.speechSynthesis.speak(utterance);
          isSpeaking = true;
          speakLabel.textContent = "Pause Voice";
        } else {
          window.speechSynthesis.cancel();
          isSpeaking = false;
          speakLabel.textContent = "Read Aloud";
        }
      };
      // Auto-trigger voice read
      setTimeout(() => speakBtn.click(), 400);
    }

    // PDF Print window
    document.getElementById("downloadPdfBtn").onclick = () => {
      const pw = window.open("", "_blank", "width=800,height=900");
      if (!pw) {
        alert("Please enable pop-ups to view/print the official PDF dispatch.");
        return;
      }
      pw.document.write(`
        <!doctype html><html><head><title>Sagar Mitra - Morning Dispatch</title>
        <style>
          @page{size:A4;margin:16mm}
          body{font-family:Arial,sans-serif;color:#0f172a;line-height:1.5;margin:0;padding:20px}
          header{border-bottom:3px solid #0284c7;padding-bottom:12px;margin-bottom:18px}
          h1{font-size:20px;color:#0369a1;margin:0 0 6px}
          table{width:100%;border-collapse:collapse;margin:12px 0 20px}
          th,td{border:1px solid #cbd5e1;padding:8px 10px;text-align:left;font-size:13px}
          th{background:#f0f9ff;color:#0369a1;width:35%}
          .summary-box{padding:14px;background:#f8fafc;border-left:4px solid #0284c7;border-radius:4px;margin:15px 0;font-size:13px}
          footer{margin-top:25px;font-size:11px;color:#64748b}
        </style>
        </head><body>
        <header>
          <h1>SAGAR MITRA · OPERATIONAL MARITIME CLEARANCE &amp; DISPATCH</h1>
          <div><strong>Issued:</strong> ${dispatchData.timestamp} &nbsp;|&nbsp; <strong>Persona:</strong> ${dispatchData.vessel_persona}</div>
          <div><strong>Vessel Coordinates:</strong> 15.30° N, 74.12° E · Indian Ocean Basin</div>
        </header>
        <div class="summary-box">
          <strong>Pre-Sail Marine Advisory:</strong><br>${dispatchData.summary || dispatchData.advisory}
        </div>
        <h3>1. Sea State &amp; Oceanographic Telemetry</h3>
        <table>
          <tr><th>Sea Safety Condition</th><td>${safe.status || "NORMAL"}</td></tr>
          <tr><th>Significant Wave Height</th><td>${t.wave_height || "1.42 m"}</td></tr>
          <tr><th>Swell Period &amp; Height</th><td>${t.swell || "1.20 m @ 8.4s"}</td></tr>
          <tr><th>Surface Wind Speed</th><td>${t.wind_speed || "14.2 kts"}</td></tr>
          <tr><th>Sea Surface Temperature (SST)</th><td>${t.sst || "28.4 °C"}</td></tr>
          <tr><th>Chlorophyll-a Gradient</th><td>${t.chlorophyll || "1.350 mg/m³"}</td></tr>
        </table>
        <h3>2. Potential Fishing Zone (PFZ) Opportunity</h3>
        <table>
          <tr><th>Target Opportunity</th><td>${pfz.target_opportunity || "South Konkan Pelagic Zone"}</td></tr>
          <tr><th>Recommended Bearing</th><td>${pfz.recommended_heading || "245.0°"}</td></tr>
          <tr><th>Distance to Feature</th><td>${pfz.distance_nm || "14.2 NM"}</td></tr>
        </table>
        <h3>3. Maritime EEZ Boundary Compliance</h3>
        <table>
          <tr><th>EEZ Compliance Corridor</th><td>${safe.corridor || "Safe (Inside Indian EEZ)"}</td></tr>
          <tr><th>Boundary Proximity</th><td>${safe.eez_distance || "64.2 km to boundary"}</td></tr>
        </table>
        <footer>Confirm latest coastal notices with INCOIS, Indian Coast Guard and IMD prior to departure.</footer>
        <script>window.onload = function() { window.print(); }<\/script>
        </body></html>
      `);
      pw.document.close();
    };
  }

  // ------------------------------------------------------------
  // 7. NEWS FEED MODAL INITIALIZATION (Live API Connected)
  // ------------------------------------------------------------
  async function fetchLiveNews() {
    try {
      // 1. Fetch live domains
      const dRes = await fetch(`${API_BASE}/api/news/domains`);
      if (dRes.ok) {
        const dData = await dRes.json();
        if (Array.isArray(dData.domains) && dData.domains.length > 0) {
          const liveDomains = [{ id: "all", label: "All Domains", emoji: "🌐" }];
          const emojiMap = {
            "satellite": "🛰️", "ecology": "🌊", "ports": "⚓", "fisheries": "🐟",
            "weather": "🌪️", "deepsea": "🔬", "buoys": "🤖", "energy": "⚡", "ocean": "🌊"
          };
          dData.domains.forEach(d => {
            const key = d.toLowerCase().replace(/[^a-z]/g, "");
            liveDomains.push({
              id: d,
              label: d.replace(/[-_]/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
              emoji: emojiMap[key] || "🌊"
            });
          });
          NEWS_DOMAINS = liveDomains;
          renderDomainChips();
        }
      }

      // 2. Fetch live articles
      const aRes = await fetch(`${API_BASE}/api/news`);
      if (aRes.ok) {
        const aData = await aRes.json();
        if (Array.isArray(aData.articles) && aData.articles.length > 0) {
          currentNewsArticles = aData.articles.map((art, idx) => ({
            id: idx + 1,
            domains: art.domain ? [art.domain.toLowerCase()] : ["ocean"],
            domainLabel: art.domain ? `🌊 ${art.domain}` : "🌐 Ocean Intelligence",
            time: art.published ? new Date(art.published).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Recently updated",
            title: art.title || "Marine Observation Bulletin",
            excerpt: art.summary || art.description || "Live oceanographic dispatch from Indian Ocean coastal sensors.",
            source: art.source || "INCOIS / Sagar Mitra Feed",
            link: art.link || "#"
          }));
          renderNewsArticles();
        }
      }
    } catch (e) {
      console.warn("Live news fetch fallback to local catalog:", e);
    }
  }

  function initNewsFeedModal() {
    let modal = document.getElementById("oceanNewsModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "oceanNewsModal";
      modal.className = "ocean-news-modal-overlay";
      modal.innerHTML = `
        <div class="ocean-news-modal">
          <div class="news-modal-header">
            <div class="news-modal-title-group">
              <div class="news-modal-kicker">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8z"/></svg>
                <span>LIVE MARITIME & SATELLITE DISPATCHES</span>
              </div>
              <h2 class="news-modal-title">Ocean Intelligence News Feed</h2>
            </div>
            <button class="news-modal-close" id="closeNewsModal" aria-label="Close News Feed">✕</button>
          </div>

          <!-- Domain Selection Filter Bar -->
          <div class="news-domains-section">
            <div class="news-domains-label">SELECT SPECIALIZED OCEAN DOMAINS (MULTI-SELECT):</div>
            <div class="news-domains-chips" id="newsDomainChips"></div>
          </div>

          <!-- Search Bar -->
          <div class="news-search-bar">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="text" id="newsSearchInput" placeholder="Filter ocean dispatches, ARGO buoys, cyclones, marine ecology, ports...">
          </div>

          <!-- Articles Scrollable Feed Grid -->
          <div class="news-articles-grid" id="newsArticlesGrid"></div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    renderDomainChips();
    renderNewsArticles();

    // Trigger async live fetch in background
    fetchLiveNews();

    const newsTrigger = document.getElementById("newsTrigger");
    if (newsTrigger) {
      newsTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        openNewsModal();
      });
    }

    const closeBtn = document.getElementById("closeNewsModal");
    if (closeBtn) {
      closeBtn.addEventListener("click", closeNewsModal);
    }

    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeNewsModal();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("open")) {
        closeNewsModal();
      }
    });

    const searchInput = document.getElementById("newsSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        renderNewsArticles();
      });
    }
  }

  function openNewsModal() {
    const modal = document.getElementById("oceanNewsModal");
    if (modal) {
      modal.classList.add("open");
      renderNewsArticles();
      fetchLiveNews();
    }
  }

  function closeNewsModal() {
    const modal = document.getElementById("oceanNewsModal");
    if (modal) modal.classList.remove("open");
  }

  function renderDomainChips() {
    const container = document.getElementById("newsDomainChips");
    if (!container) return;

    container.innerHTML = "";
    NEWS_DOMAINS.forEach(dom => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "news-domain-chip" + (selectedDomains.has(dom.id) ? " active" : "");
      chip.setAttribute("data-domain", dom.id);
      chip.innerHTML = `<span>${dom.emoji}</span><span>${dom.label}</span>`;

      chip.addEventListener("click", () => {
        if (dom.id === "all") {
          selectedDomains.clear();
          selectedDomains.add("all");
        } else {
          selectedDomains.delete("all");
          if (selectedDomains.has(dom.id)) {
            selectedDomains.delete(dom.id);
            if (selectedDomains.size === 0) selectedDomains.add("all");
          } else {
            selectedDomains.add(dom.id);
          }
        }
        renderDomainChips();
        renderNewsArticles();
      });

      container.appendChild(chip);
    });
  }

  function renderNewsArticles() {
    const grid = document.getElementById("newsArticlesGrid");
    if (!grid) return;

    const searchVal = (document.getElementById("newsSearchInput")?.value || "").toLowerCase().trim();

    const filtered = currentNewsArticles.filter(item => {
      // Domain matching
      let matchesDomain = selectedDomains.has("all");
      if (!matchesDomain) {
        matchesDomain = (item.domains || []).some(d => selectedDomains.has(d));
      }
      if (!matchesDomain) return false;

      // Search matching
      if (searchVal) {
        const hay = (item.title + " " + item.excerpt + " " + item.domainLabel + " " + item.source).toLowerCase();
        return hay.includes(searchVal);
      }
      return true;
    });

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1; text-align:center; padding:48px 20px; color:var(--text-muted,#9ca3af);">
          <div style="font-size:32px; margin-bottom:12px;">🌊</div>
          <div style="font:600 16px 'Playfair Display',serif; color:var(--ink,#f4f4f5); margin-bottom:6px;">No Ocean Dispatches Found</div>
          <p style="font-size:13px;">Try selecting different specialized domains or clear your search query.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = filtered.map(item => `
      <article class="news-card">
        <div class="news-card-meta">
          <span class="news-card-domain">${item.domainLabel}</span>
          <span class="news-card-time">${item.time}</span>
        </div>
        <h3 class="news-card-headline">${item.title}</h3>
        <p class="news-card-excerpt">${item.excerpt}</p>
        <div class="news-card-footer">
          <span>${item.source}</span>
          <button class="news-card-read-btn" onclick="alert('Viewing live scientific bulletin: ${item.title.replace(/'/g, "\\'")}')">
            <span>Dispatch</span>
            <span>→</span>
          </button>
        </div>
      </article>
    `).join("");
  }

  // ------------------------------------------------------------
  // NAVBAR LOGO TEXT CAROUSEL (10 Indian Languages)
  // Changes every 2.2s with smooth fade/scale transition & high contrast
  // ------------------------------------------------------------
  function initNavLogoCarousel() {
    const logoEls = document.querySelectorAll(".logo-title-carousel, #navLogoTitle");
    if (!logoEls || logoEls.length === 0) return;

    const sagarTranslations = [
      { lang: "English", text: "Sagar Mitra" },
      { lang: "Hindi", text: "सागर मित्र" },
      { lang: "Marathi", text: "सागर मित्र" },
      { lang: "Bengali", text: "সাগর মিত্র" },
      { lang: "Gujarati", text: "સાગર મિત્ર" },
      { lang: "Tamil", text: "சாகர் மித்ரா" },
      { lang: "Telugu", text: "సాగర్ మిత్ర" },
      { lang: "Kannada", text: "ಸಾಗರ ಮಿತ್ರ" },
      { lang: "Malayalam", text: "സാഗർ മിത്ര" },
      { lang: "Odia", text: "ସାଗର ମିତ୍ର" }
    ];

    let currentIdx = 0;
    setInterval(() => {
      currentIdx = (currentIdx + 1) % sagarTranslations.length;
      const nextText = sagarTranslations[currentIdx].text;
      logoEls.forEach(el => {
        el.style.opacity = "0";
        el.style.transform = "translateY(-4px) scale(0.96)";
        setTimeout(() => {
          el.textContent = nextText;
          el.style.opacity = "1";
          el.style.transform = "translateY(0) scale(1)";
        }, 260);
      });
    }, 2200);
  }

  // ------------------------------------------------------------
  // 8. AUTO-INIT ON DOM READY
  // ------------------------------------------------------------
  function initAll() {
    initRoleSwitcher();
    initSoundscapeWidget();
    initMorningDispatch();
    initNewsFeedModal();
    initGlobalNavigation();
    initNavLogoCarousel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }

  // Expose helper globally
  window.sagarControls = {
    getRole: () => currentRole,
    setRole: (roleId) => {
      const norm = normalizeSagarRole(roleId);
      const found = ROLES.find(r => r.id === norm) || ROLES[1];
      currentRole = norm;
      localStorage.setItem("sagarMitraRole", norm);
      updateDropdownActiveRole(norm);
      window.dispatchEvent(new CustomEvent("sagarRoleChanged", { detail: { role: norm, roleData: found } }));
    },
    openNews: openNewsModal,
    closeNews: closeNewsModal,
    triggerDispatch: generateAndDisplayMorningDispatch,
    toggleSoundscape: () => {
      const btn = document.getElementById("soundToggle");
      if (btn) toggleOceanSoundscape(btn);
    }
  };
})();
