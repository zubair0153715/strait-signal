/* Hormuz Watch — loads replay + live-context JSON, renders map + tables.
   No vessel data is fetched from anywhere at runtime: the vessel layer is
   the static historical-replay file. Live context comes from
   data/live_context.json, written by pipeline/fetch_live.py. */
(function () {
  "use strict";

  var map = L.map("map").setView([26.0, 57.0], 7);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // Schematic corridor outline — NOT for navigation.
  var corridor = [
    [27.5, 55.0], [27.5, 59.5], [25.0, 59.5], [25.0, 55.0], [27.5, 55.0]
  ];
  L.polygon(corridor, { color: "#0b2536", weight: 1.5, fillOpacity: 0.04, dashArray: "6 4" })
    .addTo(map)
    .bindPopup("<b>Strait of Hormuz corridor (schematic)</b><br>Detection bbox: 25.0–27.5°N, 55.0–59.5°E.<br>Not for navigation.");

  function fmt(n, digits) {
    return (n === null || n === undefined) ? "—" : Number(n).toFixed(digits);
  }

  function linkList(sources) {
    if (!sources || !sources.length) return "—";
    return "<ul>" + sources.map(function (s) {
      return '<li><a href="' + s.url + '" target="_blank" rel="noopener">' +
        escapeHtml(s.publisher) + "</a></li>";
    }).join("") + "</ul>";
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // ---- Historical replay ----
  fetch("data/historical_replay.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var tbody = document.querySelector("#events tbody");
      data.events.forEach(function (ev) {
        var vessels = ev.vessels.map(function (v) {
          return "<b>" + escapeHtml(v.name) + "</b> (IMO " + escapeHtml(v.imo) + ") — " +
            escapeHtml(v.class) + "; cargo: " + escapeHtml(v.cargo);
        }).join("<br>");
        var conf = "Collision: " + escapeHtml(ev.confidence.collision_occurred) +
          "<br>Position: " + escapeHtml(ev.confidence.position) +
          "<br>Shadow-fleet claim: " + escapeHtml(ev.confidence.shadow_fleet_characterization) +
          "<br>STS: " + escapeHtml(ev.confidence.sts_transfer);
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + escapeHtml(ev.event_id) + "</td>" +
          "<td>" + vessels + "</td>" +
          "<td>" + escapeHtml(ev.event_type) + "</td>" +
          "<td>" + escapeHtml(ev.occurred_at_utc) + "<br><span class='muted'>local: " +
          escapeHtml(ev.occurred_at_local) + "</span></td>" +
          "<td>" + fmt(ev.latitude, 4) + ", " + fmt(ev.longitude, 4) + "<br><span class='muted'>" +
          escapeHtml(ev.location_description) + "</span></td>" +
          "<td>" + conf + "</td>" +
          "<td>Outcome: " + escapeHtml(ev.outcome) +
          "<br>Official assessment: " + escapeHtml(ev.official_assessment) +
          "<br>Position source: " + escapeHtml(ev.position_source) +
          "<br>Sources:" + linkList(ev.sources) + "</td>";
        tbody.appendChild(tr);

        if (ev.latitude && ev.longitude) {
          L.marker([ev.latitude, ev.longitude], {
            icon: L.divIcon({
              className: "",
              html: '<div style="background:#d00;width:16px;height:16px;border-radius:50%;border:2px solid #fff;"></div>',
              iconSize: [16, 16]
            })
          }).addTo(map).bindPopup(
            "<b>" + escapeHtml(ev.event_id) + " — " + escapeHtml(ev.event_type) + "</b><br>" +
            escapeHtml(ev.occurred_at_utc) + "<br>" +
            escapeHtml(ev.vessels.map(function (v) { return v.name; }).join(" / ")) +
            "<br><i>Historical replay — not live. Not an STS event.</i>");
        }
      });
      var nc = document.getElementById("non-claims");
      nc.innerHTML = "<strong>Explicit non-claims for this replay set:</strong><ul>" +
        data.explicit_non_claims.map(function (c) { return "<li>" + escapeHtml(c) + "</li>"; }).join("") +
        "</ul><p class='muted'>" + escapeHtml(data.warning) + "</p>";
    })
    .catch(function (e) {
      document.querySelector("#events tbody").innerHTML =
        "<tr><td colspan='7'>Could not load data/historical_replay.json (" + escapeHtml(e.message) + "). Serve via run_demo.sh / a local web server — file:// may block fetch.</td></tr>";
    });

  // ---- Live keyless context ----
  fetch("data/live_context.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      document.getElementById("live-fetched").textContent =
        "— fetched " + (data.fetched_at_utc || "unknown") + " (UTC)";
      var wrap = document.getElementById("live-panels");

      data.marine_weather.forEach(function (w) {
        var card = document.createElement("div");
        card.className = "card";
        var m = w.marine || {}, wind = w.wind || {};
        card.innerHTML = "<h3>" + escapeHtml(w.waypoint.label) + "</h3>" +
          "<p><b>Sea state</b> (Open-Meteo Marine, " + escapeHtml(m.time_utc || "—") + "): " +
          "wave " + fmt(m.wave_height_m, 2) + " m, dir " + fmt(m.wave_direction_deg, 0) +
          "°, period " + fmt(m.wave_period_s, 1) + " s, SST " + fmt(m.sea_surface_temperature_c, 1) + " °C</p>" +
          "<p><b>Wind</b> (Open-Meteo Forecast, " + escapeHtml(wind.time_utc || "—") + "): " +
          fmt(wind.wind_speed_10m_kn, 1) + " kn, dir " + fmt(wind.wind_direction_10m_deg, 0) +
          "°, gusts " + fmt(wind.wind_gusts_10m_kn, 1) + " kn</p>" +
          "<p class='muted'>Waypoint: " + w.waypoint.lat + ", " + w.waypoint.lon +
          " · status: " + escapeHtml(w.status) + "</p>";
        wrap.appendChild(card);
        L.marker([w.waypoint.lat, w.waypoint.lon], {
          icon: L.divIcon({
            className: "",
            html: '<div style="background:#1a6fd4;width:14px;height:14px;border-radius:50%;border:2px solid #fff;"></div>',
            iconSize: [14, 14]
          })
        }).addTo(map).bindPopup("<b>" + escapeHtml(w.waypoint.label) + "</b><br>Live sea-state waypoint.");
      });

      var quakes = data.earthquakes || {};
      var qcard = document.createElement("div");
      qcard.className = "card";
      var qev = quakes.events_in_corridor || [];
      qcard.innerHTML = "<h3>Earthquakes in corridor (USGS, past 24h)</h3>" +
        "<p>Status: " + escapeHtml(quakes.status) + " · " +
        (qev.length ? qev.length + " event(s) in corridor." : "No earthquakes in corridor in the past 24h (normal).") +
        "</p>" + qev.map(function (q) {
          return "<p>M" + fmt(q.magnitude, 1) + " — " + escapeHtml(q.place) + " — " +
            escapeHtml(q.time_utc) + " — " + fmt(q.latitude, 2) + ", " + fmt(q.longitude, 2) + "</p>";
        }).join("");
      wrap.appendChild(qcard);
      qev.forEach(function (q) {
        L.marker([q.latitude, q.longitude], {
          icon: L.divIcon({
            className: "",
            html: '<div style="background:#e67e00;width:14px;height:14px;border-radius:50%;border:2px solid #fff;"></div>',
            iconSize: [14, 14]
          })
        }).addTo(map).bindPopup("<b>USGS earthquake M" + fmt(q.magnitude, 1) + "</b><br>" +
          escapeHtml(q.place) + "<br>" + escapeHtml(q.time_utc));
      });

      var gdacs = data.gdacs_alerts || {};
      var gcard = document.createElement("div");
      gcard.className = "card";
      var gev = gdacs.events || [];
      gcard.innerHTML = "<h3>GDACS disaster alerts (region)</h3>" +
        "<p>Status: " + escapeHtml(gdacs.status) + " · " +
        (gev.length ? gev.length + " alert(s) matching the region." : "No GDACS alerts for this region right now (normal).") +
        "</p>" + gev.map(function (g) {
          return "<p><a href='" + escapeHtml(g.link) + "' target='_blank' rel='noopener'>" +
            escapeHtml(g.title) + "</a> — " + escapeHtml(g.pub_date) + "</p>";
        }).join("");
      wrap.appendChild(gcard);
      gev.forEach(function (g) {
        if (g.latitude && g.longitude) {
          L.marker([g.latitude, g.longitude]).addTo(map)
            .bindPopup("<b>GDACS alert</b><br>" + escapeHtml(g.title));
        }
      });
    })
    .catch(function (e) {
      document.getElementById("live-panels").innerHTML =
        "<div class='card'>Live context unavailable: could not load data/live_context.json (" +
        escapeHtml(e.message) + "). Run <code>python3 pipeline/fetch_live.py</code> and serve via run_demo.sh.</div>";
    });
})();
