"use strict";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let META = null;                 // { categories, map }
let ALL_POSTS = [];              // every recommendation loaded from the API
let map = null;
let postLayer = null;            // LayerGroup of recommendation markers
let mapPoiLayer = null;          // LayerGroup of candidate POIs browsable on the main map
let mapPoiTimer = null;          // debounce for moveend POI refresh
let selectedMarker = null;       // marker for the place being recommended

const MIN_POI_ZOOM = 15;         // below this zoom, hide the browsable POI dots
const filters = { category: null, subcategory: null, tag: null, q: "" };
let selectedPlace = null;        // { poi_id, spot_name, lat, lng, category, subcategory }
let isPicking = false;           // map-pick mode active?

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
async function init() {
  META = await fetchJSON("/api/meta");
  initMap();
  buildCategoryChips();
  buildCategorySelect();
  wireEvents();
  await loadPosts();
  showToast("Tap a dot to recommend a place, or ＋ to add your own");
}

function initMap() {
  map = L.map("map", { zoomControl: true }).setView(META.map.center, META.map.zoom);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  postLayer = L.layerGroup().addTo(map);
  mapPoiLayer = L.layerGroup().addTo(map);

  map.on("click", (e) => {
    if (isPicking) selectManualPoint(e.latlng.lat, e.latlng.lng);
  });
  map.on("moveend", scheduleMapPoiRefresh);
}

// ---------------------------------------------------------------------------
// Browsable POI dots on the main map (tap a dot to recommend that place)
// ---------------------------------------------------------------------------
function scheduleMapPoiRefresh() {
  clearTimeout(mapPoiTimer);
  mapPoiTimer = setTimeout(refreshMapPois, 250);
}

async function refreshMapPois() {
  if (!mapPoiLayer || !map.hasLayer(mapPoiLayer)) return;
  if (map.getZoom() < MIN_POI_ZOOM) { mapPoiLayer.clearLayers(); return; }
  const recommended = new Set(ALL_POSTS.map((p) => p.poi_id).filter((x) => x != null));
  try {
    const b = map.getBounds();
    const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].join(",");
    const pois = await fetchJSON("/api/pois?bbox=" + encodeURIComponent(bbox));
    mapPoiLayer.clearLayers();
    pois.forEach((poi) => {
      if (recommended.has(poi.id)) return; // already has a recommendation -> shown as a pin
      const m = L.circleMarker([poi.lat, poi.lng], {
        radius: 5, color: "#ffffff", weight: 1,
        fillColor: catColor(poi.category), fillOpacity: 0.55,
      }).bindTooltip(`${poi.name} · tap to recommend`);
      m.on("click", () => recommendFromPoi(poi));
      mapPoiLayer.addLayer(m);
    });
  } catch (e) { /* ignore transient errors */ }
}

// Open the post form pre-filled with a POI chosen from the main map.
function recommendFromPoi(poi) {
  resetPostForm();
  $("post-modal").hidden = false;
  selectPlace({
    poi_id: poi.id, spot_name: poi.name, lat: poi.lat, lng: poi.lng,
    category: poi.category, subcategory: poi.suggested_subcat || null,
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

function catColor(category) {
  return (META.categories[category] || {}).color || "#5c7cfa";
}
function catEmoji(category) {
  return (META.categories[category] || {}).emoji || "📍";
}
function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function showToast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => (t.hidden = true), 2600);
}

// ---------------------------------------------------------------------------
// Filter chips
// ---------------------------------------------------------------------------
function buildCategoryChips() {
  const row = $("category-chips");
  row.innerHTML = "";
  row.appendChild(makeChip("All", null, true));
  Object.keys(META.categories).forEach((cat) => {
    row.appendChild(makeChip(`${catEmoji(cat)} ${cat}`, cat, false, catColor(cat)));
  });
}

function makeChip(label, value, active, dotColor) {
  const el = document.createElement("button");
  el.className = "chip" + (active ? " active" : "");
  el.type = "button";
  el.dataset.value = value === null ? "" : value;
  if (dotColor) {
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.background = dotColor;
    el.appendChild(dot);
  }
  el.appendChild(document.createTextNode(label));
  el.addEventListener("click", () => onCategoryChip(value, el));
  return el;
}

function onCategoryChip(value, el) {
  filters.category = value;
  filters.subcategory = null;
  document.querySelectorAll("#category-chips .chip").forEach((c) => c.classList.remove("active"));
  el.classList.add("active");
  buildSubcategoryChips(value);
  applyFilters();
}

function buildSubcategoryChips(category) {
  const row = $("subcategory-chips");
  const subs = category ? (META.categories[category].subcategories || []) : [];
  if (subs.length === 0) {
    row.hidden = true;
    row.innerHTML = "";
    return;
  }
  row.innerHTML = "";
  const all = document.createElement("button");
  all.className = "chip active";
  all.type = "button";
  all.textContent = "All";
  all.addEventListener("click", () => onSubChip(null, all));
  row.appendChild(all);
  subs.forEach((sub) => {
    const el = document.createElement("button");
    el.className = "chip";
    el.type = "button";
    el.textContent = sub;
    el.addEventListener("click", () => onSubChip(sub, el));
    row.appendChild(el);
  });
  row.hidden = false;
}

function onSubChip(value, el) {
  filters.subcategory = value;
  document.querySelectorAll("#subcategory-chips .chip").forEach((c) => c.classList.remove("active"));
  el.classList.add("active");
  applyFilters();
}

// ---------------------------------------------------------------------------
// Posts: load, filter, render
// ---------------------------------------------------------------------------
async function loadPosts() {
  ALL_POSTS = await fetchJSON("/api/posts");
  applyFilters();
  refreshMapPois();
}

function getFiltered() {
  const q = filters.q.trim().toLowerCase();
  return ALL_POSTS.filter((p) => {
    if (filters.category && p.category !== filters.category) return false;
    if (filters.subcategory && p.subcategory !== filters.subcategory) return false;
    if (filters.tag) {
      const tags = (p.tags || []).map((t) => t.toLowerCase());
      if (!tags.includes(filters.tag.toLowerCase())) return false;
    }
    if (q) {
      const hay = [p.spot_name, p.comment, p.author, (p.tags || []).join(" ")]
        .join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function applyFilters() {
  const posts = getFiltered();
  postLayer.clearLayers();
  posts.forEach((p) => postLayer.addLayer(makePostMarker(p)));
}

function makePostMarker(post) {
  const color = catColor(post.category);
  const icon = L.divIcon({
    className: "",
    html: `<div class="pin" style="background:${color}"><span>${catEmoji(post.category)}</span></div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 30],
  });
  const marker = L.marker([post.lat, post.lng], { icon });
  marker.on("click", () => openDetail(post));
  return marker;
}

// ---------------------------------------------------------------------------
// Detail sheet
// ---------------------------------------------------------------------------
function openDetail(post) {
  const color = catColor(post.category);
  const sub = post.subcategory ? ` · ${escapeHTML(post.subcategory)}` : "";
  const date = new Date(post.created_at);
  const when = isNaN(date) ? "" : date.toLocaleDateString();
  const tags = (post.tags || [])
    .map((t) => `<span class="tag-chip" data-tag="${escapeHTML(t)}">#${escapeHTML(t)}</span>`)
    .join("");

  $("detail-body").innerHTML = `
    <div class="detail-title">${catEmoji(post.category)} ${escapeHTML(post.spot_name)}</div>
    <div class="detail-meta">
      <span class="detail-badge" style="background:${color}">${escapeHTML(post.category)}${sub}</span>
      by <strong>${escapeHTML(post.author)}</strong>${when ? " · " + when : ""}
    </div>
    ${post.comment ? `<div class="detail-comment">${escapeHTML(post.comment)}</div>` : ""}
    <div class="detail-tags">${tags}</div>
  `;
  $("detail-body").querySelectorAll(".tag-chip").forEach((c) => {
    c.addEventListener("click", () => {
      filters.tag = c.dataset.tag;
      $("search").value = "";
      filters.q = "";
      applyFilters();
      closeDetail();
      showToast(`Filtering by #${c.dataset.tag}`);
    });
  });
  $("detail").hidden = false;
}
function closeDetail() { $("detail").hidden = true; }

// ---------------------------------------------------------------------------
// Posting flow
// ---------------------------------------------------------------------------
function openPostModal() {
  resetPostForm();
  $("post-modal").hidden = false;
}
function closePostModal() {
  $("post-modal").hidden = true;
  exitPickMode();
}

function resetPostForm() {
  selectedPlace = null;
  $("step-find").hidden = false;
  $("step-details").hidden = true;
  $("poi-search").value = "";
  $("poi-results").innerHTML = "";
  $("post-form").reset();
  if (selectedMarker) { map.removeLayer(selectedMarker); selectedMarker = null; }
}

// --- POI search ---
let poiSearchTimer = null;
function onPoiSearch() {
  clearTimeout(poiSearchTimer);
  const q = $("poi-search").value.trim();
  poiSearchTimer = setTimeout(async () => {
    if (q.length < 1) { $("poi-results").innerHTML = ""; return; }
    try {
      const pois = await fetchJSON("/api/pois?q=" + encodeURIComponent(q));
      renderPoiResults(pois);
    } catch (e) { /* ignore transient errors */ }
  }, 220);
}

function renderPoiResults(pois) {
  const ul = $("poi-results");
  ul.innerHTML = "";
  if (pois.length === 0) {
    const li = document.createElement("li");
    li.className = "poi-empty";
    li.textContent = "No matches. Try “Pick on map”.";
    ul.appendChild(li);
    return;
  }
  pois.slice(0, 30).forEach((poi) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="poi-cat" style="background:${catColor(poi.category)}"></span>
      <span>${escapeHTML(poi.name)}<br><small style="color:#6b7280">${escapeHTML(poi.category)}</small></span>`;
    li.addEventListener("click", () => selectPlace({
      poi_id: poi.id,
      spot_name: poi.name,
      lat: poi.lat,
      lng: poi.lng,
      category: poi.category,
      subcategory: poi.suggested_subcat || null,
    }));
    ul.appendChild(li);
  });
}

// --- pick on map ---
// POI dots are already on the main map, so pick mode just lets the user tap a
// dot (handled by recommendFromPoi) or anywhere on the map for an unlisted spot.
function enterPickMode() {
  isPicking = true;
  $("post-modal").hidden = true;
  $("pick-banner").hidden = false;
}
function exitPickMode() {
  isPicking = false;
  $("pick-banner").hidden = true;
}
function reopenModalAfterPick() {
  exitPickMode();
  $("post-modal").hidden = false;
}

function selectManualPoint(lat, lng) {
  selectPlace({
    poi_id: null, spot_name: "", lat, lng,
    category: "Other", subcategory: null,
  });
}

// --- use current location ---
function useMyLocation() {
  if (!navigator.geolocation) { showToast("Geolocation not available"); return; }
  showToast("Locating…");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      map.setView([pos.coords.latitude, pos.coords.longitude], 17);
      selectManualPoint(pos.coords.latitude, pos.coords.longitude);
    },
    () => showToast("Could not get your location"),
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

// --- a place has been chosen ---
function selectPlace(place) {
  selectedPlace = place;
  if (isPicking) reopenModalAfterPick();

  $("step-find").hidden = true;
  $("step-details").hidden = false;
  $("f-spotname").value = place.spot_name || "";
  $("sel-coords").textContent = `Lat ${place.lat.toFixed(5)}, Lng ${place.lng.toFixed(5)}`;
  $("f-category").value = place.category;
  syncSubcategory();
  if (place.subcategory) $("f-subcategory").value = place.subcategory;

  if (selectedMarker) map.removeLayer(selectedMarker);
  selectedMarker = L.marker([place.lat, place.lng], { opacity: 0.9 }).addTo(map);
  map.setView([place.lat, place.lng], Math.max(map.getZoom(), 16));
}

// --- category/subcategory selects ---
function buildCategorySelect() {
  const sel = $("f-category");
  sel.innerHTML = "";
  Object.keys(META.categories).forEach((cat) => {
    const opt = document.createElement("option");
    opt.value = cat;
    opt.textContent = `${catEmoji(cat)} ${cat}`;
    sel.appendChild(opt);
  });
  sel.addEventListener("change", syncSubcategory);
}

function syncSubcategory() {
  const cat = $("f-category").value;
  const subs = (META.categories[cat] || {}).subcategories || [];
  const sel = $("f-subcategory");
  const wrap = $("subcat-wrap");
  if (subs.length === 0) {
    wrap.hidden = true;
    sel.innerHTML = "";
    return;
  }
  sel.innerHTML = '<option value="">— optional —</option>';
  subs.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    sel.appendChild(opt);
  });
  wrap.hidden = false;
}

// --- submit ---
async function submitPost(e) {
  e.preventDefault();
  if (!selectedPlace) { showToast("Choose a place first"); return; }
  const spotName = $("f-spotname").value.trim();
  const author = $("f-author").value.trim();
  if (!spotName) { showToast("Place name is required"); return; }
  if (!author) { showToast("Your name is required"); return; }

  const payload = {
    poi_id: selectedPlace.poi_id,
    spot_name: spotName,
    lat: selectedPlace.lat,
    lng: selectedPlace.lng,
    category: $("f-category").value,
    subcategory: $("subcat-wrap").hidden ? null : ($("f-subcategory").value || null),
    author: author,
    tags: $("f-tags").value,
    comment: $("f-comment").value,
  };

  try {
    const created = await fetchJSON("/api/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    ALL_POSTS.unshift(created);
    applyFilters();
    refreshMapPois();   // the recommended POI becomes a pin, so drop its dot
    closePostModal();
    showToast("Thanks! Your recommendation is on the map 🎉");
    openDetail(created);
  } catch (err) {
    showToast("Could not post: " + err.message);
  }
}

// ---------------------------------------------------------------------------
// Event wiring
// ---------------------------------------------------------------------------
function wireEvents() {
  $("search").addEventListener("input", (e) => {
    filters.q = e.target.value;
    filters.tag = null; // a free-text search clears an active tag filter
    applyFilters();
  });

  $("fab").addEventListener("click", openPostModal);
  $("post-close").addEventListener("click", closePostModal);
  $("detail-close").addEventListener("click", closeDetail);

  $("poi-search").addEventListener("input", onPoiSearch);
  $("pick-on-map").addEventListener("click", enterPickMode);
  $("pick-cancel").addEventListener("click", () => { exitPickMode(); $("post-modal").hidden = false; });
  $("use-location").addEventListener("click", useMyLocation);
  $("change-place").addEventListener("click", resetPostForm);
  $("post-form").addEventListener("submit", submitPost);

  // tap the dimmed backdrop to close the modal
  $("post-modal").addEventListener("click", (e) => {
    if (e.target.id === "post-modal") closePostModal();
  });
}

init();
