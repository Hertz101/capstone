// Shared constants for CPW GIS integration (hunt map + planner map).
// Layer ids used by the app: 5 public-access, 6 GMU, 22 deer DAU,
// 23 elk DAU, 12 Walk-In Access.
// Note: separate <script> tags have isolated const/let scopes, so this is
// deliberately attached to window for cross-file access.
window.CPW_FEATURESERVER =
  "https://services5.arcgis.com/ttNGmDvKQA7oeDQ3/ArcGIS/rest/services/CPWAdminData/FeatureServer";

// Shared MapTiler terrain layer config — identical on the hunt map and the
// planner map, so the tile URL/attribution live in one place.
window.MAPTILER_TILE_LAYER = (apiKey) =>
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
  );
