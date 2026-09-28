/* Live OBIS occurrence view for the production Leaflet map. */
(() => {
  const API_BASE = window.SAGAR_MITRA_API_BASE ||
    (location.port === "8000" ? location.origin : "http://127.0.0.1:8000");
  const PATH_COLOR = "#22d3ee";
  const SPECIES_COLORS = ["#55d6be", "#ffb454", "#63b3ed", "#f472b6", "#a3e635", "#c4b5fd", "#fb7185", "#facc15"];
  const SPECIES_IMAGES = [
    {match:/thunnus|tuna/i,file:"yellowfin_tuna.png"},
    {match:/sardinella|sardine/i,file:"indian_oil_sardine.png"},
    {match:/cheloni|lepidochelys|turtle/i,file:"green_sea_turtle.png"},
    {match:/dugong/i,file:"dugong_sea_cow.png"},
    {match:/mobula|manta/i,file:"manta_ray.png"},
    {match:/scylla|crab/i,file:"mud_crab.png"}
  ];
  const speciesImage = name => SPECIES_IMAGES.find(entry=>entry.match.test(name)) || null;
  const escapeText = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[char]));
  const safeSource = value => {
    try { const url = new URL(value); return url.protocol === "https:" ? url.href : ""; }
    catch { return ""; }
  };

  const panel = document.getElementById("obisPanel");
  const controlsHost = panel?.querySelector(".obis-controls-grid");
  if (!panel || !controlsHost || typeof map === "undefined" || typeof obisLayerGroup === "undefined") return;

  // Replace the old fixed taxonomy list with searchable species and service-supported filters.
  controlsHost.innerHTML = `
    <div class="marine-live-controls">
      <label>Species search
        <input id="marineLiveSpecies" type="search" list="marineSpeciesHints" placeholder="Search, e.g. dolphin or tuna" autocomplete="off">
        <datalist id="marineSpeciesHints"><option value="tuna"><option value="turtle"><option value="dolphin"><option value="whale"><option value="coral"><option value="Thunnus albacares"></datalist>
      </label>
      <label>Region<select id="marineLiveRegion"><option value="indian_ocean">Indian Ocean</option><option value="indian_eez">Indian EEZ</option><option value="global">Global</option></select></label>
      <div class="marine-live-dates">
        <label>Start date<input id="marineLiveStart" type="date"></label>
        <label>End date<input id="marineLiveEnd" type="date"></label>
      </div>
      <label>Season<select id="marineLiveSeason"><option value="">Any time of year</option><option value="winter">Winter (Decâ€“Feb)</option><option value="summer">Summer (Marâ€“May)</option><option value="monsoon">Monsoon (Junâ€“Sep)</option><option value="post_monsoon">Post-monsoon (Octâ€“Nov)</option><option value="current_month">Current month</option></select></label>
      <label class="marine-live-toggle"><input id="marineLivePaths" type="checkbox" disabled> Show selected species occurrence path</label>
      <div class="marine-path-hint" id="marinePathHint">Enter a scientific or supported common species name (for example, tuna) to enable its path.</div>
      <label class="marine-live-toggle"><input id="marineLiveDepthColor" type="checkbox" checked> Color-grade by depth</label>
      <label>Depth peel <span id="marineLiveDepthValue">4,000 m</span><input id="marineLiveDepth" type="range" min="0" max="4000" step="50" value="4000"></label>
      <div class="marine-depth-legend"><div class="marine-depth-gradient"></div><div class="marine-depth-legend-row"><span>Sky blue Â· 0â€“50 m</span><span>Medium blue Â· 50â€“1,000 m</span><span>Dark navy Â· &gt;1,000 m</span></div><span>Gray Â· depth not reported</span></div>
      <div class="marine-path-key" id="marineLivePathLegend"></div>
      <div class="marine-live-actions"><button type="button" id="marineLiveApply">Visualize</button><button type="button" id="marineLiveReset">Reset</button></div>
      <div class="marine-live-status" id="marineLiveStatus" role="status" aria-live="polite">Choose filters and visualize observations.</div>
    </div>`;
  panel.querySelector(".obis-hotspot-box")?.setAttribute("hidden", "");

  const markerCluster = typeof L.markerClusterGroup === "function" ? L.markerClusterGroup({
    showCoverageOnHover: false,
    chunkedLoading: true,
    maxClusterRadius: 42,
    disableClusteringAtZoom: 11,
    spiderfyOnMaxZoom: true,
  }) : L.layerGroup();
  let pendingController = null;
  let records = [];
  let currentTrackInfo = {};
  const speciesInput = document.getElementById("marineLiveSpecies");
  const pathsToggle = document.getElementById("marineLivePaths");
  const pathHint = document.getElementById("marinePathHint");
  const hasSpeciesQuery = value => Boolean(value.trim());
  const commonTaxonAliases = {
    tuna:["thunnus"], tunas:["thunnus"],
    turtle:["chelonia","chelonoidea","lepidochelys","caretta","eretmochelys","dermochelys"],
    turtles:["chelonia","chelonoidea","lepidochelys","caretta","eretmochelys","dermochelys"],
    "sea turtle":["chelonia","chelonoidea","lepidochelys","caretta","eretmochelys","dermochelys"],
    dolphin:["delphinidae","delphinus","stenella","sousa","orcaella"],
    dolphins:["delphinidae","delphinus","stenella","sousa","orcaella"],
    whale:["cetacea","balaenoptera","megaptera","physeter"], whales:["cetacea","balaenoptera","megaptera","physeter"],
    shark:["selachimorpha","carcharhinus","rhincodon"], sharks:["selachimorpha","carcharhinus","rhincodon"],
    ray:["batoidea","mobula"], rays:["batoidea","mobula"], "manta ray":["mobula"]
  };
  function matchesSelectedSpecies(scientificName) {
    const query=speciesInput.value.trim().toLocaleLowerCase();
    if (!query) return false;
    const observed=String(scientificName || "").toLocaleLowerCase();
    const aliases=commonTaxonAliases[query];
    return aliases ? aliases.some(alias=>observed.includes(alias)) : observed.startsWith(query);
  }
  function syncPathControl() {
    const enabled = hasSpeciesQuery(speciesInput.value);
    pathsToggle.disabled = !enabled;
    if (!enabled) {
      pathsToggle.checked = false;
      pathHint.textContent = "Enter a species name (scientific or common, e.g. tuna) to enable its path.";
    } else {
      pathHint.textContent = "Scientific and supported common names work. Shows dated population observations, not one tracked animal.";
    }
  }
  syncPathControl();

  function colorFor(record) {
    if (!document.getElementById("marineLiveDepthColor").checked) return "#39bdf2";
    if (/^#[\da-f]{6}$/i.test(record.depth_color || "")) return record.depth_color;
    const depth = Number(record.depth_m);
    if (!Number.isFinite(depth)) return "#94a3b8";
    if (depth <= 50) return "#87cefa";
    if (depth <= 1000) return "#1e88e5";
    return "#001b44";
  }

  function visibleRecords() {
    const maxDepth = Number(document.getElementById("marineLiveDepth").value);
    return records.filter(record => {
      const depth = record.depth_m == null || record.depth_m === "" ? null : Number(record.depth_m);
      return depth == null || !Number.isFinite(depth) ? maxDepth >= 4000 : depth <= maxDepth;
    });
  }

  function renderRecords(trackInfo = currentTrackInfo) {
    markerCluster.clearLayers();
    obisLayerGroup.clearLayers();
    obisLayerGroup.addLayer(markerCluster);
    const shown = visibleRecords();
    const depthCounts = {surface:0, mid_water:0, deep_sea:0, unknown:0};
    const pathRecords = [];

    shown.forEach(record => {
      const lat = Number(record.lat), lon = Number(record.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
      const species = record.species_name || "Unknown species";
      const depth = record.depth_m == null || record.depth_m === "" ? null : Number(record.depth_m);
      const isSelectedSpecies = matchesSelectedSpecies(species);
      if (record.track_only) {
        if (isSelectedSpecies && record.track_scope === "global" && record.observation_date && Number.isFinite(Date.parse(record.observation_date))) {
          pathRecords.push({lat, lon, date:record.observation_date});
        }
        return;
      }
      const category = ["surface", "mid_water", "deep_sea"].includes(record.depth_category)
        ? record.depth_category : depth == null ? "unknown" : depth <= 50 ? "surface" : depth <= 1000 ? "mid_water" : "deep_sea";
      depthCounts[category]++;
      const color = colorFor(record);
      const icon = L.divIcon({
        className: "",
        html: `<div class="marine-live-observation-marker depth-${category}" style="background:${color};color:${color}"></div>`,
        iconSize: [17,17], iconAnchor: [8,8],
      });
      const url = safeSource(record.source_link);
      const date = record.observation_date || "Date unavailable";
      const popup = `<article class="marine-observation-popup"><strong>${escapeText(species)}</strong><div>Date: ${escapeText(date)}</div><div>Depth: ${depth == null || !Number.isFinite(depth) ? "Not reported" : `${depth.toLocaleString()} m`}</div><div>Season: ${escapeText(record.season || "Unknown")}</div><div>Dataset: ${escapeText(record.dataset_name || "OBIS")}</div>${url ? `<a href="${escapeText(url)}" target="_blank" rel="noopener noreferrer">View source â†—</a>` : ""}</article>`;
      L.marker([lat, lon], {icon, title: `${species} Â· ${date}`}).bindPopup(popup).bindTooltip(`${escapeText(species)}<br>${escapeText(date)}`).addTo(markerCluster);

      if (record.track_scope === "global" && record.observation_date && Number.isFinite(Date.parse(record.observation_date)) && isSelectedSpecies) {
        pathRecords.push({lat, lon, date:record.observation_date});
      }
    });

    // Labels and dashed cells in the reference style, derived from displayed OBIS rows.
    const cells = new Map();
    shown.filter(record => !record.track_only).forEach(record => {
      const lat=Number(record.lat), lon=Number(record.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      const south=Math.floor(lat), west=Math.floor(lon), key=`${south}:${west}`;
      if (!cells.has(key)) cells.set(key,{south,west,records:[],lat:0,lon:0});
      const cell=cells.get(key); cell.records.push(record); cell.lat+=lat; cell.lon+=lon;
    });
    const speciesCounts=new Map();
    cells.forEach(cell=>cell.records.forEach(record=>{
      const name=String(record.species_name || "Unknown species");
      speciesCounts.set(name,(speciesCounts.get(name)||0)+1);
    }));
    const colorBySpecies=new Map([...speciesCounts.entries()].sort((a,b)=>b[1]-a[1]).map(([name],index)=>[name,SPECIES_COLORS[index%SPECIES_COLORS.length]]));
    const callouts=[];
    cells.forEach(cell=>{
      const counts=new Map();
      cell.records.forEach(record=>{ const name=String(record.species_name || "Unknown species"); counts.set(name,(counts.get(name)||0)+1); });
      const dominant=[...counts.entries()].sort((a,b)=>b[1]-a[1])[0];
      if (cell.records.length >= 2 && dominant) {
        const [species,count]=dominant;
        const color=colorBySpecies.get(species) || SPECIES_COLORS[0];
        const share=Math.round(count/cell.records.length*1000)/10;
        const center=[cell.lat/cell.records.length,cell.lon/cell.records.length];
        const bounds=[[cell.south,cell.west],[cell.south+1,cell.west+1]];
        const popup=`<strong>${escapeText(species)}</strong><div>${share}% of records in this map cell</div><div>${count} of ${cell.records.length} occurrence records</div><small>Record share is not a biomass or population estimate.</small>`;
        L.rectangle(bounds,{color,fillColor:color,fillOpacity:.07,weight:1.5,dashArray:"5 5"}).bindPopup(popup).addTo(obisLayerGroup);
      }
      counts.forEach((count,species)=>{
        const image=speciesImage(species);
        if (!image && count < 2) return;
        const points=cell.records.filter(record=>String(record.species_name || "Unknown species")===species);
        callouts.push({cell,species,count,image,points});
      });
    });
    callouts.sort((a,b)=>b.count-a.count);
    callouts.slice(0,12).forEach(({cell,species,count,image,points})=>{
      const color=colorBySpecies.get(species) || SPECIES_COLORS[0];
      const center=[points.reduce((sum,record)=>sum+Number(record.lat),0)/points.length,points.reduce((sum,record)=>sum+Number(record.lon),0)/points.length];
      const share=Math.round(count/cell.records.length*1000)/10;
      const value=count > 1 ? `${share}% CELL RECORD SHARE` : "1 OBSERVATION RECORD";
      const popup=`<strong>${escapeText(species)}</strong><div>${count} observation record${count===1?"":"s"} in this area</div><div>${share}% of records in this map cell</div><small>Observation counts do not estimate biomass or population.</small>`;
      const html=`<div class="marine-species-callout" style="--species-color:${color}"><img src="assets/organisms/${image.file}" alt="${escapeText(species)}" onerror="this.remove()"><span><i></i><b>${escapeText(species)}</b><strong>${value}</strong></span></div>`;
      const badge=L.divIcon({className:"marine-species-callout-icon",html,iconSize:[250,70],iconAnchor:[125,58]});
      L.marker(center,{icon:badge,title:`${species}: ${count} occurrence record${count===1?"":"s"}`}).bindPopup(popup).addTo(obisLayerGroup);
    });

    const totalEl = document.getElementById("obisMetricTotal");
    const taxaEl = document.getElementById("obisMetricTaxa");
    const depthEl = document.getElementById("obisMetricDepth");
    const regionalShown = shown.filter(record => !record.track_only);
    if (totalEl) totalEl.textContent = String(regionalShown.length);
    if (taxaEl) taxaEl.textContent = String(new Set(regionalShown.map(item => item.species_name)).size);
    if (depthEl) depthEl.textContent = Object.entries(depthCounts).filter(([key]) => key !== "unknown").sort((a,b) => b[1]-a[1])[0]?.[0]?.replace("_", " ") || "Unknown";

    const legend = document.getElementById("marineLivePathLegend");
    legend.innerHTML = "";
    const canDrawPaths = pathsToggle.checked && trackInfo.available;
    let drawn = 0;
    if (canDrawPaths) {
      pathRecords.sort((a,b) => Date.parse(a.date) - Date.parse(b.date));
      const distinct = pathRecords.filter((point, i, all) => !i || point.lat !== all[i-1].lat || point.lon !== all[i-1].lon);
      const maxWaypoints = 100;
      const sampled = distinct.length > maxWaypoints
        ? Array.from({length:maxWaypoints}, (_, i) => distinct[Math.round(i * (distinct.length - 1) / (maxWaypoints - 1))])
        : distinct;
      if (sampled.length >= 2) {
        const line = L.polyline(sampled.map(point => [point.lat, point.lon]), {color:PATH_COLOR, weight:2.5, opacity:.78, dashArray:"6 6", className:"marine-migration-path"});
        line.bindTooltip(`${escapeText(speciesInput.value.trim())} | ${escapeText(sampled[0].date)} to ${escapeText(sampled.at(-1).date)} | ${distinct.length} dated population observations`);
        line.addTo(obisLayerGroup);
        legend.insertAdjacentHTML("beforeend", `<span><i style="--path-color:${PATH_COLOR}"></i>${escapeText(speciesInput.value.trim())} | ${distinct.length} dated records</span>`);
        drawn = 1;
      }
    }

    const status = document.getElementById("marineLiveStatus");
    status.classList.remove("marine-live-error");
    const trackMessage = trackInfo.message ? ` ${trackInfo.message}` : "";
    const regionalCount = shown.filter(record => !record.track_only).length;
    status.textContent = `${regionalCount} regional observation${regionalCount === 1 ? "" : "s"} shown.${drawn ? " One selected-species occurrence sequence is shown; records do not identify an individual animal." : ""}${pathsToggle.checked && !trackInfo.available ? trackMessage || " Global path records are unavailable." : ""}`;
    if (!regionalShown.length) status.textContent = records.length ? "No observations fall within the selected depth." : "No marine observations matched these filters.";
    else if (pathsToggle.checked && trackInfo.available && !drawn) status.textContent += " No path available: at least two distinct dated records are needed.";
  }

  async function loadObservations() {
    const species = document.getElementById("marineLiveSpecies").value.trim();
    const region = document.getElementById("marineLiveRegion").value;
    const temporal = document.getElementById("marineLiveSeason").value;
    const status = document.getElementById("marineLiveStatus");
    const params = new URLSearchParams({region});
    if (species) params.set("species", species);
    const start = document.getElementById("marineLiveStart").value;
    const end = document.getElementById("marineLiveEnd").value;
    if (start) params.set("start_date", start);
    if (end) params.set("end_date", end);
    if (temporal === "current_month") params.set("month", String(new Date().getMonth() + 1));
    else if (temporal) params.set("season", temporal);
    const showPaths = pathsToggle.checked && hasSpeciesQuery(species);
    if (showPaths) params.set("include_global_tracks", "true");

    if (start && end && start > end) { status.textContent = "Start date must be on or before end date."; return; }
    if (pendingController) pendingController.abort();
    const requestController = new AbortController();
    pendingController = requestController;
    status.textContent = "Loading live OBIS observationsâ€¦";
    try {
      const response = await fetch(`${API_BASE}/api/marine-observations?${params}`, {signal:requestController.signal});
      const payload = await response.json();
      if (!response.ok || payload.status === "error") throw new Error(payload.message || `Observation request failed (HTTP ${response.status}).`);
      records = Array.isArray(payload.data) ? payload.data : [];
      currentTrackInfo = payload.tracks || {};
      renderRecords(currentTrackInfo);
      const mappedRecords = records.filter(record => !record.track_only && Number.isFinite(Number(record.lat)) && Number.isFinite(Number(record.lon)));
      if (mappedRecords.length) {
        const bounds = L.latLngBounds(mappedRecords.map(record => [Number(record.lat), Number(record.lon)]));
        if (bounds.isValid()) map.flyToBounds(bounds, {padding:[70,70],duration:1.1,maxZoom:6});
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      console.error("OBIS observations unavailable:", error.message);
      records = [];
      currentTrackInfo = {available:false};
      renderRecords(currentTrackInfo);
      status.textContent = `Marine observations unavailable: ${error.message}`;
      status.classList.add("marine-live-error");
    } finally { if (pendingController === requestController) pendingController = null; }
  }

  // Expose the same entry point already called by the Marine overlay toggle.
  window.fetchAndRenderOBISData = (species = "all", region = "indian_ocean") => {
    document.getElementById("marineLiveSpecies").value = species === "all" ? "" : species;
    syncPathControl();
    document.getElementById("marineLiveRegion").value = ["indian_ocean","indian_eez","global"].includes(region) ? region : "indian_ocean";
    panel.classList.add("open");
    const routePanel = document.getElementById("routePanel");
    const reasoningDrawer = document.getElementById("reasoningDrawer");
    if ((routePanel && routePanel.classList.contains("open")) || (reasoningDrawer && reasoningDrawer.classList.contains("open"))) panel.classList.remove("standalone");
    else panel.classList.add("standalone");
    if (!map.hasLayer(marineOverlay)) marineOverlay.addTo(map);
    activeOverlays.add("marine");
    document.querySelector('.mode-btn[data-mode="marine"]')?.classList.add("active");
    updateLegend("marine");
    loadObservations();
  };

  document.getElementById("marineLiveApply").addEventListener("click", loadObservations);
  document.getElementById("marineLiveReset").addEventListener("click", () => {
    document.getElementById("marineLiveSpecies").value = "";
    document.getElementById("marineLiveRegion").value = "indian_ocean";
    document.getElementById("marineLiveStart").value = "";
    document.getElementById("marineLiveEnd").value = "";
    document.getElementById("marineLiveSeason").value = "";
    document.getElementById("marineLivePaths").checked = false;
    syncPathControl();
    document.getElementById("marineLiveDepthColor").checked = true;
    document.getElementById("marineLiveDepth").value = "4000";
    document.getElementById("marineLiveDepthValue").textContent = "4,000 m";
    loadObservations();
  });
  document.getElementById("marineLiveDepthColor").addEventListener("change", () => renderRecords());
  document.getElementById("marineLiveDepth").addEventListener("input", event => {
    document.getElementById("marineLiveDepthValue").textContent = `${Number(event.target.value).toLocaleString()} m`;
    renderRecords();
  });
  pathsToggle.addEventListener("change", loadObservations);
  speciesInput.addEventListener("input", () => {
    if (pathsToggle.checked) pathsToggle.checked = false;
    syncPathControl();
    renderRecords();
  });
  document.getElementById("closeObisPanelBtn")?.addEventListener("click", () => {
    markerCluster.clearLayers();
    obisLayerGroup.clearLayers();
    records = [];
  });
})();
