// Your Trip: pre-hunt checklist with localStorage persistence.
// Checked state and user-added items survive page reloads on this device.

(function () {
  const STORAGE_KEY = "rmc_trip_checklist_v1";
  const root = document.getElementById("tripChecklist");
  const progress = document.getElementById("tripProgress");
  if (!root) return;

  const groups = Array.from(root.querySelectorAll(".trip-group"));
  let state = loadState();

  function loadState() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
      return {};
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* storage unavailable (private mode) — checklist still works, just won't persist */
    }
  }

  // state shape: { "group:originalIndex": true, "custom:group:timestamp": {text, done} }
  function updateProgress() {
    let total = 0;
    let done = 0;
    root.querySelectorAll("input[type=checkbox]").forEach(box => {
      total++;
      if (box.checked) done++;
    });
    progress.textContent = `${done} of ${total} packed`;
  }

  function bindCheckbox(box) {
    box.addEventListener("change", () => {
      state[box.dataset.item] = box.checked;
      saveState();
      updateProgress();
    });
  }

  function makeCustomItem(groupEl, text, key, done) {
    const li = document.createElement("li");
    const label = document.createElement("label");
    label.className = "trip-item";

    const box = document.createElement("input");
    box.type = "checkbox";
    box.dataset.item = key;
    box.dataset.label = text;   // so the packing list can show its text
    box.checked = !!done;

    const mark = document.createElement("span");
    mark.className = "trip-checkmark";
    mark.setAttribute("aria-hidden", "true");

    const span = document.createElement("span");
    span.className = "trip-item-label";
    span.textContent = text;

    label.append(box, mark, span);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "trip-item-remove";
    remove.setAttribute("aria-label", `Remove ${text}`);
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      delete state[key];
      delete state[`done:${key}`];
      saveState();
      li.remove();
      updateProgress();
    });

    li.append(label, remove);
    groupEl.querySelector(".trip-items").appendChild(li);
    bindCheckbox(box);
    // Persist custom item text separately from done state.
    state[`text:${key}`] = text;
    saveState();
  }

  groups.forEach(groupEl => {
    const groupId = groupEl.dataset.group;

    // Restore checked state for original items.
    groupEl.querySelectorAll("input[type=checkbox]").forEach(box => {
      if (state[box.dataset.item]) {
        box.checked = true;
      }
      bindCheckbox(box);
    });

    // Restore previously added custom items.
    Object.keys(state).forEach(key => {
      if (key.startsWith(`text:custom:${groupId}:`)) {
        makeCustomItem(groupEl, state[key], key.slice("text:".length), state[key.slice(5)] || false);
      }
    });

    // Add-your-own row.
    const input = groupEl.querySelector(".trip-add-input");
    const btn = groupEl.querySelector(".trip-add-btn");
    function add() {
      const text = input.value.trim();
      if (!text) return;
      const key = `custom:${groupId}:${Date.now()}`;
      makeCustomItem(groupEl, text, key, false);
      input.value = "";
      updateProgress();
    }
    btn.addEventListener("click", add);
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        e.preventDefault();
        add();
      }
    });
  });

  function setAllOpen(open) {
    groups.forEach(g => g.classList.toggle("collapsed", !open));
  }
  document.getElementById("tripExpandAll")?.addEventListener("click", () => setAllOpen(true));
  document.getElementById("tripCollapseAll")?.addEventListener("click", () => setAllOpen(false));

  document.getElementById("tripReset")?.addEventListener("click", () => {
    if (!confirm("Reset the checklist? All checked items and custom additions will be cleared.")) return;
    state = {};
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    root.querySelectorAll("input[type=checkbox]").forEach(box => {
      if (box.dataset.item.startsWith("custom:")) {
        box.closest("li")?.remove();
      } else {
        box.checked = false;
      }
    });
    updateProgress();
  });

  updateProgress();

  // ----------------------------------------
  // "My Hunt Plan" card (from the Hunt Planner)
  // ----------------------------------------
  // Show the card either way: populated with the plan, or with a
  // call-to-action when no plan exists. If this card never appears at
  // all, the script itself isn't running (cache/script error).
  const planCard = document.getElementById("planCard");
  if (planCard) {
    let plan = null;
    try {
      plan = JSON.parse(localStorage.getItem("rmc_hunt_plan_v1"));
    } catch (e) {
      console.error("your_trip.js: corrupt hunt plan in localStorage", e);
    }

    if (plan && plan.species) {
      document.getElementById("planSpecies").textContent = plan.species || "—";
      document.getElementById("planSeason").textContent = plan.season || "—";
      document.getElementById("planMethod").textContent = plan.method || "—";
      document.getElementById("planGmu").textContent = plan.gmu ? `GMU ${plan.gmu}` : "—";
      document.getElementById("planLicense").textContent = plan.license || "—";
      if (plan.savedAt) {
        const when = new Date(plan.savedAt);
        document.getElementById("planSavedAt").textContent =
          `Last updated ${when.toLocaleDateString()} at ${when.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
      }
    } else {
      // Empty state: swap the field list for a prompt to build a plan.
      planCard.querySelector(".plan-body").innerHTML =
        '<p class="plan-empty">No hunt plan yet. ' +
        '<a href="' + planCard.dataset.plannerUrl + '">Build one in the Hunt Planner</a>' +
        ' and it will show up here.</p>';
      planCard.querySelector(".plan-header h3").textContent = "🎯 My Hunt Plan";
    }
    planCard.hidden = false;
  }

  // ----------------------------------------
  // "My Packing List" summary card
  // ----------------------------------------
  const packingBody = document.getElementById("packingBody");
  const packingEmpty = document.getElementById("packingEmpty");

  function updatePackingList() {
    if (!packingBody) return;
    let any = false;
    packingBody.querySelectorAll(".packing-group").forEach(pg => {
      const groupId = pg.dataset.packing;
      const ul = pg.querySelector("ul");
      ul.replaceChildren();

      // Collect checked items whose data-item key starts with this group id
      // (covers both "groupId:n" and "custom:groupId:ts" keys).
      root.querySelectorAll("input[type=checkbox]:checked").forEach(box => {
        const key = box.dataset.item;
        if (!key.startsWith(`${groupId}:`) && !key.startsWith(`custom:${groupId}:`)) return;
        any = true;
        const li = document.createElement("li");
        li.textContent = box.dataset.label || key;
        ul.appendChild(li);
      });

      pg.hidden = !ul.childElementCount;
    });
    packingBody.hidden = !any;
    packingEmpty.hidden = any;
  }

  // Rebuild whenever any checkbox changes (capture phase catches all).
  root.addEventListener("change", updatePackingList);
  root.addEventListener("click", e => {
    // Custom-item removal also changes the list.
    if (e.target.classList?.contains("trip-item-remove")) {
      setTimeout(updatePackingList, 0);
    }
  });
  document.getElementById("tripReset")?.addEventListener("click", () => {
    setTimeout(updatePackingList, 0);
  });
  updatePackingList();

  // Copy to clipboard.
  document.getElementById("packingCopy")?.addEventListener("click", async () => {
    const lines = [];
    packingBody.querySelectorAll(".packing-group:not([hidden])").forEach(pg => {
      lines.push(pg.querySelector("h4").textContent);
      pg.querySelectorAll("li").forEach(li => lines.push(`  ${li.textContent}`));
      lines.push("");
    });
    const text = lines.join("\n").trim();
    try {
      await navigator.clipboard.writeText(text);
      const btn = document.getElementById("packingCopy");
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = "Copy"; }, 1500);
    } catch {
      alert(text);  // clipboard blocked — fall back to showing the list
    }
  });

  // Print just the packing list.
  document.getElementById("packingPrint")?.addEventListener("click", () => {
    document.body.classList.add("print-packing-only");
    window.print();
    setTimeout(() => document.body.classList.remove("print-packing-only"), 500);
  });
})();
