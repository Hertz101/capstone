(() => {
  "use strict";

  // Form elements
  const form = document.getElementById("huntForm");
  const speciesInput = document.getElementById("species");
  const methodInput = document.getElementById("method");
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
  // License guidance
  // ----------------------------------------
  function updateLicenseInfo() {
    const answer = licenseInput.value;

    licenseInfo.classList.add("d-none");

    if (!answer) {
      return;
    }

    licenseInfo.classList.remove("d-none");
    licenseLink.href = CPW_LICENSE_URL;

    if (answer === "yes") {
      licenseTitle.textContent = "Check your license details";
      licenseDescription.textContent =
        "Confirm your license or application is valid for your species, GMU, season, method, and dates. This selection does not verify eligibility.";
      licenseLink.textContent = "Review CPW License Options";
    } else if (answer === "no") {
      licenseTitle.textContent = "Find the license you need";
      licenseDescription.textContent =
        "Review current Colorado Parks and Wildlife license requirements, application options, deadlines, and restrictions.";
      licenseLink.textContent = "Visit CPW License Shop";
    } else if (answer === "unsure") {
      licenseTitle.textContent = "Not sure which license applies?";
      licenseDescription.textContent =
        "Check current CPW regulations and license information for your species, hunt area, season, and method.";
      licenseLink.textContent = "Check CPW License Information";
    }
  }

  licenseInput.addEventListener("change", updateLicenseInfo);

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

    const licenseText = {
      yes: "Yes — verify license and hunt eligibility",
      no: "No — review license requirements",
      unsure: "Unsure — check CPW license information"
    }[licenseAnswer] || "Check CPW license information";

    summary.replaceChildren();

    addSummaryItem("Species", species);
    addSummaryItem("Hunting method", method);
    addSummaryItem("Game Management Unit", `GMU ${gmu}`);
    addSummaryItem("License status", licenseText);

    const note = document.createElement("li");
    note.className = "list-group-item small text-muted";
    note.textContent =
      "This is a preliminary planning summary, not confirmation of a valid tag, season, legal method, access permission, or hunt eligibility. Verify current CPW regulations and land access before hunting.";

    summary.appendChild(note);

    results.classList.remove("d-none");

    results.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  });

  // Initialize the license guidance.
  updateLicenseInfo();
})();