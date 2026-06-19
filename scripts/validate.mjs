#!/usr/bin/env node
import fs from "node:fs";
import vm from "node:vm";

const root = new URL("..", import.meta.url);
const args = new Set(process.argv.slice(2));
const withNetwork = args.has("--network");
const checks = [];
const ESPN_TEAMS = {
  ARI: 22, ATL: 1, BAL: 33, BUF: 2, CAR: 29, CHI: 3, CIN: 4, CLE: 5,
  DAL: 6, DEN: 7, DET: 8, GB: 9, HOU: 34, IND: 11, JAX: 30, KC: 12,
  LAC: 24, LAR: 14, LV: 13, MIA: 15, MIN: 16, NE: 17, NO: 18, NYG: 19,
  NYJ: 20, PHI: 21, PIT: 23, SEA: 26, SF: 25, TB: 27, TEN: 10, WAS: 28
};

function readText(path) {
  return fs.readFileSync(new URL(path, root), "utf8");
}

function readJson(path) {
  return JSON.parse(readText(path));
}

function pass(name, detail = "") {
  checks.push({ ok: true, name, detail });
}

function fail(name, detail) {
  checks.push({ ok: false, name, detail });
}

function assertCheck(name, condition, detail) {
  if (condition) pass(name, detail);
  else fail(name, detail);
}

async function checkIndex() {
  const html = readText("index.html");
  assertCheck("index.html exists", html.includes("<div id=\"root\"></div>"), "root mount found");
  assertCheck("Babel standalone pinned", /babel-standalone\/7\.23\.5\/babel\.min\.js/.test(html), "CDN version 7.23.5");
  const blocks = [...html.matchAll(/<script\s+type="text\/babel">([\s\S]*?)<\/script>/gi)].map(m => m[1]);
  assertCheck("text/babel block", blocks.length === 1, `${blocks.length} block(s)`);
  if (!blocks.length) return;

  const source = blocks.join("\n");
  assertCheck("news fallback removed", !source.includes("around the league:"), "player panels stay player-specific");
  assertCheck("global news wire present", source.includes("function GlobalNewsWire"), "general headlines are separate");
  assertCheck("integration status present", source.includes("function IntegrationStatus"), "runtime source status panel exists");
  assertCheck("identity coverage surface present", source.includes("function IdentityCoverage"), "join coverage report is visible");
  assertCheck("depth partial status present", source.includes("unmapped athlete"), "depth-chart degradation is labeled");

  const babelUrl = "https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.5/babel.min.js";
  const res = await fetch(babelUrl);
  if (!res.ok) throw new Error(`could not fetch Babel standalone (${res.status})`);
  const babelCode = await res.text();
  const sandbox = { console };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(babelCode, sandbox, { filename: "babel-standalone.js" });
  sandbox.Babel.transform(source, {
    filename: "index.html",
    presets: ["react"],
    sourceType: "script"
  });
  pass("Babel transform", "index.html JSX compiled");
}

function checkSignal() {
  const signal = readJson("data/signal.json");
  const players = signal && signal.players;
  const rows = players ? Object.values(players) : [];
  assertCheck("signal.json players", rows.length > 1000, `${rows.length} players`);
  assertCheck("signal.json meta", !!(signal.meta && signal.meta.backtest), "backtest metadata present");
  const usable = rows.filter(p => p && p.name && p.pos && p.season && typeof p.z_opp === "number" && typeof p.gap === "number");
  assertCheck("signal player shape", usable.length > 1000, `${usable.length} usable rows`);
}

function checkEspnIds() {
  const ids = readJson("data/espn_ids.json");
  const byName = ids.by_name || {};
  const byPosName = ids.by_pos_name || {};
  assertCheck("espn_ids by_name", Object.keys(byName).length > 1000, `${Object.keys(byName).length} names`);
  assertCheck("espn_ids by_pos_name", Object.keys(byPosName).length > 1000, `${Object.keys(byPosName).length} pos/name keys`);
}

function checkIdentityCoverage() {
  const cov = readJson("data/identity_coverage.json");
  const rows = Array.isArray(cov.rows) ? cov.rows : [];
  const bySource = cov.by_source || {};
  const shaped = rows.filter(r => r && r.source && r.season && r.position && r.join_method &&
    Number.isFinite(r.covered) && Number.isFinite(r.total) && Number.isFinite(r.pct));
  const sources = new Set(rows.map(r => r.source));
  assertCheck("identity_coverage rows", shaped.length >= 20, `${shaped.length} shaped rows`);
  assertCheck("identity_coverage by_source", Object.keys(bySource).length >= 3, `${Object.keys(bySource).length} sources`);
  assertCheck("identity_coverage sources", sources.has("signal.json") && sources.has("nflverse_snap") && sources.has("nflverse_air_yards"), [...sources].join(", "));
  assertCheck("identity_coverage priority gaps", Array.isArray(cov.priority_gaps), `${(cov.priority_gaps || []).length} gaps`);
}

async function fetchJson(name, url, predicate) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${name} returned ${res.status}`);
  const data = await res.json();
  assertCheck(name, predicate(data), "network shape ok");
}

async function checkNetwork() {
  await fetchJson("Sleeper state", "https://api.sleeper.app/v1/state/nfl", d => !!(d && d.season));
  await fetchJson("ESPN news", "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=5", d => Array.isArray(d.articles));
  const season = "2026";
  const failed = [];
  await Promise.all(Object.entries(ESPN_TEAMS).map(async ([abbr, id]) => {
    try {
      await fetchJson(`ESPN depth ${abbr}`, `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/${season}/teams/${id}/depthcharts?lang=en&region=us`, d => Array.isArray(d.items));
    } catch (e) {
      failed.push(`${abbr}:${id}`);
      fail(`ESPN depth ${abbr}`, e.message);
    }
  }));
  assertCheck("ESPN depth mappings", failed.length === 0, failed.length ? `failed ${failed.join(", ")}` : "32 teams");
  await fetchJson("ESPN stats sample", "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/4262921/stats", d => Array.isArray(d.categories));
  await fetchJson("ESPN gamelog sample", "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/4262921/gamelog?season=2025", d => !!d);
}

async function main() {
  await checkIndex();
  checkSignal();
  checkEspnIds();
  checkIdentityCoverage();
  if (withNetwork) await checkNetwork();
  else pass("network smoke checks", "skipped; run with --network");

  for (const c of checks) {
    console.log(`${c.ok ? "ok" : "FAIL"} ${c.name}${c.detail ? ` - ${c.detail}` : ""}`);
  }
  const bad = checks.filter(c => !c.ok);
  if (bad.length) {
    console.error(`\n${bad.length} validation check(s) failed.`);
    process.exit(1);
  }
}

main().catch(err => {
  console.error(`FAIL validation crashed - ${err.message}`);
  process.exit(1);
});
