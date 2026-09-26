import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { buildPie, clean, isUsListed, parseRows, roundToTotal } from "../../site/holdings.js";

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
const csvRows = (text) => text.trim().split("\n").map((l) => l.match(/("[^"]*"|[^,]*)(,|$)/g)
  .map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "")));

test("parses issuer CSV with title rows, skips cash", () => {
  const rows = csvRows(readFileSync(new URL("../fixtures/sample_holdings.csv", import.meta.url), "utf8"));
  const h = parseRows(rows);
  assert.deepEqual(h.map((r) => r.symbol), ["AAA", "BBB", "CCC", "2330.TW", "DDD"]);
  near(h[0].weight, 0.052);
  assert.equal(h[0].name, "Alpha Corp");
});

test("fraction weights stay fractions", () => {
  const h = parseRows([["Symbol", "Name", "Weight"], ["X", "Ex", "0.4"], ["Y", "Why", "0.6"]]);
  assert.deepEqual(h.map((r) => r.symbol), ["Y", "X"]);
});

test("missing weight column throws", () => {
  assert.throws(() => parseRows([["Symbol", "Name"], ["X", "Ex"]]));
});

test("clean merges duplicate symbols", () => {
  const h = clean([{ symbol: "a", name: "A1", weight: 0.01 }, { symbol: "A", name: "A2", weight: 0.02 },
    { symbol: "B", name: "B", weight: 0.025 }]);
  assert.deepEqual(h.map((r) => r.symbol), ["A", "B"]);
  near(h[0].weight, 0.03);
});

test("isUsListed", () => {
  assert.ok(isUsListed("AAPL") && isUsListed("BRK-B"));
  assert.ok(!isUsListed("2330.TW") && !isUsListed("005930.KS") && !isUsListed("RIO.L"));
});

const picks = () => ({
  F1: [{ symbol: "A", name: "a", weight: 0.03 }, { symbol: "B", name: "b", weight: 0.01 }],
  F2: [{ symbol: "C", name: "c", weight: 0.02 }],
});

test("buildPie proportional", () => {
  const p = Object.fromEntries(buildPie(picks(), { F1: 50, F2: 50 }).map((r) => [r.symbol, r.pct]));
  near(p.A, 37.5); near(p.B, 12.5); near(p.C, 50);
});

test("buildPie equal, normalizes allocation", () => {
  const p = buildPie(picks(), { F1: 2, F2: 1 }, "equal");
  p.forEach((r) => near(r.pct, 100 / 3));
});

test("buildPie merges a stock held by two funds", () => {
  const pk = picks();
  pk.F2 = [{ symbol: "A", name: "a", weight: 0.02 }];
  const a = buildPie(pk, { F1: 50, F2: 50 }).find((r) => r.symbol === "A");
  near(a.pct, 87.5);
  assert.deepEqual(a.etfs, ["F1", "F2"]);
});

test("roundToTotal sums to 100", () => {
  const r = roundToTotal([33.333, 33.333, 33.334]);
  assert.equal(r.reduce((a, v) => a + v, 0), 100);
  const r2 = roundToTotal(Array(7).fill(1), 2);
  near(r2.reduce((a, v) => a + v, 0), 100);
});
