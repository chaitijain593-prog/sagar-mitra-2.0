// ============================================================
// SAGAR MITRA — SHARED CONTROLS & NEWS FEED ENGINE
// Role Switcher & Multi-Domain Specialized Ocean News Feed
// ============================================================

(function initSagarSharedControls() {
  // ------------------------------------------------------------
  // 1. PERSONA ROLES CONFIGURATION
  // ------------------------------------------------------------
  const ROLES = [
    {
      id: "primary_student",
      name: "Primary Grade Student",
      emoji: "🐬",
      desc: "Creative, child-like & curious ocean buddy exploration"
    },
    {
      id: "high_school",
      name: "High School Student",
      emoji: "🔬",
      desc: "Coursework, STEM oceanography & science lab experiments"
    },
    {
      id: "researcher",
      name: "Researcher",
      emoji: "🏛️",
      desc: "Multiple research notebooks, external sources & deep telemetry"
    },
    {
      id: "coastal_community",
      name: "Coastal Community Resident",
      emoji: "⚓",
      desc: "Local swell, fishing zone advisories & cyclone safety alerts"
    },
    {
      id: "others",
      name: "Others / Ocean Explorer",
      emoji: "🌐",
      desc: "General versatile Claude-inspired ocean AI assistant"
    }
  ];

  // Get or set current persona
  let currentRole = localStorage.getItem("sagarMitraRole") || "researcher";

  // ------------------------------------------------------------
  // 2. NEWS ARTICLES DATA CATALOG
  // ------------------------------------------------------------
  const NEWS_DOMAINS = [
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

  const NEWS_ARTICLES = [
    {
      id: 1,
      domains: ["satellite", "ecology"],
      domainLabel: "🛰️ Satellite Oceanography",
      time: "2 hours ago",
      title: "ISRO & INCOIS Deploy OceanSat-3 Thermal Radiometers to Track Indian Ocean Marine Heatwaves",
      excerpt: "High-resolution thermal infrared bands are now transmitting sub-surface thermal gradients across the Bay of Bengal, providing 6-hour interval boundary current telemetry to coastal researchers.",
      source: "INCOIS Remote Sensing Lab"
    },
    {
      id: 2,
      domains: ["buoys", "deepsea"],
      domainLabel: "🤖 ARGO Float Telemetry",
      time: "3 hours ago",
      title: "Central Arabian Sea ARGO Array Detects Salinity Intrusion at 1,200m Depth",
      excerpt: "Profilers #290145 and #290148 recorded an anomalous pulse of high-salinity Persian Gulf outflow water, modulating sound velocity profiles and mesopelagic sonic layer acoustics.",
      source: "Global ARGO Data Repository"
    },
    {
      id: 3,
      domains: ["fisheries", "satellite"],
      domainLabel: "🐟 Fisheries Intelligence",
      time: "5 hours ago",
      title: "Real-Time Potential Fishing Zone (PFZ) Advisories Released for Konkan & Gujarat Fleets",
      excerpt: "Composite chlorophyll and ocean temperature front analyses highlight massive pelagic fish aggregations off the continental shelf break, cutting fleet fuel consumption by an estimated 28%.",
      source: "National Marine Fisheries Advisory"
    },
    {
      id: 4,
      domains: ["ecology", "buoys"],
      domainLabel: "🌊 Marine Ecology",
      time: "Yesterday",
      title: "Lakshadweep Coral Bleaching Recovery Rate Increases 18% Following Deep Cold Upwelling",
      excerpt: "Autonomous glider surveys at Kadmat and Kavaratti atolls indicate stabilized zooxanthellae density after southwest monsoon currents pumped cooler mesopelagic water onto shallow reef flats.",
      source: "Marine Biodiversity Research Centre"
    },
    {
      id: 5,
      domains: ["weather", "ports"],
      domainLabel: "🌪️ Extreme Coastal Weather",
      time: "Yesterday",
      title: "Deep Depression Over South Andaman Sea Intensifying; Coastal Swell Surge Alert Active",
      excerpt: "Wave rider buoys report significant wave heights climbing to 4.2 meters off Tamil Nadu and Andhra coasts. Automated safety dispatches have been transmitted to port authorities and regional rescue cells.",
      source: "Regional Meteorological Centre"
    },
    {
      id: 6,
      domains: ["ports", "energy"],
      domainLabel: "⚓ Maritime Ports & Logistics",
      time: "2 days ago",
      title: "JNPT Mumbai Inaugurates AI-Optimized Green Shipping Corridor to Singapore",
      excerpt: "Dynamic voyage planning integrating real-time ocean surface currents, bathymetric waypoints, and wind vectors is projected to reduce bunker fuel emissions by 14% on the Malacca Strait route.",
      source: "International Maritime Organization"
    },
    {
      id: 7,
      domains: ["deepsea", "buoys"],
      domainLabel: "🔬 Deep-Sea Exploration",
      time: "3 days ago",
      title: "Samudrayaan Mission: Manned Submersible 'Matsya 6000' Completes 6,000m Pressure Validation",
      excerpt: "Engineered to explore polymetallic nodules and hydrothermal vent ecosystems in the Central Indian Ocean Basin, the titanium pressure hull successfully cleared rigorous hydrostatic chamber qualification.",
      source: "National Institute of Ocean Technology"
    },
    {
      id: 8,
      domains: ["energy", "ecology"],
      domainLabel: "⚡ Blue Economy & Clean Energy",
      time: "4 days ago",
      title: "100MW Ocean Thermal Energy Conversion (OTEC) Pilot Approved for Andaman Coast",
      excerpt: "Utilizing the 21°C thermal gradient between warm surface waters and 1,000m-deep bathypelagic water to deliver continuous baseload renewable energy and municipal desalination.",
      source: "Ministry of Earth Sciences"
    }
  ];

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

    // Set initial active state
    updateDropdownActiveRole(currentRole);

    roleTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      roleDropdown.classList.toggle("open");
    });

    document.querySelectorAll(".role-dropdown-item").forEach(item => {
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        const roleId = item.getAttribute("data-role");
        const found = ROLES.find(r => r.id === roleId);
        if (!found) return;

        currentRole = roleId;
        localStorage.setItem("sagarMitraRole", roleId);
        updateDropdownActiveRole(roleId);
        roleDropdown.classList.remove("open");
        showRoleToast(found);

        // Notify page / chatbot of role change
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
    document.querySelectorAll(".role-dropdown-item").forEach(item => {
      item.classList.toggle("active", item.getAttribute("data-role") === roleId);
    });
  }

  // ------------------------------------------------------------
  // 5. NEWS FEED MODAL INITIALIZATION
  // ------------------------------------------------------------
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

          <!-- Domain Selection Filter Bar (Multi-Select) -->
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

    const filtered = NEWS_ARTICLES.filter(item => {
      // Domain matching
      let matchesDomain = selectedDomains.has("all");
      if (!matchesDomain) {
        matchesDomain = item.domains.some(d => selectedDomains.has(d));
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
          <button class="news-card-read-btn" onclick="alert('Displaying live scientific bulletin: ${item.title.replace(/'/g, "\\'")}')">
            <span>Dispatch</span>
            <span>→</span>
          </button>
        </div>
      </article>
    `).join("");
  }

  // ------------------------------------------------------------
  // 6. AUTO-INIT ON DOM READY
  // ------------------------------------------------------------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initRoleSwitcher();
      initNewsFeedModal();
    });
  } else {
    initRoleSwitcher();
    initNewsFeedModal();
  }

  // Expose helper globally
  window.sagarControls = {
    getRole: () => currentRole,
    setRole: (roleId) => {
      const found = ROLES.find(r => r.id === roleId);
      if (found) {
        currentRole = roleId;
        localStorage.setItem("sagarMitraRole", roleId);
        updateDropdownActiveRole(roleId);
        window.dispatchEvent(new CustomEvent("sagarRoleChanged", { detail: { role: roleId, roleData: found } }));
      }
    },
    openNews: openNewsModal,
    closeNews: closeNewsModal
  };
})();
