(() => {
  "use strict";

  const MAP_ELEMENT = document.getElementById("gmuMap");
  const SEARCH_ELEMENT = document.getElementById("gmuSearch");
  const SELECTED_ELEMENT = document.getElementById("selectedGMU");
  const STATUS_ELEMENT = document.getElementById("gmuMapStatus");
  const GMU_INPUT = document.getElementById("gmu");

  if (
    !MAP_ELEMENT ||
    !SEARCH_ELEMENT ||
    !SELECTED_ELEMENT ||
    !STATUS_ELEMENT ||
    !GMU_INPUT
  ) {
    console.warn("GMU map elements are missing from this page.");
    return;
  }

  if (typeof L === "undefined") {
    STATUS_ELEMENT.textContent =
      "Leaflet did not load. Check the Leaflet script in base.html.";
    console.error("Leaflet (L) is undefined.");
    return;
  }

  const CPW_GMU_QUERY =
    "https://services5.arcgis.com/ttNGmDvKQA7oeDQ3/ArcGIS/rest/services/CPWAdminData/FeatureServer/6/query";

  let map;
  let gmuLayer = null;
  let selectedLayer = null;
  let featureLayers = [];

  const normalStyle = {
    color: "#315c3b",
    weight: 1.5,
    fillColor: "#8da98a",
    fillOpacity: 0.18
  };

  const selectedStyle = {
    color: "#e07a19",
    weight: 3,
    fillColor: "#f2b66d",
    fillOpacity: 0.55
  };

  function setStatus(message) {
    STATUS_ELEMENT.textContent = message;
  }

  function getGMU(feature) {
    const properties = feature?.properties || {};

    const key = Object.keys(properties).find(
      name => name.toUpperCase() === "GMUID"
    );

    return key && properties[key] != null
      ? String(properties[key]).trim()
      : "";
  }

  // ----------------------------------------
  // Initialize the map BEFORE adding layers.
  // ----------------------------------------
  function initializeMap() {
    const apiKey = MAP_ELEMENT.dataset.maptilerKey?.trim();

    if (!apiKey) {
      throw new Error(
        "MapTiler API key is missing. Check data-maptiler-key in home.html."
      );
    }

    map = L.map(MAP_ELEMENT, {
      center: [39.0, -105.5],
      zoom: 7
    });

    // MapTiler base map
    L.tileLayer(
      `https://api.maptiler.com/maps/outdoor-v2/{z}/{x}/{y}.png?key=${encodeURIComponent(apiKey)}`,
      {
        tileSize: 512,
        zoomOffset: -1,
        maxZoom: 22,
        attribution:
          '&copy; <a href="https://www.maptiler.com/copyright/">MapTiler</a> ' +
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
      }
    ).addTo(map);

    map.on("tileerror", event => {
      console.error("Map tile failed to load:", event);
    });
  }

  function selectFeature(layer, feature) {
    if (selectedLayer && gmuLayer) {
      gmuLayer.resetStyle(selectedLayer);
    }

    selectedLayer = layer;
    selectedLayer.setStyle(selectedStyle);
    selectedLayer.bringToFront();

    const number = getGMU(feature);

    GMU_INPUT.value = number;
    SELECTED_ELEMENT.textContent = number
      ? `GMU ${number}`
      : "Selected unit";

    setStatus(
      number
        ? `GMU ${number} selected. Confirm current regulations with CPW.`
        : "Unit selected. Verify its number in the official CPW Hunting Atlas."
    );

    GMU_INPUT.dispatchEvent(
      new Event("change", { bubbles: true })
    );
  }

  function findFeatureByNumber(value) {
    const normalized = value.trim().toLowerCase();

    if (!normalized) {
      return null;
    }

    return featureLayers.find(item => {
      const number = getGMU(item.feature).toLowerCase();

      return (
        number === normalized ||
        `gmu ${number}` === normalized
      );
    }) || null;
  }

  // ----------------------------------------
  // Build the ArcGIS query URL for GMU data.
  // ----------------------------------------
  function buildQuery() {
    const params = new URLSearchParams({
      where: "GMUID IS NOT NULL",
      outFields: "*",
      returnGeometry: "true",
      outSR: "4326",
      f: "geojson"
    });

    return `${CPW_GMU_QUERY}?${params.toString()}`;
  }

  // ----------------------------------------
  // Validate the response and keep usable features.
  // ----------------------------------------
  function validateAndFilterFeatures(data) {
    if (data.error) {
      throw new Error(
        data.error.message || "CPW GIS returned an error."
      );
    }

    if (
      !Array.isArray(data.features) ||
      data.features.length === 0
    ) {
      throw new Error(
        "The CPW GIS service returned no GMU features."
      );
    }

    const validFeatures = data.features.filter(feature => {
      if (
        !feature ||
        !feature.geometry ||
        !getGMU(feature)
      ) {
        return false;
      }

      try {
        return L.geoJSON(feature).getBounds().isValid();
      } catch (error) {
        return false;
      }
    });

    if (validFeatures.length === 0) {
      console.error("CPW GeoJSON response:", data);

      throw new Error(
        "No valid GMU boundaries were found in the CPW response."
      );
    }

    return validFeatures;
  }

  // ----------------------------------------
  // Add the GMU layer to the map and fit its bounds.
  // ----------------------------------------
  function addGMULayerToMap(features) {
    featureLayers = [];

    gmuLayer = L.geoJSON(
      { type: "FeatureCollection", features },
      {
        style: normalStyle,
        onEachFeature(feature, layer) {
          const number = getGMU(feature);

          layer.bindTooltip(`GMU ${number}`);
          layer.on("click", () => selectFeature(layer, feature));
          featureLayers.push({ feature, layer });
        }
      }
    ).addTo(map);

    const bounds = gmuLayer.getBounds();

    if (!bounds.isValid()) {
      gmuLayer.remove();
      gmuLayer = null;
      throw new Error("The GMU layer has invalid map bounds.");
    }

    map.fitBounds(bounds, { padding: [15, 15] });
  }

  // ----------------------------------------
  // Load Colorado Parks and Wildlife GMUs.
  // Fetch → validate → add to map → report status.
  // ----------------------------------------
  async function loadGMUs() {
    setStatus("Loading GMU boundaries from CPW GIS...");

    try {
      const response = await fetch(buildQuery());

      if (!response.ok) {
        throw new Error(`CPW GIS request failed: HTTP ${response.status}`);
      }

      const validFeatures = validateAndFilterFeatures(await response.json());
      addGMULayerToMap(validFeatures);

      setStatus(
        `${validFeatures.length} GMU boundaries loaded. Click a unit to select it.`
      );
    } catch (error) {
      console.error("Unable to load CPW GMUs:", error);
      setStatus(
        `Could not load GMU boundaries: ${error.message}. ` +
        "You can use the official CPW Hunting Atlas."
      );
    }
  }

  // ----------------------------------------
  // Search for a GMU by number.
  // ----------------------------------------
  function searchGMU() {
    const value = SEARCH_ELEMENT.value.trim();

    if (!value) {
      setStatus("Enter a GMU number to search.");
      return;
    }

    const match = findFeatureByNumber(value);

    if (!match) {
      setStatus(
        `GMU "${value}" was not found in the loaded boundary data.`
      );
      return;
    }

    const bounds = match.layer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [25, 25]
      });

      selectFeature(match.layer, match.feature);
    }
  }

  // ----------------------------------------
  // Start the map in the correct order.
  // ----------------------------------------
  try {
    initializeMap();
  } catch (error) {
    console.error("Unable to initialize the map:", error);
    setStatus(`Map initialization failed: ${error.message}`);
    return;
  }

  SEARCH_ELEMENT.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchGMU();
    }
  });

  SEARCH_ELEMENT.addEventListener("change", searchGMU);

  loadGMUs();
})();