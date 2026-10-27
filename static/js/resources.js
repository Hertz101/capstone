// Resources page: expandable hero cards.
// Clicking a card's hero toggles its body; opening one closes the others.

document.querySelectorAll(".resource-card").forEach((card) => {
  const hero = card.querySelector(".resource-hero");
  const body = card.querySelector(".resource-body");
  if (!hero || !body) return;

  hero.addEventListener("click", () => {
    const isOpen = !body.hidden;

    // Collapse every open card first (accordion behavior).
    document.querySelectorAll(".resource-card.open").forEach((other) => {
      if (other === card) return;
      other.classList.remove("open");
      const otherBody = other.querySelector(".resource-body");
      const otherHero = other.querySelector(".resource-hero");
      if (otherBody) otherBody.hidden = true;
      if (otherHero) otherHero.setAttribute("aria-expanded", "false");
    });

    body.hidden = isOpen;
    card.classList.toggle("open", !isOpen);
    hero.setAttribute("aria-expanded", String(!isOpen));
    if (!isOpen) {
      body.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });
});
