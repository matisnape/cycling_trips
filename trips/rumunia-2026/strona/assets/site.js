/* Drobiazgi wspólne dla wszystkich stron. */
(function () {
  // rok w stopce
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();

  // Podgląd na żywo: tylko lokalnie (localhost). Co 1,5 s sprawdza znacznik
  // wersji; gdy build.py --watch przebuduje stronę, przeglądarka sama się odświeży.
  // Na GitHub Pages (host *.github.io) ten kod się nie uruchamia.
  var host = location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    var last = null;
    setInterval(function () {
      fetch("assets/_buildid.txt?_=" + Date.now(), { cache: "no-store" })
        .then(function (r) { return r.ok ? r.text() : null; })
        .then(function (v) {
          if (v == null) return;
          if (last === null) last = v;
          else if (v !== last) location.reload();
        })
        .catch(function () {});
    }, 1500);
  }
})();
