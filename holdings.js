// Holdings parsing and pie math: the browser twin of etf_dashboard/holdings.py.
// Pure functions, no DOM, so they can be tested with Node.

const SYMBOL_COLS = ["ticker", "symbol", "stock ticker", "ticker symbol"];
const NAME_COLS = ["name", "security name", "security", "description", "holding", "holding name", "company"];
const WEIGHT_COLS = ["weight", "% of net assets", "% net assets", "percent of net assets", "% of fund",
  "% weight", "weighting", "holding percent", "% of assets", "market value %", "portfolio %"];
const NON_STOCK = /\b(?:cash|usd|dollar|future|futures|swap|money market|repo|fx|currency|receivable|payable)\b/i;

function matches(cell, names) {
  const c = String(cell ?? "").replace(/\s+/g, " ").trim().toLowerCase();
  return names.includes(c) || names.some((n) => n.length > 4 && c.includes(n));
}

function findHeaderRow(rows) {
  for (let i = 0; i < Math.min(rows.length, 30); i++) {
    const cells = rows[i].filter((v) => v !== null && v !== undefined && String(v).trim() !== "");
    if (cells.some((c) => matches(c, WEIGHT_COLS)) &&
        cells.some((c) => matches(c, SYMBOL_COLS) || matches(c, NAME_COLS))) return i;
  }
  throw new Error("Couldn't find a header row with a weight column (e.g. 'Weight' or '% of Net Assets').");
}

/** rows: array of arrays of cell values (from a CSV or spreadsheet). Returns cleaned holdings. */
export function parseRows(rows) {
  const h = findHeaderRow(rows);
  const header = rows[h].map((c) => String(c ?? "").trim());
  const col = (names) => header.findIndex((c) => matches(c, names));
  const w = col(WEIGHT_COLS), s = col(SYMBOL_COLS), n = col(NAME_COLS);
  if (s < 0 && n < 0) throw new Error("Couldn't find a ticker/symbol or name column.");
  let out = rows.slice(h + 1).map((r) => ({
    symbol: s >= 0 ? r[s] : "",
    name: n >= 0 ? r[n] : r[s],
    weight: parseFloat(String(r[w] ?? "").replace(/[%,\s$]/g, "")),
  })).filter((r) => Number.isFinite(r.weight));
  // Issuers report either 5.2 (percent) or 0.052 (fraction)
  const total = out.reduce((a, r) => a + r.weight, 0);
  if (total > 2) out = out.map((r) => ({ ...r, weight: r.weight / 100 }));
  return clean(out);
}

/** Normalize text, drop cash/derivative lines, merge duplicate symbols, sort by weight. */
export function clean(rows) {
  const merged = new Map();
  for (const r of rows) {
    let symbol = String(r.symbol ?? "").trim().toUpperCase();
    if (symbol === "NAN" || symbol === "-") symbol = "";
    const name = String(r.name ?? "").trim();
    const weight = Number(r.weight);
    if (!(weight > 0) || (!symbol && !name)) continue;
    if (!symbol && NON_STOCK.test(name)) continue;
    if (["CASH", "USD", "CASH_USD"].includes(symbol)) continue;
    if (!symbol) symbol = name.toUpperCase().slice(0, 12);
    const prev = merged.get(symbol);
    if (prev) prev.weight += weight;
    else merged.set(symbol, { symbol, name, weight });
  }
  return [...merged.values()].sort((a, b) => b.weight - a.weight);
}

/** Yahoo-style suffixes (.TW, .L, .KS…) mean a foreign listing; plain tickers are US-listed. */
export function isUsListed(symbol) {
  return /^[A-Z]{1,5}([.-][A-B])?$/.test(symbol);
}

/**
 * picks:  { ETF: [{symbol, name, weight}] } chosen stocks per fund
 * alloc:  { ETF: number } share of the pie per fund (any scale; normalized)
 * method: "proportional" | "equal"
 * Returns [{symbol, name, etfs, weightInEtf, pct}] sorted by pct, summing to 100.
 */
export function buildPie(picks, alloc, method = "proportional") {
  const funds = Object.keys(picks).filter((f) => picks[f].length && (alloc[f] ?? 0) > 0);
  const totalAlloc = funds.reduce((a, f) => a + alloc[f], 0);
  const bySymbol = new Map();
  for (const f of funds) {
    const share = alloc[f] / totalAlloc;
    const sum = picks[f].reduce((a, r) => a + r.weight, 0);
    for (const r of picks[f]) {
      const within = method === "proportional" ? r.weight / sum : 1 / picks[f].length;
      const prev = bySymbol.get(r.symbol);
      if (prev) {
        prev.pct += share * within * 100;
        prev.etfs.push(f);
        prev.weightInEtf = Math.max(prev.weightInEtf, r.weight);
      } else {
        bySymbol.set(r.symbol, { symbol: r.symbol, name: r.name, etfs: [f], weightInEtf: r.weight,
          pct: share * within * 100 });
      }
    }
  }
  return [...bySymbol.values()].sort((a, b) => b.pct - a.pct);
}

/** Round so the result still sums exactly to `total` (largest-remainder method). */
export function roundToTotal(values, decimals = 0, total = 100) {
  const scale = 10 ** decimals;
  const sum = values.reduce((a, v) => a + v, 0);
  if (!sum) return values.map(() => 0);
  const raw = values.map((v) => (v / sum) * total * scale);
  const floored = raw.map(Math.floor);
  let short = Math.round(total * scale - floored.reduce((a, v) => a + v, 0));
  const order = raw.map((v, i) => [v - floored[i], i]).sort((a, b) => b[0] - a[0]);
  for (let k = 0; k < short; k++) floored[order[k][1]] += 1;
  return floored.map((v) => v / scale);
}
