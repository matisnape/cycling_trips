/* Route map — Leaflet + Esri light gray canvas (Latin labels worldwide).
   Reads window.TRIP (from route-data.js) and optional window.MAP_DAY
   (day number on a subpage; absent = home page). */
(function () {
  if (typeof L === "undefined" || !window.TRIP) return;
  var el = document.getElementById("map");
  if (!el) return;

  var DAY = window.MAP_DAY || null;
  var t = window.TRIP;

  var map = L.map(el, { scrollWheelZoom: false, zoomControl: true });
  L.control.scale({ imperial: false }).addTo(map);

  // Esri's light gray canvas, no API key: a quiet basemap whose labels are in
  // Latin script everywhere, which OSM's own tiles are not — in Japan they are
  // written in Japanese. Base and labels are two separate layers.
  // (CARTO's Positron came first but started demanding a key, stamping
  // "API KEY REQUIRED" across every published map.)
  var ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_";
  var ESRI_ATTR = '&copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, ' +
                  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  var base = L.tileLayer(ESRI + "Base/MapServer/tile/{z}/{y}/{x}",
                         { attribution: ESRI_ATTR, maxZoom: 16 }).addTo(map);
  var labels = L.tileLayer(ESRI + "Reference/MapServer/tile/{z}/{y}/{x}",
                           { maxZoom: 16 }).addTo(map);

  // Safety net: if Esri ever stops serving these without a key, fall back to OSM
  // rather than leave a blank rectangle. A handful of errors in the first seconds
  // means the service is gone; one missing tile at the edge of the world does not.
  var bad = 0, since = Date.now();
  base.on("tileerror", function () {
    if (bad < 0 || Date.now() - since > 8000) return;
    if (++bad < 4) return;
    bad = -1;
    map.removeLayer(base);
    map.removeLayer(labels);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19
    }).addTo(map);
    map.getPane("tilePane").style.filter = "grayscale(0.85) contrast(0.95) brightness(1.06)";
  });

  // route line
  var line = L.polyline(t.route, {
    color: "#2f6e78", weight: 3, opacity: 0.85, lineJoin: "round", lineCap: "round"
  }).addTo(map);

  // points
  var dayPoints = [];
  t.pois.forEach(function (p) {
    var current = DAY && p.day === DAY;
    var dimmed = DAY && p.day !== DAY;
    var m = L.circleMarker([p.lat, p.lon], {
      radius: current ? 8 : (dimmed ? 4 : 6),
      color: "#fbfcfb",
      weight: 2,
      fillColor: dimmed ? "#9aa39d" : "#2f6e78",
      fillOpacity: dimmed ? 0.6 : 1,
      pane: current ? "markerPane" : undefined
    }).addTo(map);

    var link = (DAY && p.day === DAY) ? "" :
      '<br><a href="' + p.url + '">Dzień ' + p.day + ' &rarr;</a>';
    m.bindPopup(
      '<span class="pp-day">Dzień ' + p.day + '</span>' +
      "<b>" + p.name + "</b><br>" + p.blurb + link
    );
    m.bindTooltip(p.name, { direction: "top", offset: [0, -4], opacity: 0.9 });
    if (current) dayPoints.push([p.lat, p.lon]);
  });

  // framing
  if (DAY && dayPoints.length) {
    var b = L.latLngBounds(dayPoints).pad(0.6);
    map.fitBounds(b, { maxZoom: 11 });
  } else {
    map.fitBounds(line.getBounds(), { padding: [24, 24] });
  }

  // enable scroll-zoom only after click (so it doesn't hijack page scrolling)
  map.on("focus", function () { map.scrollWheelZoom.enable(); });
  map.on("blur", function () { map.scrollWheelZoom.disable(); });
})();
