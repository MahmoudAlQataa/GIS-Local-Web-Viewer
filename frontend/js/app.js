/* =========================================================
   GIS Local Web Viewer — Frontend Logic
   ========================================================= */

const state = {
    map: null,
    layers: {},        // id -> { leafletLayer, name, color, visible, type, rawFeatures, link }
    layerCounter: 0,
};

/* ---------- Linking helpers ---------- */
function getLayerColumns(id) {
    const layer = state.layers[id];
    if (!layer) return [];
    return layer.rawFeatures && layer.rawFeatures.length
        ? Object.keys(layer.rawFeatures[0].properties)
        : [];
}

function getCommonColumns(idA, idB) {
    const a = new Set(getLayerColumns(idA));
    const b = getLayerColumns(idB);
    return b.filter((col) => a.has(col));
}

function autoDetectLink(tableLayerId) {
    const spatialIds = Object.keys(state.layers).filter((id) => state.layers[id].type !== "table" && id !== tableLayerId);
    for (const targetId of spatialIds) {
        const common = getCommonColumns(tableLayerId, targetId);
        if (common.length >= 1) {
            return { targetLayerId: targetId, column: common[0] };
        }
    }
    return null;
}

function findLinkedSpatialFeature(tableLayerId, personProperties) {
    const link = state.layers[tableLayerId].link;
    if (!link || !link.targetLayerId || !link.column) return null;
    const targetLayer = state.layers[link.targetLayerId];
    if (!targetLayer) return null;
    const value = personProperties[link.column];
    if (value === undefined || value === null) return null;

    const match = targetLayer.features.find(
        (f) => f.properties && String(f.properties[link.column]) === String(value)
    );
    return match ? match.leafletLayer : null;
}

const PALETTE = ["#134e45", "#774a07", "#af2010", "#095a9c", "#4710a0", "#07831b"];

function enableSearchInputs() {
    ["search-general", "search-name", "search-id", "search-camp", "search-family"].forEach((id) => {
        document.getElementById(id).disabled = false;
    });
}

/* ---------- Map init ---------- */
async function initMap() {
    state.map = L.map("map", {
        center: [31.5, 34.46], // مركز منطقة التغطية (غزة)
        zoom: 13,
        zoomControl: true,
        attributionControl: true,
    });

    // كل الطبقات (basemaps) أوفلاين بالكامل، بتنكشف تلقائياً من raster_data/
    await loadRasterLayers();

    state.map.on("mousemove", (e) => {
        document.getElementById("coord-lat").textContent = e.latlng.lat.toFixed(5);
        document.getElementById("coord-lng").textContent = e.latlng.lng.toFixed(5);
    });

    state.map.on("mouseout", () => {
        document.getElementById("coord-lat").textContent = "—";
        document.getElementById("coord-lng").textContent = "—";
    });

    state.map.on("zoomend", () => {
        document.getElementById("coord-zoom").textContent = state.map.getZoom();
    });

    document.getElementById("coord-zoom").textContent = state.map.getZoom();
}

/* ---------- Raster (basemap) layers: auto-discovery from raster_data/ ---------- */
let rasterLayersControl = null; // نگرال بالمرجع عشان نقدر نحدّثه لاحقاً لو احتجنا

async function loadRasterLayers() {
    let layersInfo = [];
    try {
        const res = await fetch("/raster-layers");
        layersInfo = await res.json();
    } catch (err) {
        console.error("فشل تحميل طبقات الخريطة (raster-layers):", err);
    }

    if (!layersInfo || layersInfo.length === 0) {
        console.warn("ما في أي طبقة خريطة (raster) موجودة بمجلد raster_data/");
        return;
    }

    const baseLayers = {};
    layersInfo.forEach((layer, index) => {
        const tileLayer = L.tileLayer(layer.url_template, {
            minZoom: 12,
            maxZoom: 17,
            tms: false, // QTiles صدرت XYZ عادي (مش TMS)
            attribution: layer.name,
        });

        baseLayers[layer.name] = tileLayer;

        if (index === 0) {
            tileLayer.addTo(state.map); // أول طبقة مكتشفة = الافتراضية عند التحميل
        }
    });

    rasterLayersControl = L.control.layers(baseLayers, null, { collapsed: false }).addTo(state.map);
}

/* ---------- Upload handling ---------- */
function setupUpload() {
    const input = document.getElementById("file-input");
    const status = document.getElementById("upload-status");

    input.addEventListener("change", async () => {
        const file = input.files[0];
        if (!file) return;

        status.textContent = "Uploading…";
        status.style.color = "var(--muted)";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/upload", { method: "POST", body: formData });
            const data = await res.json();

            if (!data.success) {
                status.textContent = data.error || "Upload failed.";
                status.style.color = "#c97064";
                return;
            }

            addLayer(data.layer);
            status.textContent = `Loaded "${data.layer.name}"`;
            status.style.color = "var(--accent-strong)";
        } catch (err) {
            status.textContent = "Network error — is the server running?";
            status.style.color = "#c97064";
        } finally {
            input.value = "";
        }
    });
}

/* ---------- Layer management ---------- */
function addLayer(layerModel) {
    const id = `layer-${state.layerCounter++}`;
    const color = PALETTE[state.layerCounter % PALETTE.length];
    const layerType = layerModel.type || "spatial";

    if (layerType === "table") {
        addTableLayer(id, color, layerModel);
        return;
    }

    const validFeatures = layerModel.features.filter((f) => isValidGeometry(f.geometry));
    const skippedCount = layerModel.features.length - validFeatures.length;

    const featureCollection = {
        type: "FeatureCollection",
        features: validFeatures.map((f) => ({
            type: "Feature",
            geometry: f.geometry,
            properties: f.properties,
        })),
    };

    const featureRefs = [];

    const leafletLayer = L.geoJSON(featureCollection, {
        style: () => ({ color, weight: 2, fillColor: color, fillOpacity: 0.25 }),
        pointToLayer: (feature, latlng) =>
            L.circleMarker(latlng, { radius: 6, color, weight: 2, fillColor: color, fillOpacity: 0.6 }),
        onEachFeature: (feature, layer) => {
            layer.bindPopup(buildPopupHTML(feature.properties));
            const props = feature.properties || {};
            const label = props.name || props.Name || Object.values(props)[0] || "(unnamed)";
            featureRefs.push({ name: label, leafletLayer: layer, properties: props });
        },
    }).addTo(state.map);

    state.layers[id] = {
        leafletLayer,
        name: layerModel.name,
        color,
        visible: true,
        features: featureRefs,
        rawFeatures: validFeatures, // [{geometry, properties}] — used by getLayerColumns/autoDetectLink
    };

    if (leafletLayer.getLayers().length === 0) {
        console.warn(`Layer "${layerModel.name}" has no valid features to display.`);
    } else {
        try {
            const bounds = leafletLayer.getBounds();
            const sw = bounds.getSouthWest();
            const ne = bounds.getNorthEast();
            const boundsAreFinite =
                bounds.isValid() &&
                Number.isFinite(sw.lat) && Number.isFinite(sw.lng) &&
                Number.isFinite(ne.lat) && Number.isFinite(ne.lng);

            if (boundsAreFinite) {
                state.map.fitBounds(bounds, { padding: [30, 30], maxZoom: 17 });
            } else {
                console.warn(`Layer "${layerModel.name}" produced invalid bounds — skipped fitBounds.`, bounds);
            }
        } catch (err) {
            console.error("fitBounds failed:", err);
        }
    }

    renderLayersList();
    enableSearchInputs();

    if (skippedCount > 0) {
        const status = document.getElementById("upload-status");
        status.textContent = `Loaded "${layerModel.name}" (${skippedCount} feature(s) skipped — no geometry)`;
        status.style.color = "var(--highlight)";
    }
}

function addTableLayer(id, color, layerModel) {
    state.layers[id] = {
        leafletLayer: null,
        name: layerModel.name,
        color,
        visible: true,
        type: "table",
        rawFeatures: layerModel.features, // [{geometry:null, properties:{...}}]
        link: null,
        fieldMap: { personName: null, personId: null, campName: null },
    };

    const detected = autoDetectLink(id);
    if (detected) {
        state.layers[id].link = detected;
    }

    state.layers[id].fieldMap = autoDetectFieldMap(id);

    renderLayersList();
    enableSearchInputs();
    runSearch();
}

/* ---------- Field mapping helpers (per-layer, not persisted yet) ---------- */
function autoDetectFieldMap(tableLayerId) {
    const columns = getLayerColumns(tableLayerId);
    const guess = (keywords) =>
        columns.find((col) => keywords.some((kw) => col.includes(kw))) || null;

    return {
        personId: guess(["هوي", "id", "ID"]),
        personName: guess(["اسم__", "الاسم", "اسم_شخص", "اسم_ال"]) || null,
        campName: guess(["اسم_ا", "مخيم", "camp"]) || null,
    };
}

function isValidGeometry(geometry) {
    if (!geometry || !geometry.coordinates) return false;

    const checkCoords = (coords) => {
        if (typeof coords[0] === "number") {
            return coords.every((n) => typeof n === "number" && Number.isFinite(n));
        }
        return coords.every(checkCoords);
    };

    try {
        return checkCoords(geometry.coordinates);
    } catch {
        return false;
    }
}

function buildPopupHTML(properties) {
    const rows = Object.entries(properties)
        .map(([k, v]) => `<tr><td class="popup-key">${k}</td><td>${v ?? "—"}</td></tr>`)
        .join("");
    return `<table class="popup-table">${rows}</table>`;
}

function renderLayersList() {
    const list = document.getElementById("layers-list");
    const ids = Object.keys(state.layers);

    if (ids.length === 0) {
        list.innerHTML = `<li class="empty-state">No layers loaded yet.</li>`;
        return;
    }

    list.innerHTML = ids
        .map((id) => {
            const layer = state.layers[id];
            const linkControls = layer.type === "table" ? buildLinkControlsHTML(id) : "";
            const fieldMapControls = layer.type === "table" ? buildFieldMapControlsHTML(id) : "";
            return `
        <li data-id="${id}">
          <label class="layer-row">
            <input type="checkbox" ${layer.visible ? "checked" : ""} data-action="toggle" data-id="${id}">
            <span class="layer-swatch" style="background:${layer.color}"></span>
            <span class="layer-name">${layer.name}</span>
          </label>
          ${linkControls}
          ${fieldMapControls}
        </li>`;
        })
        .join("");

    list.querySelectorAll('[data-action="toggle"]').forEach((el) => {
        el.addEventListener("change", (e) => toggleLayer(e.target.dataset.id, e.target.checked));
    });

    list.querySelectorAll(".layer-name").forEach((el) => {
        el.addEventListener("click", () => {
            const id = el.closest("li").dataset.id;
            const layer = state.layers[id];
            if (layer.type === "table" || !layer.leafletLayer) return;
            state.map.fitBounds(layer.leafletLayer.getBounds(), { padding: [30, 30] });
        });
    });

    list.querySelectorAll('[data-action="link-target"]').forEach((el) => {
        el.addEventListener("change", (e) => {
            const id = e.target.dataset.id;
            const targetLayerId = e.target.value || null;
            const currentCol = state.layers[id].link ? state.layers[id].link.column : null;
            state.layers[id].link = targetLayerId ? { targetLayerId, column: currentCol } : null;
            renderLayersList();
        });
    });

    list.querySelectorAll('[data-action="link-column"]').forEach((el) => {
        el.addEventListener("change", (e) => {
            const id = e.target.dataset.id;
            if (state.layers[id].link) {
                state.layers[id].link.column = e.target.value || null;
            }
        });
    });

    list.querySelectorAll('[data-action="field-map"]').forEach((el) => {
        el.addEventListener("change", (e) => {
            const id = e.target.dataset.id;
            const field = e.target.dataset.field;
            if (!state.layers[id].fieldMap) {
                state.layers[id].fieldMap = { personName: null, personId: null, campName: null };
            }
            state.layers[id].fieldMap[field] = e.target.value || null;
            runSearch();
        });
    });
}
function buildFieldMapControlsHTML(tableLayerId) {
    const layer = state.layers[tableLayerId];
    const columns = getLayerColumns(tableLayerId);
    const fm = layer.fieldMap || { personName: null, personId: null, campName: null };

    const optionsFor = (selected) =>
        `<option value="">— اختر عمود —</option>` +
        columns.map((col) => `<option value="${col}" ${selected === col ? "selected" : ""}>${col}</option>`).join("");

    return `
      <div class="field-map-controls">
        <label class="field-map-row">
          <span>اسم الشخص</span>
          <select class="link-select" data-action="field-map" data-field="personName" data-id="${tableLayerId}">
            ${optionsFor(fm.personName)}
          </select>
        </label>
        <label class="field-map-row">
          <span>رقم الهوية</span>
          <select class="link-select" data-action="field-map" data-field="personId" data-id="${tableLayerId}">
            ${optionsFor(fm.personId)}
          </select>
        </label>
        <label class="field-map-row">
          <span>اسم المخيم</span>
          <select class="link-select" data-action="field-map" data-field="campName" data-id="${tableLayerId}">
            ${optionsFor(fm.campName)}
          </select>
        </label>
      </div>`;
}

function buildLinkControlsHTML(tableLayerId) {
    const layer = state.layers[tableLayerId];
    const spatialIds = Object.keys(state.layers).filter(
        (id) => id !== tableLayerId && state.layers[id].type !== "table"
    );

    if (spatialIds.length === 0) {
        return `<div class="link-controls empty-state">No spatial layer to link with yet.</div>`;
    }

    const targetOptions = spatialIds
        .map((id) => `<option value="${id}" ${layer.link && layer.link.targetLayerId === id ? "selected" : ""}>${state.layers[id].name}</option>`)
        .join("");

    const columns = layer.link ? getLayerColumns(tableLayerId) : [];
    const columnOptions = columns
        .map((col) => `<option value="${col}" ${layer.link && layer.link.column === col ? "selected" : ""}>${col}</option>`)
        .join("");

    return `
        <div class="link-controls">
            <select class="link-select" data-action="link-target" data-id="${tableLayerId}">
                <option value="">— اربط مع لاير —</option>
                ${targetOptions}
            </select>
        ${layer.link ? `
        <select class="link-select" data-action="link-column" data-id="${tableLayerId}">
          <option value="">— عمود الربط —</option>
          ${columnOptions}
        </select>` : ""
        }
      </div>`;
}


/* ---------- Query panel (linked table records) ---------- */
function openQueryPanel(properties, tableLayerId, options = {}) {
    const { openPopup = true } = options;
    const panel = document.getElementById("query-panel");
    const body = document.getElementById("query-panel-body");

    const rows = Object.entries(properties)
        .map(([k, v]) => `<tr><td class="popup-key">${k}</td><td>${v ?? "—"}</td></tr>`)
        .join("");
    body.innerHTML = `<table class="popup-table">${rows}</table>`;
    panel.classList.add("open");

    const spatialTarget = findLinkedSpatialFeature(tableLayerId, properties);
    if (spatialTarget) {
        if (spatialTarget.getBounds) {
            state.map.fitBounds(spatialTarget.getBounds(), { padding: [40, 40], maxZoom: 17 });
        } else if (spatialTarget.getLatLng) {
            state.map.setView(spatialTarget.getLatLng(), 17);
        }
        if (openPopup) spatialTarget.openPopup();
    }
}

function closeQueryPanel() {
    document.getElementById("query-panel").classList.remove("open");
}

function toggleLayer(id, visible) {
    const layer = state.layers[id];
    layer.visible = visible;
    if (visible) {
        layer.leafletLayer.addTo(state.map);
    } else {
        state.map.removeLayer(layer.leafletLayer);
    }
}

/* ---------- Search (person search across all table layers) ---------- */
function getTablePersonLayers() {
    return Object.entries(state.layers).filter(([, layer]) => layer.type === "table" && layer.fieldMap);
}

function runSearch() {
    const nameTerm = document.getElementById("search-name").value.trim().toLowerCase();
    const idTerm = document.getElementById("search-id").value.trim().toLowerCase();
    const campTerm = document.getElementById("search-camp").value.trim().toLowerCase();
    const familyTerm = document.getElementById("search-family").value.trim().toLowerCase();

    const resultsList = document.getElementById("search-results");

    if (!nameTerm && !idTerm && !campTerm && !familyTerm) {
        resultsList.innerHTML = `<li class="empty-state">اكتب للبحث…</li>`;
        return;
    }

    const results = [];

    getTablePersonLayers().forEach(([layerId, layer]) => {
        const { personName, personId, campName } = layer.fieldMap;
        layer.rawFeatures.forEach((f) => {
            const props = f.properties;

            if (nameTerm && !(personName && String(props[personName] ?? "").toLowerCase().includes(nameTerm))) return;
            if (idTerm && !(personId && String(props[personId] ?? "").toLowerCase().includes(idTerm))) return;
            if (campTerm && !(campName && String(props[campName] ?? "").toLowerCase().includes(campTerm))) return;
            if (familyTerm) {
                const fullName = personName ? String(props[personName] ?? "").trim().toLowerCase() : "";
                const parts = fullName.split(/\s+/).filter(Boolean);
                const lastWord = parts.length ? parts[parts.length - 1] : "";
                if (!lastWord.includes(familyTerm)) return;
            }

            const label = (personName && props[personName]) || Object.values(props)[0] || "(unnamed)";
            results.push({ layerId, properties: props, label });
        });
    });

    if (results.length === 0) {
        resultsList.innerHTML = `<li class="empty-state">لا توجد نتائج.</li>`;
        return;
    }

    resultsList.innerHTML = results
        .map((r, i) => `<li data-result-index="${i}">${r.label}</li>`)
        .join("");

    resultsList.querySelectorAll("li[data-result-index]").forEach((el) => {
        el.addEventListener("click", () => {
            const idx = Number(el.dataset.resultIndex);
            const r = results[idx];
            openQueryPanel(r.properties, r.layerId, { openPopup: false });
        });
    });
}

function resetGeneralSearchStyles() {
    Object.values(state.layers).forEach((layer) => {
        if (layer.type === "table" || !layer.leafletLayer) return;
        layer.leafletLayer.eachLayer((sub) => {
            if (sub.setStyle) {
                sub.setStyle({
                    color: layer.color,
                    weight: 2,
                    fillColor: layer.color,
                    fillOpacity: sub.feature.geometry.type === "Point" ? 0.6 : 0.25,
                });
            }
            if (sub.setRadius) sub.setRadius(6);
        });
    });
}

function runGeneralSearch(term) {
    resetGeneralSearchStyles();
    if (!term) return;

    const matches = [];
    Object.values(state.layers).forEach((layer) => {
        if (layer.type === "table" || !layer.leafletLayer) return;
        layer.leafletLayer.eachLayer((sub) => {
            const props = sub.feature.properties || {};
            const isMatch = Object.values(props).some((v) => String(v).toLowerCase().includes(term));
            if (isMatch) matches.push(sub);
        });
    });

    if (matches.length === 0) return;

    matches.forEach((sub) => {
        if (sub.setStyle) {
            sub.setStyle({ color: "#ffffff", weight: 3, fillColor: "#ffffff", fillOpacity: 0.9 });
        }
        if (sub.setRadius) sub.setRadius(8);
        sub.bringToFront && sub.bringToFront();
    });

    const first = matches[0];
    if (first.getBounds) {
        state.map.fitBounds(first.getBounds(), { padding: [40, 40], maxZoom: 17 });
    } else if (first.getLatLng) {
        state.map.setView(first.getLatLng(), 17);
    }
    first.openPopup();
}

function setupSearch() {
    const generalInput = document.getElementById("search-general");
    generalInput.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        runGeneralSearch(generalInput.value.trim().toLowerCase());
    });

    ["search-name", "search-id", "search-camp", "search-family"].forEach((id) => {
        document.getElementById(id).addEventListener("input", runSearch);
    });
}

function showLayerLoadError(layerName, errorMessage) {
    let container = document.getElementById("layer-error-banner");
    if (!container) {
        container = document.createElement("div");
        container.id = "layer-error-banner";
        container.style.cssText =
            "position:fixed;top:10px;right:10px;z-index:9999;" +
            "width:360px;max-width:calc(100vw - 20px);box-sizing:border-box;" +
            "background:#fdecea;border:1px solid #f44336;" +
            "border-radius:6px;padding:8px 12px;font-size:13px;" +
            "color:#611a15;box-shadow:0 2px 6px rgba(0,0,0,0.15);";
        document.body.appendChild(container);
    }
    const line = document.createElement("div");
    line.style.cssText =
        "margin-top:4px;display:flex;justify-content:space-between;align-items:flex-start;" +
        "gap:8px;width:100%;box-sizing:border-box;";

    const text = document.createElement("span");
    text.textContent = `⚠ ${layerName}: ${errorMessage} `;
    text.style.cssText =
        "flex:1;min-width:0;word-break:break-word;overflow-wrap:break-word;";

    const closeBtn = document.createElement("span");
    closeBtn.textContent = "×";
    closeBtn.style.cssText =
        "cursor:pointer;font-weight:bold;font-size:18px;line-height:1;" +
        "flex-shrink:0;color:#611a15;direction:ltr;width:20px;height:20px;" +
        "display:flex;align-items:center;justify-content:center;" +
        "border-radius:50%;background:rgba(97,26,21,0.1);";
    closeBtn.onmouseenter = () => closeBtn.style.background = "rgba(97,26,21,0.2)";
    closeBtn.onmouseleave = () => closeBtn.style.background = "rgba(97,26,21,0.1)";
    closeBtn.onclick = () => {
        line.remove();
        if (container.children.length === 0) container.remove();
    };

    line.appendChild(text);
    line.appendChild(closeBtn);
    container.appendChild(line);
}

async function loadDataLayers() {
    try {
        const res = await fetch("/data-layers");
        const layers = await res.json();
        layers.forEach((layerModel) => {
            if (layerModel.error) {
                console.error(`Layer '${layerModel.name}' failed: `, layerModel.error);
                showLayerLoadError(layerModel.name, layerModel.error);
            } else {
                addLayer(layerModel);
            }
        });
    } catch (err) {
        console.error("Failed to load data layers:", err);
    }
}
/* ---------- Bootstrap ---------- */
window.addEventListener("DOMContentLoaded", () => {
    initMap();
    setupUpload();
    setupSearch();
    loadDataLayers();

    const closeBtn = document.getElementById("query-panel-close");
    if (closeBtn) closeBtn.addEventListener("click", closeQueryPanel);
});