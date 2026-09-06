// ---------- Customer site: mobile hamburger nav ----------
(function () {
  const toggle = document.getElementById("navToggle");
  const panel = document.getElementById("navPanel");
  const overlay = document.getElementById("navOverlay");
  if (!toggle || !panel) return;

  function closeNav() {
    panel.classList.remove("open");
    toggle.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
    if (overlay) overlay.classList.remove("open");
    document.body.classList.remove("no-scroll");
  }

  function openNav() {
    panel.classList.add("open");
    toggle.classList.add("open");
    toggle.setAttribute("aria-expanded", "true");
    if (overlay) overlay.classList.add("open");
    document.body.classList.add("no-scroll");
  }

  toggle.addEventListener("click", function () {
    if (panel.classList.contains("open")) {
      closeNav();
    } else {
      openNav();
    }
  });

  if (overlay) overlay.addEventListener("click", closeNav);

  // Close menu when a nav link is tapped (useful on mobile)
  panel.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", closeNav);
  });

  // Close on Escape key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeNav();
  });
})();

// ---------- Admin dashboard: mobile off-canvas sidebar ----------
(function () {
  const toggle = document.getElementById("adminToggle");
  const sidebar = document.getElementById("adminSidebar");
  const overlay = document.getElementById("adminOverlay");
  if (!toggle || !sidebar) return;

  function closeSidebar() {
    sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("open");
    document.body.classList.remove("no-scroll");
  }

  function openSidebar() {
    sidebar.classList.add("open");
    if (overlay) overlay.classList.add("open");
    document.body.classList.add("no-scroll");
  }

  toggle.addEventListener("click", function () {
    if (sidebar.classList.contains("open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  if (overlay) overlay.addEventListener("click", closeSidebar);
})();

// ---------- Quantity increment/decrement buttons (product/order pages) ----------
document.addEventListener("click", function (e) {
  if (e.target.matches("[data-qty-plus]")) {
    const input = document.querySelector(e.target.dataset.qtyPlus);
    if (input) input.value = Math.max(1, parseInt(input.value || 1) + 1);
  }
  if (e.target.matches("[data-qty-minus]")) {
    const input = document.querySelector(e.target.dataset.qtyMinus);
    if (input) input.value = Math.max(1, parseInt(input.value || 1) - 1);
  }
});
