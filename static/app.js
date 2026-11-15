// Rotation Explorer front end: reads the inputs, asks the Python server, draws the results.

const RULE_TITLES = {
  1: "Fallow before wheat", 4: "Wind erosion", 5: "Forage timing", 7: "Soil pH",
  8: "Canola", 9: "Cereal root disease", 10: "Water erosion", 11: "Soil carbon",
  interval: "Disease break",
};
const LEVEL_NAMES = { block: "Blocked", warning: "Warning", caution: "Caution", info: "Note" };
const SCORE_NAMES = { yield: "Typical grain", dry_years: "Dry-year grain", soil: "Soil", risk: "Low risk" };
const CUSTOM = "custom";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => Number(n).toLocaleString("en-US");

let options, map, marker;
let point = { lat: 0, lon: 0 };
let timer, requestId = 0;

// ---------- Inputs ----------
function option(value, label) {
  const o = document.createElement("md-select-option");
  o.setAttribute("value", value);
  o.innerHTML = `<div slot="headline">${esc(label)}</div>`;
  return o;
}

async function setSelect(select, value) {
  await customElements.whenDefined("md-outlined-select");
  await select.updateComplete;
  select.value = value;
}

function buildYears(length) {
  const box = $("years");
  box.innerHTML = "";
  const defaults = options.default_rotations[length];
  for (let i = 0; i < length; i++) {
    const s = document.createElement("md-outlined-select");
    s.label = `Year ${i + 1}`;
    s.className = "year";
    options.crops.forEach((c) => s.append(option(c.key, c.name)));
    s.addEventListener("change", schedule);
    box.append(s);
    setSelect(s, defaults[i]);
  }
}

function readInputs() {
  const weights = {};
  for (const key of Object.keys(SCORE_NAMES)) weights[key] = Number($(`w-${key}`).value);
  let soil_ph = null;
  if ($("has-test").selected) {
    const v = parseFloat($("ph").value);
    if (v >= 3.5 && v <= 9) soil_ph = v;
  }
  const rotation = [...document.querySelectorAll("#years md-outlined-select")].map((s) => s.value);
  return { lat: point.lat, lon: point.lon, rotation, soil_ph, weights };
}

function moveTo(lat, lon, zoom) {
  point = { lat: Number(lat), lon: Number(lon) };
  if (!map) return;
  marker.setLatLng([point.lat, point.lon]);
  if (zoom) map.setView([point.lat, point.lon], zoom);
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(run, 300);
}

// ---------- Server ----------
async function run() {
  const body = readInputs();
  if (body.rotation.some((c) => !c)) return;
  const id = ++requestId;
  $("loading").hidden = false;
  $("error").hidden = true;
  try {
    const res = await fetch("/api/analyse", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await res.json();
    if (id !== requestId) return;               // a newer request has started
    if (!res.ok) throw new Error(data.detail || "Request failed");
    render(data, body);
  } catch (err) {
    if (id !== requestId) return;
    $("error").textContent = err.message;
    $("error").hidden = false;
  } finally {
    if (id === requestId) $("loading").hidden = true;
  }
}

// ---------- Drawing ----------
function chip(text, cls = "", title = "") {
  return `<span class="chip ${cls}"${title ? ` title="${esc(title)}"` : ""}>${esc(text)}</span>`;
}

function render(d, input) {
  const z = d.zone;
  $("stats").innerHTML = [
    ["Rainfall zone", z.zone.charAt(0).toUpperCase() + z.zone.slice(1), ""],
    ["Precipitation", fmt(z.mean_precip_mm), "mm/yr"],
    ["Frost-free", Math.round(d.frost_free_days), "days"],
    ["Hot days", Math.round(d.hot_days), "≥ 30 °C"],
  ].map(([label, value, unit]) =>
    `<div class="stat"><div class="label">${label}</div><div class="value">${esc(value)}<span class="unit">${unit}</span></div></div>`
  ).join("");

  const split = Object.entries(z.years_per_zone).map(([k, v]) => `${k} ${v}`).join(", ");
  const chips = [chip(`${Math.round(z.share_of_years_in_zone * 100)}% of years in this zone`, "",
    `Crop years ${d.first_year}-${d.last_year}: ${split}`)];
  if (!d.calibrated) {
    chips.push(chip("Yield estimate: rough", "warn",
      `${d.mean_inches} in/yr is outside the 9.5-13.8 in the WSU yield equations were fitted on.`));
  }
  if (d.soil) {
    const s = d.soil;
    chips.push(chip(s.map_unit.split(",")[0], "", `${s.map_unit}. ${s.soil}, ${s.share_pct}% of map unit.`));
    if (s.slope_pct != null) chips.push(chip(`Slope ${s.slope_pct}%`, "", "Typical slope of the soil map unit"));
    if (s.organic_matter_pct != null) chips.push(chip(`Organic matter ${s.organic_matter_pct}%`));
    if (s.survey_ph != null) chips.push(chip(`Survey pH ${s.survey_ph}`, "soft",
      "Typical for this soil type, not your field today. Add a soil test for pH checks."));
  } else {
    chips.push(chip("Soil data unavailable", "warn", d.soil_error || "No soil mapped at this point."));
  }
  $("chips").innerHTML = chips.join("");

  // Shared scale for the grain bars, padded so the ends are not at the edges.
  const lo = Math.min(...d.results.map((r) => r.grain_p10));
  const hi = Math.max(...d.results.map((r) => r.grain_p90));
  const pad = Math.max((hi - lo) * 0.08, 1);
  const axis = { lo: Math.max(0, lo - pad), hi: hi + pad };
  $("cards").innerHTML = d.results.map((r, i) => card(r, i + 1, axis, input.soil_ph)).join("");
}

function card(r, rank, axis, ph) {
  const pct = (v) => `${(100 * (v - axis.lo) / (axis.hi - axis.lo)).toFixed(1)}%`;
  const crops = r.rotation.map((key, i) => {
    const name = r.name.split(" → ")[i];
    return `<span class="step">${i ? '<span class="arrow" aria-hidden="true">›</span>' : ""}<span class="crop${key === "fallow" ? " fallow" : ""}">${esc(name)}</span></span>`;
  }).join("");

  const scores = Object.entries(SCORE_NAMES).map(([k, label]) => {
    const v = Math.max(0, Math.min(1, r.scores[k]));
    return `<div class="score-row"><span>${label}</span><span class="meter"><i style="width:${v * 100}%"></i></span><span class="num">${r.scores[k].toFixed(2)}</span></div>`;
  }).join("");

  const flags = [
    ...r.not_modelled.map((c) => chip(`${c}: no yield data`, "soft", "Counted as zero, so this rotation's grain is understated.")),
    ...r.weak_yield_evidence.map((c) => chip(`${c}: 1 farm, 1 year`, "soft", "Yield ratio from one WSU farm in 2023. Weak evidence.")),
    ...(r.capped_yields ? [chip("Wheat at yield cap", "soft", "Winter wheat hits the 101 bu/acre regional cap in most years, so dry and good years look alike.")] : []),
  ].join("");

  const counts = {};
  r.notes.forEach((n) => { counts[n.level] = (counts[n.level] || 0) + 1; });
  const summary = ["block", "warning", "caution", "info"].filter((l) => counts[l])
    .map((l) => `<span class="level ${l}">${counts[l]} ${LEVEL_NAMES[l]}</span>`).join("") || "No flags";
  const notes = r.notes.map((n) => `
    <li class="${n.level}">
      <span class="level ${n.level}">${LEVEL_NAMES[n.level]}</span><span class="title">${esc(RULE_TITLES[n.rule] || "Note")}</span>
      <div class="msg">${esc(n.message)}</div>
      <div class="src">${esc(n.source)}</div>
    </li>`).join("");

  return `
  <article class="card${r.is_current ? " current" : ""}${r.blocked ? " blocked" : ""}">
    <div class="card-top">
      <div class="rank"><span class="rank-num">${rank}</span>${r.is_current ? '<span class="tag">Current</span>' : ""}</div>
      <div class="score"><div class="value">${r.total.toFixed(2)}</div><div class="label">Score</div></div>
    </div>
    ${r.blocked ? `<div class="blocked-banner">Not suitable at soil pH ${esc(ph)}</div>` : ""}
    <div class="seq">${crops}</div>
    <p class="reason">${esc(r.reason)}${r.reason_source ? `<span class="source">${esc(r.reason_source)}</span>` : ""}</p>
    <div class="range" title="Grain per hectare per year, all fields of the rotation averaged">
      <div class="head"><span>Grain, kg/ha/yr</span><span>${r.years} years</span></div>
      <div class="track"><span class="bar" style="left:${pct(r.grain_p10)};width:calc(${pct(r.grain_p90)} - ${pct(r.grain_p10)})"></span><span class="dot" style="left:${pct(r.grain_p50)}"></span></div>
      <div class="nums"><span>Dry <b>${fmt(r.grain_p10)}</b></span><span>Typical <b>${fmt(r.grain_p50)}</b></span><span>Good <b>${fmt(r.grain_p90)}</b></span></div>
    </div>
    <div class="scores">${scores}</div>
    ${flags ? `<div class="chips">${flags}</div>` : ""}
    <details><summary>${summary}</summary><ul class="notes">${notes}</ul></details>
  </article>`;
}

// ---------- Start ----------
async function start() {
  options = await (await fetch("/api/options")).json();
  const site = $("site");
  options.sites.forEach((s) => site.append(option(s.name, s.name)));
  site.append(option(CUSTOM, "Custom point"));
  const first = options.sites[0];
  point = { lat: first.lat, lon: first.lon };

  map = L.map("map", { scrollWheelZoom: false }).setView([first.lat, first.lon], 8);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  marker = L.circleMarker([first.lat, first.lon], {
    radius: 9, color: "#ffffff", weight: 3, fillColor: "#1650c7", fillOpacity: 1,
  }).addTo(map);
  map.on("click", (e) => {
    setSelect(site, CUSTOM);
    $("coords").hidden = false;
    $("lat").value = e.latlng.lat.toFixed(4);
    $("lon").value = e.latlng.lng.toFixed(4);
    moveTo(e.latlng.lat, e.latlng.lng);
    schedule();
  });

  await setSelect(site, first.name);
  site.addEventListener("change", () => {
    const custom = site.value === CUSTOM;
    $("coords").hidden = !custom;
    if (custom) {
      $("lat").value = point.lat.toFixed(4);
      $("lon").value = point.lon.toFixed(4);
      return;
    }
    const s = options.sites.find((x) => x.name === site.value);
    moveTo(s.lat, s.lon, 9);
    schedule();
  });
  for (const id of ["lat", "lon"]) {
    $(id).addEventListener("change", () => {
      const lat = parseFloat($("lat").value), lon = parseFloat($("lon").value);
      if (Number.isFinite(lat) && Number.isFinite(lon)) { moveTo(lat, lon, 9); schedule(); }
    });
  }

  await setSelect($("length"), "2");
  buildYears(2);
  $("length").addEventListener("change", () => { buildYears(Number($("length").value)); schedule(); });

  $("has-test").addEventListener("change", () => { $("ph").hidden = !$("has-test").selected; schedule(); });
  $("ph").addEventListener("input", schedule);
  for (const key of Object.keys(SCORE_NAMES)) {
    const slider = $(`w-${key}`);
    slider.addEventListener("input", () => { $(`v-${key}`).textContent = slider.value; });
    slider.addEventListener("change", schedule);
  }

  setTimeout(run, 50);
}

start().catch((err) => {
  $("error").textContent = `Could not start: ${err.message}`;
  $("error").hidden = false;
});
