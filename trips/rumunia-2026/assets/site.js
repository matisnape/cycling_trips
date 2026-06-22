/* Drobiazgi wspólne dla wszystkich stron. */
(function () {
  // delikatne wejście elementów .reveal (jeśli użytkownik nie wyłączył animacji)
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var items = document.querySelectorAll(".reveal");
  if (reduce || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("in"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    items.forEach(function (el) { io.observe(el); });
  }
  // rok w stopce
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();
})();
