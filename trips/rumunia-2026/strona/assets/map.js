/* Route map — Leaflet + CARTO Positron tiles (clean, light).
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

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd", maxZoom: 19
  }).addTo(map);

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
