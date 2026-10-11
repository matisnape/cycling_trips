/* Small bits shared across all pages. */
(function () {
  // year in the footer
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();

  // Live preview: local only (localhost). Every 1.5s it checks the version
  // marker; when build.py --watch rebuilds the site, the browser refreshes itself.
  // On GitHub Pages (host *.github.io) this code does not run.
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
