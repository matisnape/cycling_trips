/* Phrasebook: pin the phrases you actually use, count how often, keep them on top.
   Opt-in per page with  phrasebook = true  in that [[pages]] block of trip.toml.

   Everything lives in localStorage, so it is per browser and per trip. Nothing is
   written into the page, which means a browser with JavaScript switched off — the
   Files preview on an iPhone, for one — shows the phrasebook exactly as authored. */
(function () {
  var box = document.querySelector(".phrasebook");
  if (!box) return;

  var KEY = "gp-phr:" + (box.getAttribute("data-pk") || "x");
  var S = { pin: [], n: {} };
  try {
    var raw = window.localStorage && localStorage.getItem(KEY);
    if (raw) { var p = JSON.parse(raw); if (p && typeof p === "object") S = p; }
  } catch (e) {}
  S.pin = S.pin || [];
  S.n = S.n || {};
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} }

  // One table row = one phrase. The Polish cell is its id: stable as long as the
  // wording does not change, and readable in storage.
  var rows = [], byId = {};
  Array.prototype.forEach.call(box.querySelectorAll("table tr"), function (tr) {
    if (tr.getElementsByTagName("th").length || tr.cells.length < 2) return;
    var id = (tr.cells[0].textContent || "").trim();
    if (!id || byId[id]) return;
    var r = { id: id, tr: tr };
    rows.push(r); byId[id] = r;
  });
  if (!rows.length) return;

  // "Moje" goes above the first category, not in place of it: the categories keep
  // their order, so nothing moves around under your finger while you read.
  var top = document.createElement("section");
  top.className = "phr-top";
  top.innerHTML =
    '<h3>Moje<span class="phr-hint">im częściej używasz, tym wyżej</span></h3>' +
    '<table><tbody></tbody></table>' +
    '<p class="phr-foot"><button type="button" class="phr-clear">Wyczyść listę</button></p>';
  box.insertBefore(top, box.firstChild);
  var tbody = top.querySelector("tbody");

  function pinned(id) { return S.pin.indexOf(id) !== -1; }

  function star(id, big) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "phr-star" + (big ? " big" : "");
    b.setAttribute("aria-pressed", pinned(id) ? "true" : "false");
    b.title = pinned(id) ? "Usuń z „Moich”" : "Dodaj do „Moich”";
    b.textContent = pinned(id) ? "★" : "☆";
    b.addEventListener("click", function () {
      var i = S.pin.indexOf(id);
      if (i === -1) S.pin.push(id); else S.pin.splice(i, 1);
      save(); paint();
    });
    return b;
  }

  function paint() {
    // stars in the categories
    rows.forEach(function (r) {
      var old = r.tr.cells[0].querySelector(".phr-star");
      if (old) old.parentNode.removeChild(old);
      r.tr.cells[0].insertBefore(star(r.id), r.tr.cells[0].firstChild);
    });

    // "Moje": most used first, ties in the order they were pinned
    var mine = S.pin.filter(function (id) { return byId[id]; });
    mine.sort(function (a, b) {
      var d = (S.n[b] || 0) - (S.n[a] || 0);
      return d || S.pin.indexOf(a) - S.pin.indexOf(b);
    });
    tbody.innerHTML = "";
    mine.forEach(function (id) {
      var src = byId[id].tr, tr = document.createElement("tr");
      tr.setAttribute("data-id", id);
      for (var i = 0; i < src.cells.length; i++) {
        var td = document.createElement("td");
        td.innerHTML = src.cells[i].innerHTML;
        var s = td.querySelector(".phr-star");
        if (s) s.parentNode.removeChild(s);
        tr.appendChild(td);
      }
      tr.cells[0].insertBefore(star(id, true), tr.cells[0].firstChild);

      var td2 = document.createElement("td");
      td2.className = "phr-use";
      var use = document.createElement("button");
      use.type = "button";
      use.className = "phr-plus";
      use.setAttribute("aria-label", "Użyłam tego zwrotu");
      use.innerHTML = '<span class="phr-n">' + (S.n[id] || 0) + "</span>+";
      use.addEventListener("click", function () {
        S.n[id] = (S.n[id] || 0) + 1;
        save(); paint();
        // the row may have jumped a few places; a short flash says where it went
        var moved = tbody.querySelector('tr[data-id="' + id.replace(/"/g, '\\"') + '"]');
        if (moved) {
          moved.className = "phr-just";
          setTimeout(function () { moved.className = ""; }, 700);
        }
      });
      td2.appendChild(use);
      tr.appendChild(td2);
      tbody.appendChild(tr);
    });
    top.style.display = mine.length ? "" : "none";
  }

  top.querySelector(".phr-clear").addEventListener("click", function () {
    if (!S.pin.length) return;
    S.pin = []; S.n = {};
    save(); paint();
  });

  paint();
})();
