// Colorado Hunting Map — CPW GIS layers + per-GMU big-game stats.
// Extracted from templates/pages/maps.html.
// Requires: Leaflet (L), and the page to carry the MapTiler key + stats URL
// as data attributes on the #map element.

// Colorado Parks & Wildlife admin boundaries FeatureServer (cpw-config.js).
// Layer ids used by the app: 5 public-access, 6 GMU, 22 deer DAU, 23 elk DAU.

const layers = {
  gmu: {
    id: 6,
    name: "Big-game GMU",
    color: "#d946ef",
    opacity: 0.04,
  },
  public: {
    id: 5,
    name: "CPW public-access property",
    color: "#16a34a",
    opacity: 0.25,
  },
  wia: {
    id: 12,
    name: "Walk-In Access",
    color: "#f59e0b",
    opacity: 0.24,
  },
  elk: {
    id: 23,
    name: "Elk DAU",
    isLine: true,
    color: "#dc2626",
  },
  deer: {
    id: 22,
    name: "Deer DAU",
    isLine: true,
    color: "#2563eb",
  },
};

const SEX_M = { elk: "bull", deer: "buck", pronghorn: "buck", bear: "boar" };
const SEX_F = { elk: "cow", deer: "doe", pronghorn: "doe", bear: "sow" };

let map;
let SPECIES_STATS = null;
const geoLayers = {};
const loading = {};

async function loadLayer(key) {
  if (geoLayers[key]) return;
  if (loading[key]) return loading[key];

  loading[key] = (async () => {
    const cfg = layers[key];
    const params = new URLSearchParams({
      where: "1=1",
      outFields: "*",
      outSR: "4326",
      returnGeometry: "true",
      f: "geojson",
    });

    const url = `${window.CPW_FEATURESERVER}/${cfg.id}/query?${params}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const geojson = await response.json();
    if (geojson.error) {
      throw new Error(geojson.error.message || "CPW service error");
    }
    if (!geojson.features) {
      throw new Error("The service returned no GeoJSON features.");
    }

    const dataLayer = L.geoJSON(geojson, {
      // DAU layers are boundary LINE features, not polygons — fill styling
      // is ignored on polylines, so they must be drawn as visible lines.
      style: () => layerStyle(cfg, key),
    }).addTo(map);

    dataLayer.eachLayer((layer) => {
      layer.on("click", (event) => {
        const props = layer.feature.properties || {};

        const title = `${cfg.name} — ${
          Object.entries(props).find(
            ([k, v]) =>
              /GMUID|ELKDAU|DEERDAU|PROPNAME|NAME/i.test(k) &&
              v !== null &&
              v !== "",
          )?.[1] ?? "Feature details"
        }`;

        const box = el("div");
        box.appendChild(el("strong", null, title));

        // Curated fields instead of dumping the raw record: hide GIS
        // housekeeping (FID, dates, acres) and render epoch-ms dates readably.
        const LABELS = {
          COUNTY: "Counties",
          DEERDAU: "Deer DAU",
          ELKDAU: "Elk DAU",
          ANTDAU: "Pronghorn DAU",
          MOOSEDAU: "Moose DAU",
          BEARDAU: "Bear DAU",
          LIONDAU: "Lion region",
        };
        const shown = new Set();
        for (const [rawKey, label] of Object.entries(LABELS)) {
          const entry = Object.entries(props).find(
            ([k, v]) =>
              k.toUpperCase() === rawKey && v !== null && v !== "",
          );
          if (entry) {
            shown.add(entry[0].toUpperCase());
            box.appendChild(el("div", null, `${label}: ${entry[1]}`));
          }
        }

        // Fallback for layers without curated fields (public access, DAU
        // lines): show the first few non-housekeeping properties.
        if (!shown.size) {
          const HIDE = /^(FID|OBJECTID|.*DATE.*|.*_DATE|AcresGISCa|SHAPE.*)$/i;
          Object.entries(props)
            .filter(([k]) => !HIDE.test(k))
            .slice(0, 8)
            .forEach(([k, v]) => {
              box.appendChild(
                el("div", null, `${k}: ${fmtValue(k, v)}`),
              );
            });
        }

        // Acres from the GIS field, formatted; shown for polygons only.
        if (!cfg.isLine) {
          const acres = Object.entries(props).find(
            ([k]) => k.toUpperCase() === "ACRESGISCA",
          )?.[1];
          if (typeof acres === "number" && acres > 0) {
            box.appendChild(
              el(
                "div",
                null,
                `Area: ${Math.round(acres).toLocaleString()} acres ` +
                  `(~${Math.round(acres / 640)} sq mi)`,
              ),
            );
          }
        }

        // Last boundary edit, human-readable instead of epoch milliseconds.
        const editTs = Object.entries(props).find(([k]) =>
          /^EDIT_DATE$/i.test(k),
        )?.[1];
        const edited = fmtMsDate(editTs);
        if (edited) {
          box.appendChild(el("div", null, `Boundary last edited: ${edited}`));
        }

        // Attach per-GMU big-game stats when clicking a GMU boundary.
        if (key === "gmu") {
          const gmuCode = String(props.GMUID ?? props.GMU ?? "").padStart(
            3,
            "0",
          );
          // Highlight the clicked unit (same visual as the search-box path).
          highlightUnit(gmuCode, layer);

          if (SPECIES_STATS) {
          const season = document.getElementById("seasonSelect")?.value ?? "all";
          const year = document.getElementById("yearSelect")?.value ?? "";
          const sex = document.getElementById("sexSelect")?.value ?? "any";
          const species = document.getElementById("speciesSelect")?.value ?? "elk";
          const statsBox = el("div");
          statsBox.style.marginTop = "6px";
          let any = false;

          const table =
            (SPECIES_STATS.seasons?.[species]?.[season] || {})[year] ||
            (season === "all" ? SPECIES_STATS[species]?.units : null);
          const raw = table && table[gmuCode];

          if (sex === "licenses") {
            // License-sex mode: draw licenses broken down by tag sex.
            const lic = (SPECIES_STATS.licenses?.[species] || {})[gmuCode];
            if (lic) {
              any = true;
              const total = lic.bull + lic.cow + lic.either;
              statsBox.appendChild(
                el(
                  "div",
                  null,
                  `${cap(species)} — ${total} draw licenses: ` +
                    `${lic.bull} ${SEX_M[species]} · ${lic.cow} ${SEX_F[species]} · ${lic.either} either-sex`,
                ),
              );
            }
          } else if (raw) {
            // Harvest mode; sex filter excludes young (calves/fawns) rows.
            const male = raw.males ?? 0,
              female = raw.females ?? 0;
            const skip =
              (sex === "males" && male === 0) ||
              (sex === "females" && female === 0);
            if (!skip) {
              const shown =
                sex === "males"
                  ? male
                  : sex === "females"
                    ? female
                    : raw.harvest;
              const note =
                sex !== "any" && (raw.young ?? 0) > 0
                  ? ` (+${raw.young} young not shown)`
                  : "";
              any = true;
              const parts = [`harvest ${shown}${note}`];
              if (sex === "any" && raw.hunters != null)
                parts.push(`hunters ${raw.hunters}`);
              if (sex === "any" && raw.success_pct != null)
                parts.push(`success ${raw.success_pct}%`);
              statsBox.appendChild(
                el("div", null, `${cap(species)} — ${parts.join(" · ")}`),
              );
            }
          }
          if (any) box.appendChild(statsBox);
          // Always update the stats panel below the map on every GMU click,
          // even when there is no data for the current filter combination.
          showStatCard(gmuCode);
          }
        }

        L.popup().setLatLng(event.latlng).setContent(box).openOn(map);
      });
    });

    geoLayers[key] = dataLayer;
    updateStatus(`${cfg.name} loaded (${geojson.features.length} features).`);
    if (key === "gmu") setupSearch();
  })();

  try {
    await loading[key];
  } finally {
    delete loading[key];
  }
}

// ---- GMU search & highlight ----
let highlighted = null;
let highlightOutline = null;

function setupSearch() {
  const gmuLayer = geoLayers.gmu;
  if (!gmuLayer) return;

  const units = new Map(); // unit number -> layer
  gmuLayer.eachLayer((layer) => {
    const props = layer.feature.properties || {};
    const num = props.GMUID ?? props.gmuid ?? props.GMU;
    if (num != null) units.set(String(num).padStart(3, "0"), layer);
  });

  const datalist = document.getElementById("gmuList");
  datalist.innerHTML = "";
  for (const unit of [...units.keys()].sort()) {
    const opt = document.createElement("option");
    opt.value = unit;
    datalist.appendChild(opt);
  }

  const input = document.getElementById("gmuSearch");
  const status = document.getElementById("searchStatus");
  input.disabled = false;
  status.textContent = `${units.size} units searchable.`;

  function doSearch() {
    const raw = input.value.trim();
    if (!raw) return;
    const query = raw.padStart(3, "0");
    const layer = units.get(query);
    if (!layer) {
      status.textContent = `No unit "${raw}". Try 3 digits like 201.`;
      return;
    }
    status.textContent = `Unit ${query} highlighted.`;
    highlightUnit(query, layer);
    input.value = "";
  }

  // 'change' only fires on blur; also handle Enter, the Go button, and datalist picks.
  input.addEventListener("change", doSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      doSearch();
    }
  });
  document.getElementById("gmuSearchBtn").addEventListener("click", doSearch);
}

function highlightUnit(unit, layer) {
  const mapLayers = geoLayers.gmu;
  if (highlighted) {
    mapLayers.resetStyle(highlighted);
    highlighted = null;
  }
  if (highlightOutline) {
    map.removeLayer(highlightOutline);
    highlightOutline = null;
  }

  highlighted = layer;
  layer.setStyle({
    fillColor: "#facc15",
    fillOpacity: 0.45,
    color: "#facc15",
    weight: 4,
    opacity: 1,
  });
  layer.bringToFront();

  // Dashed pulsing-style outline ring around the selected polygon
  highlightOutline = L.polyline(
    layer.getLatLngs().flat ? layer.getLatLngs().flat() : layer.getLatLngs(),
    {
      color: "#fde047",
      weight: 10,
      opacity: 0.35,
      dashArray: "1 12",
      lineCap: "round",
      interactive: false,
    },
  ).addTo(map);

  map.fitBounds(layer.getBounds(), { padding: [40, 40] });
  showStatCard(unit);
}

function updateStatus(message) {
  const status = document.getElementById("status");
  const row = document.createElement("div");
  row.textContent = message;
  status.appendChild(row);
}

async function initMap() {
  const mapEl = document.getElementById("map");
  map = L.map("map", {
    center: [39.0, -105.5],
    zoom: 7,
  });

  const apiKey = mapEl.dataset.maptilerKey;
  const statsUrl = mapEl.dataset.statsUrl;

  // Load pre-extracted per-GMU big-game stats (harvest + licenses).
  try {
    const res = await fetch(statsUrl);
    if (res.ok) SPECIES_STATS = await res.json();
  } catch (e) {
    /* stats are optional */
  }
  L.tileLayer(
    `https://api.maptiler.com/maps/outdoor-v2/{z}/{x}/{y}.png?key=${encodeURIComponent(apiKey)}`,
    {
      tileSize: 512,
      zoomOffset: -1,
      maxZoom: 22,
      attribution:
        '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> ' +
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    },
  ).addTo(map);

  for (const key of Object.keys(layers)) {
    document.getElementById(key).addEventListener("change", async (e) => {
      try {
        if (e.target.checked) await loadLayer(key);
        if (geoLayers[key]) {
          geoLayers[key].setStyle(layerStyle(layers[key], key));
          if (!e.target.checked) map.removeLayer(geoLayers[key]);
          else geoLayers[key].addTo(map);
        }
      } catch (error) {
        updateStatus(`${layers[key].name}: ${error.message}`);
      }
    });
  }

  // Load the default visible layers.
  for (const key of ["gmu", "public"]) {
    try {
      await loadLayer(key);
    } catch (error) {
      updateStatus(`${layers[key].name}: ${error.message}`);
    }
  }

  // Deep link: /maps/?gmu=101 highlights and opens that unit's stat card.
  // The GMU layer loads asynchronously, so retry until the unit is found.
  const params = new URLSearchParams(window.location.search);
  const gmuParam = params.get("gmu");
  if (gmuParam) {
    const input = document.getElementById("gmuSearch");
    if (input) input.value = gmuParam;
    let tries = 0;
    const timer = setInterval(() => {
      tries++;
      document.getElementById("gmuSearchBtn")?.click();
      if (!document.getElementById("statCard")?.hidden || tries > 12) clearInterval(timer);
    }, 500);
  }
}

// Shared style for both the initial load and the checkbox re-style path.
function layerStyle(cfg, key) {
  // DAU layers are boundary LINE features, not polygons — fill styling
  // is ignored on polylines, so they must be drawn as visible lines.
  return cfg.isLine
    ? { color: cfg.color, opacity: 0.9, weight: 3, dashArray: "8 5" }
    : {
        fillColor: cfg.color,
        fillOpacity: cfg.opacity,
        color: cfg.color,
        opacity: 0.95,
        weight: key === "gmu" ? 2 : 1,
      };
}

// ---- GMU stats card ----
const statCard = document.getElementById("statCard");
const statCardTitle = document.getElementById("statCardTitle");
const statCardBody = document.getElementById("statCardBody");
const statCardClose = document.getElementById("statCardClose");

if (!statCard || !statCardTitle || !statCardBody || !statCardClose) {
  console.warn("GMU stats card elements are missing from this page.");
} else {
statCardClose.addEventListener("click", () => {
  statCard.hidden = true;
})}

function pctArrow(prev, curr) {
  if (prev == null || curr == null) return "";
  if (curr > prev) return " ▲";
  if (curr < prev) return " ▼";
  return "";
}

// Small DOM helpers: replace ~150 lines of createElement boilerplate.
function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
}

// Format an epoch-milliseconds timestamp (CPW EDIT_DATE style) as a real
// date. Returns null for null/empty/nonsense input so callers can skip it.
function fmtMsDate(value) {
  if (value == null || value === "") return null;
  const ms = Number(value);
  if (!Number.isFinite(ms) || ms <= 0) return null;
  // CPW timestamps are in ms; a plain seconds value would land in 1970.
  const seconds = ms > 1e12 ? ms / 1000 : ms;
  const date = new Date(seconds * 1000);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Render a property value for the fallback popup: format epoch-ms date
// fields, pass everything else through as text.
function fmtValue(key, value) {
  if (/date/i.test(key)) {
    const formatted = fmtMsDate(value);
    if (formatted) return formatted;
  }
  return String(value ?? "");
}

function statRow(label, value) {
  const row = el("div", "stat-row");
  row.append(el("span", null, label), el("span", null, String(value)));
  return row;
}

function speciesBlockHeader(species, colHead) {
  const title = el("div", "stat-species-title");
  title.append(
    el("strong", null, species[0].toUpperCase() + species.slice(1)),
    el("span", "colhead", colHead),
  );
  return title;
}

const cap = (s) => s[0].toUpperCase() + s.slice(1);

const statTabs = document.getElementById("statTabs");
let activeTabSpecies = "all";

function finishCard() {
  statCard.hidden = false;
  // Enable "Share to group chat" once a unit is shown.
  const shareBtn = document.getElementById("statShareChat");
  if (shareBtn) shareBtn.disabled = false;
  statCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderTabs(speciesList) {
  statTabs.innerHTML = "";
  if (speciesList.length <= 1) {
    statTabs.hidden = true;
    return;
  }
  statTabs.hidden = false;
  const labels = {
    all: "All",
    elk: "Elk",
    deer: "Deer",
    pronghorn: "Pronghorn",
    bear: "Bear",
  };
  for (const key of ["all", ...speciesList]) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = labels[key] || key;
    if (key === activeTabSpecies) btn.classList.add("active");
    btn.addEventListener("click", () => {
      activeTabSpecies = key;
      if (lastGmu) showStatCard(lastGmu);
    });
    statTabs.appendChild(btn);
  }
}

function renderStatCard(gmuCode) {
  if (!statCard || !statCardTitle || !statCardBody) return;
  const seasonSelect = document.getElementById("seasonSelect");
  const sexSelect = document.getElementById("sexSelect");
  const speciesSelect = document.getElementById("speciesSelect");
  if (!seasonSelect || !sexSelect || !speciesSelect) return;

  const season = seasonSelect.value;
  const sex = sexSelect.value;
  const speciesChoice = speciesSelect.value;
  const allSpecies =
    speciesChoice === "all"
      ? ["elk", "deer", "pronghorn", "bear"]
      : [speciesChoice];
  // Tab filter: on mobile the tabs let you focus one species without scrolling.
  const speciesList =
    activeTabSpecies === "all"
      ? allSpecies
      : allSpecies.filter((s) => s === activeTabSpecies);
  const years = (SPECIES_STATS.harvest_years || []).slice().sort();

  const selectedSeasonOption = seasonSelect.selectedOptions[0];
  const seasonLabel = selectedSeasonOption
    ? selectedSeasonOption.textContent
    : season || "All seasons";
  statCardTitle.textContent = `${gmuCode} · ${seasonLabel}${speciesList.length === 1 ? ` — ${speciesList[0][0].toUpperCase() + speciesList[0].slice(1)}` : " — all species"}`;

  statCardBody.textContent = "";
  if (activeTabSpecies !== "all" && !allSpecies.includes(activeTabSpecies))
    activeTabSpecies = "all";
  renderTabs(allSpecies);

  if (sex === "licenses") {
    const anyLic = renderLicenseCard(speciesList, gmuCode);
    if (!anyLic)
      statCardBody.textContent = "No draw license data for this unit.";
    finishCard();
    return;
  }

  // Harvest by year for the selected season + sex, one card per species.
  for (const species of speciesList) {
    const block = renderHarvestCard(species, gmuCode, season, sex, years);
    if (!block) continue;
    statCardBody.appendChild(block);
  }
  if (!statCardBody.childElementCount) {
    statCardBody.textContent =
      "No harvest data for this unit, season, and sex.";
  }
  finishCard();
}

// Draw-license block: one sub-block per species with bull/cow/either counts.
function renderLicenseCard(speciesList, gmuCode) {
  let anyLic = false;
  for (const species of speciesList) {
    const lic = (SPECIES_STATS.licenses?.[species] || {})[gmuCode];
    if (!lic) continue;
    anyLic = true;
    const block = el("div", "stat-species-block");
    block.appendChild(
      speciesBlockHeader(species, `${SPECIES_STATS.license_year} draw`),
    );
    block.appendChild(statRow("Total", lic.bull + lic.cow + lic.either));
    block.appendChild(statRow(SEX_M[species], lic.bull));
    block.appendChild(statRow(SEX_F[species], lic.cow));
    block.appendChild(statRow("Either sex", lic.either));
    statCardBody.appendChild(block);
  }
  return anyLic;
}

// Harvest-by-year block for one species; returns null when nothing to show.
function renderHarvestCard(species, gmuCode, season, sex, years) {
  const block = el("div", "stat-species-block");
  block.appendChild(speciesBlockHeader(species, "Harvest · Success"));

  let last = null;
  let rowCount = 0;
  const selectedYear = String(document.getElementById("yearSelect").value);
  for (const year of [...years].sort()) {
    const raw = ((SPECIES_STATS.seasons?.[species]?.[season] || {})[year] ||
      {})[gmuCode];
    if (!raw) continue;
    const male = raw.males ?? 0,
      female = raw.females ?? 0;
    if (
      (sex === "males" && male === 0) ||
      (sex === "females" && female === 0)
    )
      continue;
    const shown =
      sex === "males" ? male : sex === "females" ? female : raw.harvest;

    const row = el("div", "stat-row");
    const left = el("span", null, String(year));
    if (String(year) === selectedYear) {
      left.textContent = `${year} ←`;
      left.style.fontWeight = "700";
    }
    const right = el("span");
    const arrow = pctArrow(last, shown);
    if (arrow)
      right.className = arrow.trim() === "▲" ? "trend-up" : "trend-down";
    right.appendChild(document.createTextNode(`${shown}`));
    if (arrow) right.appendChild(el("span", "trend-arrow", arrow.trim()));
    if (sex === "any" && raw.success_pct != null) {
      right.appendChild(document.createTextNode(` · ${raw.success_pct}%`));
    }
    row.append(left, right);
    block.appendChild(row);

    // Sex breakdown row beneath the year row.
    if (sex === "any" && (raw.males != null || raw.females != null)) {
      const terms = {
        elk: ["bulls", "cows", "calves"],
        deer: ["bucks", "does", "fawns"],
        pronghorn: ["bucks", "does", "fawns"],
        bear: ["boars", "sows", null],
      };
      const [mTerm, fTerm, yTerm] = terms[species] || [
        "males",
        "females",
        "young",
      ];
      const bits = [];
      if (raw.males) bits.push(`${raw.males} ${mTerm}`);
      if (raw.females) bits.push(`${raw.females} ${fTerm}`);
      if (yTerm && raw.young) bits.push(`${raw.young} ${yTerm}`);
      block.appendChild(el("div", "stat-sexrow", bits.join(" · ")));
    }
    last = shown;
    rowCount++;
  }

  // Per-season harvest breakdown for the selected year (only in "all seasons" view).
  if (sex === "any") renderSeasonBreakdown(species, gmuCode, selectedYear, block);

  if (!rowCount && !block.querySelector(".stat-seasons")) return null;
  return block;
}

// "By season" sub-table for the selected year, appended to a harvest block.
function renderSeasonBreakdown(species, gmuCode, selectedYear, block) {
  const seasonTables = SPECIES_STATS.seasons?.[species] || {};
  const seasonDefs = [
    ["rifle_1", "Rifle 1"],
    ["rifle_2", "Rifle 2"],
    ["rifle_3", "Rifle 3"],
    ["rifle_4", "Rifle 4"],
    ["rifle", "Rifle (all)"],
    ["september", "September"],
    ["archery", "Archery"],
    ["muzzleloader", "Muzzleloader"],
  ];
  const seasonRows = [];
  for (const [key, label] of seasonDefs) {
    const row = ((seasonTables[key] || {})[selectedYear] || {})[gmuCode];
    if (!row || row.harvest == null) continue;
    seasonRows.push({
      label,
      harvest: row.harvest,
      success: row.success_pct,
    });
  }
  if (seasonRows.length <= 1) return;
  const sub = el("div", "stat-seasons");
  sub.appendChild(el("div", "stat-seasons-head", `By season (${selectedYear})`));
  for (const s of seasonRows) {
    const r = el("div", "stat-season-row");
    r.append(
      el("span", null, s.label),
      el(
        "span",
        null,
        `${s.harvest}${s.success != null ? ` · ${s.success}%` : ""}`,
      ),
    );
    sub.appendChild(r);
  }
  block.appendChild(sub);
}

// Build a short shareable message: "check this GMU out" + a deep link to
// the map with that unit pre-selected.
function buildShareText(gmuCode) {
  const url = `${window.location.origin}${window.location.pathname}?gmu=${encodeURIComponent(gmuCode)}`;
  return `Check out GMU ${gmuCode}! 🗺️\n${url}`;
}

// Re-render the card when pickers change; remember the last GMU clicked.
let lastGmu = null;
function showStatCard(gmu) {
  lastGmu = gmu;
  try {
    localStorage.setItem("rmc_last_gmu_v1", JSON.stringify(gmu));
  } catch {
    /* storage unavailable — the sidebar just won't show the shared unit */
  }
  renderStatCard(gmu);
}
for (const id of ["speciesSelect", "seasonSelect", "sexSelect", "yearSelect"]) {
  document.getElementById(id).addEventListener("change", () => {
    if (statCard && !statCard.hidden && lastGmu) showStatCard(lastGmu);
  });
}

// "Share to group chat" dropdown: POST the current unit's summary to the
// chosen chat as a regular message (same CSRF-protected path as the chat form).
const statShareBtn = document.getElementById("statShareChat");
if (statShareBtn) {
  statShareBtn.parentElement
    .querySelectorAll(".dropdown-item[data-chat-url]")
    .forEach((item) => {
      item.addEventListener("click", async () => {
        if (!lastGmu || statShareBtn.disabled) return;
        const text = buildShareText(lastGmu);
        if (!text) return;
        const csrf = document.querySelector("input[name=csrfmiddlewaretoken]");
        const token = csrf?.value || document.cookie.split(";").map(c => c.trim())
          .find(c => c.startsWith("csrftoken="))?.split("=")[1];
        if (!token) return; // no token available — bail rather than fail the POST
        try {
          const resp = await fetch(item.dataset.chatUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": token,
            },
            body: new URLSearchParams({
              text,
              kind: "gmu",
              payload: JSON.stringify({ gmu: lastGmu }),
            }),
          });
          if (resp.ok) {
            // Land on the chat that received the share; ?gmu= re-triggers
            // the highlight when the visitor clicks the unit link.
            window.location.href = item.dataset.chatUrl + (item.dataset.chatUrl.includes("?") ? "&" : "?") + "gmu=" + encodeURIComponent(lastGmu);
          } else {
            alert("Couldn't share to chat (HTTP " + resp.status + "). Try again.");
          }
        } catch (err) {
          alert("Couldn't reach the chat: " + err.message);
        }
      });
    });
}

initMap();
