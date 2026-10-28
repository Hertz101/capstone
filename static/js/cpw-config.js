// Shared constants for CPW GIS integration (hunt map + planner map).
// Layer ids used by the app: 5 public-access, 6 GMU, 22 deer DAU,
// 23 elk DAU, 12 Walk-In Access.
// Note: separate <script> tags have isolated const/let scopes, so this is
// deliberately attached to window for cross-file access.
window.CPW_FEATURESERVER =
  "https://services5.arcgis.com/ttNGmDvKQA7oeDQ3/ArcGIS/rest/services/CPWAdminData/FeatureServer";
