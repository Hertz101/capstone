(() => {
  "use strict";

  // Form elements
  const form = document.getElementById("huntForm");
  const speciesInput = document.getElementById("species");
  const methodInput = document.getElementById("method");
  const seasonInput = document.getElementById("season");
  const gmuInput = document.getElementById("gmu");
  const licenseInput = document.getElementById("license");

  // License guidance elements
  const licenseInfo = document.getElementById("licenseInfo");
  const licenseTitle = document.getElementById("licenseTitle");
  const licenseDescription = document.getElementById("licenseDescription");
  const licenseLink = document.getElementById("licenseLink");

  // Results elements
  const results = document.getElementById("huntResults");
  const summary = document.getElementById("huntSummary");

  const CPW_LICENSE_URL =
    "https://www.cpwshop.com/purchaseprivilege.page";

  // ----------------------------------------
  // Selectable species and hunting-method cards
  // ----------------------------------------
  function initializeHuntCards() {
    const cards = document.querySelectorAll(
      ".hunt-card[data-group][data-value]"
    );

    cards.forEach(card => {
      card.addEventListener("click", () => {
        const group = card.dataset.group;
        const value = card.dataset.value;
        const field = document.getElementById(group);

        if (!field) {
          console.error(`Missing form field: #${group}`);
          return;
        }

        // Make sure the selected value exists in the dropdown.
        const optionExists = Array.from(field.options).some(
          option => option.value === value
        );

        if (!optionExists) {
          console.error(
            `Card value "${value}" does not match an option in #${group}.`
          );
          return;
        }

        // Update the hidden select field.
        field.value = value;
        field.dispatchEvent(
          new Event("change", { bubbles: true })
        );

        // Highlight the selected card within its own group.
        document
          .querySelectorAll(`.hunt-card[data-group="${group}"]`)
          .forEach(other => {
            const selected = other === card;

            other.classList.toggle("selected", selected);
            other.setAttribute("aria-pressed", String(selected));
          });
      });
    });
  }

  // Initialize cards once.
  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initializeHuntCards,
      { once: true }
    );
  } else {
    initializeHuntCards();
  }

  // Stop if this page does not contain the hunt planner.
  if (
    !form ||
    !speciesInput ||
    !methodInput ||
    !seasonInput ||
    !gmuInput ||
    !licenseInput ||
    !licenseInfo ||
    !licenseTitle ||
    !licenseDescription ||
    !licenseLink ||
    !results ||
    !summary
  ) {
    return;
  }

  // ----------------------------------------
  // Method ↔ season coupling
  // ----------------------------------------
  // Archery and Muzzleloader ARE their own season windows, so choosing
  // that method locks the season select; Rifle frees the select for
  // 1st–4th rifle seasons.
  const seasonHint = document.getElementById("seasonHint");

  function syncSeasonWithMethod() {
    const method = methodInput.value;
    if (!seasonInput) return;

    if (method === "Archery" || method === "Black Powder") {
      const locked = method === "Archery" ? "Archery" : "Muzzleloader";
      seasonInput.value = locked;
      seasonInput.disabled = true;
      if (seasonHint) seasonHint.hidden = false;
    } else {
      seasonInput.disabled = false;
      if (seasonHint) seasonHint.hidden = true;
    }
  }

  methodInput.addEventListener("change", syncSeasonWithMethod);
  syncSeasonWithMethod();

  // ----------------------------------------
  // License guidance
  // ----------------------------------------
  const LICENSE_GUIDANCE = {
    yes: {
      title: "Check your license details",
      description:
        "Confirm your license or application is valid for your species, GMU, season, method, and dates. This selection does not verify eligibility.",
      linkText: "Review CPW License Options"
    },
    no: {
      title: "Find the license you need",
      description:
        "Review current Colorado Parks and Wildlife license requirements, application options, deadlines, and restrictions.",
      linkText: "Visit CPW License Shop"
    },
    unsure: {
      title: "Not sure which license applies?",
      description:
        "Check current CPW regulations and license information for your species, hunt area, season, and method.",
      linkText: "Check CPW License Information"
    }
  };

  function updateLicenseInfo() {
    const answer = licenseInput.value;
    const guidance = LICENSE_GUIDANCE[answer];

    // Hide the box until a known answer is chosen.
    licenseInfo.classList.toggle("d-none", !guidance);

    if (!guidance) {
      return;
    }

    licenseLink.href = CPW_LICENSE_URL;
    licenseTitle.textContent = guidance.title;
    licenseDescription.textContent = guidance.description;
    licenseLink.textContent = guidance.linkText;
  }

  licenseInput.addEventListener("change", updateLicenseInfo);

  const LICENSE_SUMMARY_TEXT = {
    yes: "Yes — verify license and hunt eligibility",
    no: "No — review license requirements",
    unsure: "Unsure — check CPW license information"
  };

  // ----------------------------------------
  // Hunt summary helpers
  // ----------------------------------------
  function addSummaryItem(label, value) {
    const item = document.createElement("li");

    item.className =
      "list-group-item d-flex justify-content-between align-items-start gap-3";

    const labelElement = document.createElement("span");
    labelElement.className = "fw-semibold";
    labelElement.textContent = label;

    const valueElement = document.createElement("span");
    valueElement.className = "text-end";
    valueElement.textContent = value;

    item.append(labelElement, valueElement);
    summary.appendChild(item);
  }

  // ----------------------------------------
  // Build the hunt plan
  // ----------------------------------------
  form.addEventListener("submit", event => {
    event.preventDefault();

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const species = speciesInput.value;
    const method = methodInput.value;
    const season = seasonInput.disabled ? seasonInput.value : seasonInput.value;
    const gmu = gmuInput.value.trim();
    const licenseAnswer = licenseInput.value;

    if (!gmu) {
      alert(
        "Please select a GMU on the map before building your hunt plan."
      );

      document.getElementById("gmuMap")?.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });

      return;
    }

    if (!seasonInput.disabled && !seasonInput.value) {
      alert("Please choose a season before building your hunt plan.");
      seasonInput.scrollIntoView({ behavior: "smooth", block: "center" });
      seasonInput.focus();
      return;
    }

    const licenseText =
      LICENSE_SUMMARY_TEXT[licenseAnswer] || "Check CPW license information";

    summary.replaceChildren();

    addSummaryItem("Species", species);
    addSummaryItem("Hunting method", method);
    addSummaryItem("Season", season);
    addSummaryItem("Game Management Unit", `GMU ${gmu}`);
    addSummaryItem("License status", licenseText);

    const note = document.createElement("li");
    note.className = "list-group-item small text-muted";
    note.textContent =
      "This is a preliminary planning summary, not confirmation of a valid tag, season, legal method, access permission, or hunt eligibility. Verify current CPW regulations and land access before hunting.";

    summary.appendChild(note);

    results.classList.remove("d-none");

    // Persist the plan so the Your Trip page can display it as a card.
    try {
      localStorage.setItem("rmc_hunt_plan_v1", JSON.stringify({
        species: species,
        method: method,
        season: season,
        gmu: gmu,
        license: licenseText,
        savedAt: new Date().toISOString(),
      }));
    } catch {
      /* storage unavailable — planner still works, plan just won't carry over */
    }

    results.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  });

  // Initialize the license guidance.
  updateLicenseInfo();
})();