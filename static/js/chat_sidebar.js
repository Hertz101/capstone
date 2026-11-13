// Group-chat sidebar: surfaces the user's hunt plan, packing list, and the
// GMU they had selected on the Hunting Map, and lets them share any of the
// three into the chat as a regular message.
//
// Data sources (same keys the other pages already write):
//   rmc_hunt_plan_v1    — hunt plan from the Hunt Planner
//   rmc_trip_checklist_v1 — checked packing items (key -> label map)
//   rmc_last_gmu_v1     — last GMU clicked on the Hunting Map
(function () {
  const sidebar = document.getElementById("chatSidebar");
  if (!sidebar) return;

  function readJson(key) {
    try {
      return JSON.parse(localStorage.getItem(key));
    } catch {
      return null;
    }
  }

  function setText(id, value) {
    // Null-checked so a missing template element degrades to a skipped
    // update instead of throwing and killing the whole sidebar script.
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function setEmpty(cardId, emptyId, empty) {
    const card = document.getElementById(cardId);
    const emptyEl = document.getElementById(emptyId);
    if (card) card.classList.toggle("chat-tool-card-empty", empty);
    if (emptyEl) emptyEl.hidden = !empty;
  }

  // ---- Hunt plan -----------------------------------------------------------
  const plan = readJson("rmc_hunt_plan_v1");
  let planPayload = null;
  if (plan && plan.species) {
    setText("planSpecies", plan.species || "—");
    setText("planSeason", plan.season || "—");
    setText("planMethod", plan.method || "—");
    setText("planGmu", plan.gmu ? `GMU ${plan.gmu}` : "—");
    setText("planLicense", plan.license || "—");
    planPayload = {
      species: plan.species || "",
      season: plan.season || "",
      method: plan.method || "",
      gmu: plan.gmu || "",
      license: plan.license || "",
    };
  }
  setEmpty("planCard", "planEmpty", !planPayload);

  // ---- Packing list --------------------------------------------------------
  // Checklist state is { "group:N": bool, "custom:<id>": bool } plus a
  // parallel label map persisted by your_trip.js.
  const state = readJson("rmc_trip_checklist_v1") || {};
  const labels = readJson("rmc_trip_labels_v1") || {};
  const packingItems = [];
  for (const [key, val] of Object.entries(state)) {
    if (key.startsWith("text:")) continue; // custom item text, not a checkbox
    if (val === true) packingItems.push(labels[key] || key.replace(/_/g, " "));
  }
  let packingPayload = null;
  if (packingItems.length) {
    const list = document.getElementById("packingList");
    packingItems.forEach((label) => {
      const li = document.createElement("li");
      li.textContent = label;
      list.appendChild(li);
    });
    list.hidden = false;
    packingPayload = { items: packingItems };
  }
  setEmpty("packingCard", "packingEmpty", !packingPayload);

  // ---- Selected GMU --------------------------------------------------------
  const lastGmu = readJson("rmc_last_gmu_v1");
  let gmuPayload = null;
  if (lastGmu) {
    setText("gmuCode", `GMU ${lastGmu}`);
    document.getElementById("gmuNote").hidden = false;
    gmuPayload = { gmu: String(lastGmu) };
  }
  setEmpty("gmuCard", "gmuEmpty", !gmuPayload);

  // ---- Share forms: fill each card's own form with the JSON payload -------
  // Each card has its own <form data-kind="..."> with a hidden payload
  // input; the script fills the payload and enables the Share button when
  // there is data to share. No cross-form state, no delegation fragility.
  const forms = {
    plan: sidebar.querySelector('.share-form[data-kind="plan"]'),
    packing: sidebar.querySelector('.share-form[data-kind="packing"]'),
    gmu: sidebar.querySelector('.share-form[data-kind="gmu"]'),
  };
  const payloadFor = { plan: planPayload, packing: packingPayload, gmu: gmuPayload };
  for (const kind of Object.keys(forms)) {
    const form = forms[kind];
    if (!form) continue;
    const payload = payloadFor[kind];
    const btn = form.querySelector("button[type=submit]");
    if (payload) {
      form.querySelector('input[name="payload"]').value = JSON.stringify(payload);
      btn.disabled = false;
    }
  }
})();
