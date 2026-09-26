import { buildPie, isUsListed, parseRows, roundToTotal } from "./holdings.js";

const ETFS = [
  { t: "AVUV", name: "U.S. Small Cap Value" },
  { t: "AVDV", name: "International Small Cap Value" },
  { t: "AVEM", name: "Emerging Markets Equity" },
];
const STORE_KEY = "etf-pie-builder-v1";

// ---------- state ----------
const state = {
  holdings: {},   // t -> [{symbol, name, weight}]
  files: {},      // t -> file name
  errors: {},     // t -> message
  picks: {},      // t -> [symbols]
  n: 5,
  usOnly: false,
  method: "proportional",
  alloc: { AVUV: 33, AVDV: 33, AVEM: 33 },
  whole: true,
  tab: "AVUV",
};

function save() {
  try {
    const { errors, ...rest } = state;
    localStorage.setItem(STORE_KEY, JSON.stringify(rest));
  } catch { /* storage unavailable: app still works for this visit */ }
}
function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
    if (saved) Object.assign(state, saved, { errors: {} });
  } catch { /* ignore */ }
}

// ---------- helpers ----------
const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const etfColor = (t) => css(`--etf-${ETFS.findIndex((e) => e.t === t) + 1}`);
const pct = (x, d = 2) => `${(x * 100).toFixed(d)}%`;
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function eligible(t) {
  const rows = state.holdings[t] || [];
  return state.usOnly ? rows.filter((r) => isUsListed(r.symbol)) : rows;
}
function resetPicks(t) {
  state.picks[t] = eligible(t).slice(0, state.n).map((r) => r.symbol);
}
function pickedRows(t) {
  const set = new Set(state.picks[t] || []);
  return (state.holdings[t] || []).filter((r) => set.has(r.symbol));
}

function withAlpha(hex, a) {
  const n = parseInt(hex.replace("#", ""), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}
function plotLayout(extra = {}) {
  return {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "system-ui, -apple-system, Segoe UI, sans-serif", color: css("--ink-2"), size: 12 },
    margin: { l: 8, r: 8, t: 8, b: 8 },
    hoverlabel: { bgcolor: css("--surface"), bordercolor: css("--grid"), font: { color: css("--ink") } },
    ...extra,
  };
}

// ---------- file loading ----------
async function readFile(t, file) {
  try {
    if (!window.XLSX) throw new Error("Spreadsheet reader didn't load. Check your connection and refresh.");
    const wb = XLSX.read(await file.arrayBuffer(), { type: "array" });
    const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, raw: false, defval: "" });
    const holdings = parseRows(rows);
    if (!holdings.length) throw new Error("No holdings with a weight were found in this file.");
    state.holdings[t] = holdings;
    state.files[t] = file.name;
    delete state.errors[t];
    resetPicks(t);
    state.tab = t;
  } catch (e) {
    state.errors[t] = e.message || String(e);
  }
  save();
  render();
}

function demoHoldings(t, seed) {
  // Made-up tickers and weights, only for trying the page out
  let s = seed;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const suffix = { AVUV: [""], AVDV: ["", ".L", ".T", ".TO", ".AX"], AVEM: ["", ".TW", ".KS", ".HK", ".NS"] }[t];
  const rows = Array.from({ length: 40 }, (_, i) => {
    const sym = `${t.slice(2)}${String.fromCharCode(65 + (i % 26))}${i >= 26 ? "X" : ""}${suffix[i % suffix.length]}`;
    return { symbol: sym, name: `Demo Company ${sym}`, weight: (0.9 ** i) * (0.6 + rand()) * 0.03 };
  });
  return rows.sort((a, b) => b.weight - a.weight);
}

// ---------- rendering ----------
function renderSettings() {
  $("nPicks").value = state.n;
  $("nOut").textContent = state.n;
  $("usOnly").checked = state.usOnly;
  $("whole").checked = state.whole;
  document.querySelector(`input[name=method][value=${state.method}]`).checked = true;
  $("allocInputs").innerHTML = ETFS.map(({ t }) =>
    `<label>${t}<input type="number" min="0" max="100" step="1" value="${state.alloc[t] ?? 0}" data-etf="${t}"></label>`).join("");
}

function renderUploads() {
  $("uploads").innerHTML = ETFS.map(({ t, name }) => {
    const rows = state.holdings[t];
    const err = state.errors[t];
    const status = err ? `<span class="status err">⚠️ ${esc(err)}</span>`
      : rows ? `<span class="status">✅ ${esc(state.files[t] || "")} · ${rows.length} holdings</span>`
      : `<span class="status">Drop the CSV/Excel file here, or tap to choose.</span>`;
    return `<div class="drop ${rows ? "loaded" : ""}" data-etf="${t}">
      <span class="etf"><span class="dot" style="background:${etfColor(t)}"></span>${t}</span>
      <span class="fine">${name}</span>
      ${status}
      <input type="file" accept=".csv,.xlsx,.xls,text/csv" aria-label="Upload ${t} holdings file">
      ${rows ? `<button type="button" class="link clear" data-clear="${t}">Remove</button>` : ""}
    </div>`;
  }).join("");
}

function renderTabs() {
  $("tabs").innerHTML = ETFS.map(({ t, name }) =>
    `<button role="tab" aria-selected="${state.tab === t}" data-tab="${t}">${t} — ${name}</button>`).join("");
}

function renderPanel() {
  const t = state.tab;
  const rows = state.holdings[t];
  const panel = $("tabPanel");
  if (!rows) {
    panel.innerHTML = `<div class="empty">No holdings loaded for ${t} yet. Add its file in step 1.</div>`;
    return;
  }
  const picked = new Set(state.picks[t] || []);
  const elig = eligible(t);
  const shown = rows.slice(0, 60);
  const picks = pickedRows(t);
  const foreign = picks.filter((r) => !isUsListed(r.symbol)).map((r) => r.symbol);
  panel.innerHTML = `
    <div class="hold-grid">
      <div>
        <p class="fine">Top ${Math.min(25, rows.length)} of ${rows.length} holdings by weight in the fund. Colored bars are in your pie.</p>
        <div id="barChart" class="chart"></div>
      </div>
      <div>
        <p class="fine">Tick the stocks from ${t} to include.
          <button type="button" class="link" id="resetPicks">Reset to top ${state.n}</button></p>
        <div class="picklist">${shown.map((r, i) => `
          <label title="${esc(r.name)}">
            <input type="checkbox" data-sym="${esc(r.symbol)}" ${picked.has(r.symbol) ? "checked" : ""}>
            <span class="nm"><span class="sym">${i + 1}. ${esc(r.symbol)}${isUsListed(r.symbol) ? "" : " 🌍"}</span>${esc(r.name)}</span>
            <span class="w">${pct(r.weight)}</span>
          </label>`).join("")}</div>
        ${rows.length > shown.length ? `<p class="fine">Showing the top ${shown.length} of ${rows.length}.</p>` : ""}
        <div class="tiles hold-tiles">
          <div class="tile"><div class="k">Picked</div><div class="v">${picks.length} stocks</div></div>
          <div class="tile"><div class="k">Share of the fund</div><div class="v">${pct(picks.reduce((a, r) => a + r.weight, 0), 1)}</div></div>
        </div>
        ${elig.length < state.n ? `<p class="warn">ℹ️ Only ${elig.length} eligible holdings in this file.</p>` : ""}
        ${foreign.length ? `<p class="warn">🌍 Foreign listings, may not be buyable at a US brokerage: ${foreign.map(esc).join(", ")}.
          Look for a US ADR ticker (e.g. TSM for 2330.TW) or tick <i>Only US-listed</i>.</p>` : ""}
      </div>
    </div>`;

  const top = rows.slice(0, 25).reverse();
  if (window.Plotly) {
    Plotly.react("barChart", [{
      type: "bar", orientation: "h",
      x: top.map((r) => r.weight), y: top.map((r) => r.symbol),
      marker: { color: top.map((r) => (picked.has(r.symbol) ? etfColor(t) : css("--unpicked"))), cornerradius: 4 },
      text: top.map((r) => pct(r.weight)), textposition: "outside", cliponaxis: false,
      textfont: { color: css("--ink-2") },
      customdata: top.map((r) => r.name),
      hovertemplate: "<b>%{y}</b> · %{customdata}<br>%{x:.2%} of fund<extra></extra>",
    }], plotLayout({
      height: 70 + 22 * top.length, margin: { l: 8, r: 8, t: 8, b: 30 },
      xaxis: { tickformat: ".1%", range: [0, Math.max(...top.map((r) => r.weight)) * 1.3], gridcolor: css("--grid"), zeroline: false },
      yaxis: { ticksuffix: "  ", automargin: true, type: "category" },
      bargap: 0.25,
    }), { displayModeBar: false, responsive: true });
  }
}

function currentPie() {
  const picks = Object.fromEntries(ETFS.map(({ t }) => [t, pickedRows(t)]));
  const pie = buildPie(picks, state.alloc, state.method);
  const rounded = roundToTotal(pie.map((p) => p.pct), state.whole ? 0 : 2);
  const kept = pie.map((p, i) => ({ ...p, pct: rounded[i] })).filter((p) => p.pct > 0)
    .sort((a, b) => b.pct - a.pct);
  const dropped = pie.filter((p) => !kept.some((k) => k.symbol === p.symbol)).map((p) => p.symbol);
  return { pie: kept, dropped };
}

function renderPie() {
  const { pie, dropped } = currentPie();
  $("pieEmpty").hidden = pie.length > 0;
  $("pieBody").hidden = pie.length === 0;
  if (!pie.length) return;
  const fmt = (v) => (state.whole ? v.toFixed(0) : v.toFixed(2));
  const etfsUsed = new Set(pie.flatMap((p) => p.etfs));
  $("pieTiles").innerHTML = [
    ["Stocks in pie", pie.length],
    ["ETFs used", etfsUsed.size],
    [`Largest slice · ${fmt(pie[0].pct)}%`, esc(pie[0].symbol)],
    ["Total", `${fmt(pie.reduce((a, p) => a + p.pct, 0))}%`],
  ].map(([k, v]) => `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
  $("dropped").hidden = !dropped.length;
  $("dropped").textContent = `Rounded down to 0% and left out: ${dropped.join(", ")}. Untick "Round to whole percents" to keep them.`;

  $("pieTable").innerHTML = `<thead><tr><th>Symbol</th><th>Name</th><th>From</th><th class="num">In ETF</th><th class="num">Pie %</th></tr></thead>
    <tbody>${pie.map((p) => `<tr>
      <td><span class="dot" style="background:${etfColor(p.etfs[0])}"></span><b>${esc(p.symbol)}</b></td>
      <td>${esc(p.name)}</td><td>${p.etfs.join(", ")}</td>
      <td class="num">${pct(p.weightInEtf)}</td><td class="num"><b>${fmt(p.pct)}%</b></td></tr>`).join("")}</tbody>`;

  if (window.Plotly) {
    // Nested donut: inner ring = ETF share, outer ring = each stock
    const funds = ETFS.map((e) => e.t).filter((f) => etfsUsed.has(f));
    const outer = funds.flatMap((f) => pie.filter((p) => p.etfs[0] === f));
    const fundTotals = funds.map((f) => outer.filter((p) => p.etfs[0] === f).reduce((a, p) => a + p.pct, 0));
    const ring = { color: css("--surface"), width: 2 };
    Plotly.react("donut", [{
      type: "pie", hole: 0.62, sort: false, direction: "clockwise", rotation: 0,
      labels: outer.map((p) => p.symbol), values: outer.map((p) => p.pct),
      customdata: outer.map((p) => [p.name, p.etfs.join(", ")]),
      marker: { colors: outer.map((p) => withAlpha(etfColor(p.etfs[0]), 0.7)), line: ring },
      textinfo: "label", textposition: "inside", insidetextorientation: "radial",
      textfont: { color: "#ffffff" },
      hovertemplate: "<b>%{label}</b> · %{customdata[0]}<br>From %{customdata[1]} · %{value:.2f}% of pie<extra></extra>",
    }, {
      type: "pie", hole: 0.55, sort: false, direction: "clockwise", rotation: 0,
      domain: { x: [0.21, 0.79], y: [0.21, 0.79] },
      labels: funds, values: fundTotals,
      customdata: funds.map((f) => ETFS.find((e) => e.t === f).name),
      marker: { colors: funds.map(etfColor), line: ring },
      textinfo: "label", textposition: "inside", textfont: { color: "#ffffff" },
      hovertemplate: "<b>%{label}</b> · %{customdata}<br>%{value:.2f}% of pie<extra></extra>",
    }], plotLayout({ height: 460, showlegend: false }), { displayModeBar: false, responsive: true });
  }
}

function render() {
  renderSettings();
  renderUploads();
  renderTabs();
  renderPanel();
  renderPie();
}

// ---------- events ----------
function bind() {
  $("nPicks").addEventListener("input", (e) => {
    state.n = +e.target.value;
    ETFS.forEach(({ t }) => state.holdings[t] && resetPicks(t));
    save(); render();
  });
  $("usOnly").addEventListener("change", (e) => {
    state.usOnly = e.target.checked;
    ETFS.forEach(({ t }) => state.holdings[t] && resetPicks(t));
    save(); render();
  });
  $("whole").addEventListener("change", (e) => { state.whole = e.target.checked; save(); renderPie(); });
  document.querySelectorAll("input[name=method]").forEach((el) =>
    el.addEventListener("change", (e) => { state.method = e.target.value; save(); renderPie(); }));
  $("allocInputs").addEventListener("input", (e) => {
    const t = e.target.dataset.etf;
    if (!t) return;
    state.alloc[t] = Math.max(0, Math.min(100, +e.target.value || 0));
    save(); renderPie();
  });

  const uploads = $("uploads");
  uploads.addEventListener("change", (e) => {
    const drop = e.target.closest(".drop");
    if (drop && e.target.files?.[0]) readFile(drop.dataset.etf, e.target.files[0]);
  });
  uploads.addEventListener("click", (e) => {
    const t = e.target.dataset?.clear;
    if (!t) return;
    e.preventDefault();
    delete state.holdings[t]; delete state.files[t]; delete state.picks[t]; delete state.errors[t];
    save(); render();
  });
  ["dragenter", "dragover"].forEach((ev) => uploads.addEventListener(ev, (e) => {
    const d = e.target.closest(".drop");
    if (d) { e.preventDefault(); d.classList.add("over"); }
  }));
  ["dragleave", "drop"].forEach((ev) => uploads.addEventListener(ev, (e) => {
    const d = e.target.closest(".drop");
    if (!d) return;
    d.classList.remove("over");
    if (ev === "drop") {
      e.preventDefault();
      const f = e.dataTransfer?.files?.[0];
      if (f) readFile(d.dataset.etf, f);
    }
  }));

  $("demoBtn").addEventListener("click", () => {
    ETFS.forEach(({ t }, i) => {
      state.holdings[t] = demoHoldings(t, 97 + i * 31);
      state.files[t] = "demo data (not real)";
      delete state.errors[t];
      resetPicks(t);
    });
    save(); render();
  });

  $("tabs").addEventListener("click", (e) => {
    const t = e.target.closest("[data-tab]")?.dataset.tab;
    if (t) { state.tab = t; save(); renderTabs(); renderPanel(); }
  });
  $("tabPanel").addEventListener("change", (e) => {
    const sym = e.target.dataset?.sym;
    if (!sym) return;
    const t = state.tab;
    const set = new Set(state.picks[t] || []);
    e.target.checked ? set.add(sym) : set.delete(sym);
    state.picks[t] = [...set];
    save(); renderPanel(); renderPie();
  });
  $("tabPanel").addEventListener("click", (e) => {
    if (e.target.id === "resetPicks") { resetPicks(state.tab); save(); renderPanel(); renderPie(); }
  });

  $("copyBtn").addEventListener("click", async () => {
    const { pie } = currentPie();
    const text = pie.map((p) => `${p.symbol}\t${state.whole ? p.pct.toFixed(0) : p.pct.toFixed(2)}%`).join("\n");
    try { await navigator.clipboard.writeText(text); } catch {
      const ta = Object.assign(document.createElement("textarea"), { value: text });
      document.body.append(ta); ta.select(); document.execCommand("copy"); ta.remove();
    }
    $("copied").hidden = false;
    setTimeout(() => ($("copied").hidden = true), 1800);
  });
  $("csvBtn").addEventListener("click", () => {
    const { pie } = currentPie();
    const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
    const csv = ["Symbol,Name,From ETF,Weight in ETF,Pie %",
      ...pie.map((p) => [q(p.symbol), q(p.name), q(p.etfs.join(", ")), (p.weightInEtf * 100).toFixed(4), p.pct].join(","))].join("\n");
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: "my_pie.csv",
    });
    a.click(); URL.revokeObjectURL(a.href);
  });

  // Recolor charts when the OS theme flips
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
}

load();
bind();
// CDN scripts are deferred; render once they're in (module scripts also run after parsing)
if (document.readyState === "complete") render();
else window.addEventListener("load", render);
render();
