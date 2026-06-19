# DWR / Dynasty Terminal — Roadmap

Living backlog. Open items at top; shipped log at the bottom.

---

## Open / next

### Prioritized sprint list

Factored from `PROJECT_OUTLINE.md` priorities plus the live backlog below. Number order is the recommended execution order.

#### Sprint 1 — Trust: news, source labels, and empty states
Goal: remove the highest-risk trust problems first.
- Fix player-news empty states: matched player news only; unrelated headlines move to a separate global wire.
- Audit FantasyCalc/DWR/revealed/intrinsic language so market anchors are not described as proprietary value.
- Add source/status labels to value, news, ESPN depth, stats/gamelogs, nflverse usage, and signal panels.

Done when:
- A player with no matched headlines shows only a clean empty state.
- User can tell which source powers each major value/stat/depth panel.
- FantasyCalc is consistently labeled as market input, not DWR's own value engine.

#### Sprint 2 — Platform: validation harness and integration status
Goal: make the buildless app safer to keep shipping.
- Add a repeatable validation script for Babel syntax and core data-shape checks.
- Smoke-check `data/signal.json`, `data/espn_ids.json`, ESPN stats/gamelogs, ESPN depth charts, and news matching behavior.
- Add a small integration status panel in the guide/footer.
- Document the Vite migration trigger before adding the next major surface.

Done when:
- Core data artifacts and parser assumptions can be checked before deploy.
- Known integration failures surface as status, not silent UI weirdness.
- The build/no-build decision has a documented boundary.

#### Sprint 3 — Depth + identity coverage
Goal: make provider joins auditable before leaning harder on model outputs.
- Validate all 32 ESPN depth-chart mappings.
- Decide whether WR should expose ESPN's slot/rank structure as WR1/WR2/slot.
- Show partial/unmapped athlete status when ESPN depth data degrades.
- Add an identity coverage report by source, season, position, and join method.

Done when:
- Depth charts have explicit fallback/partial-source indicators.
- Join coverage gaps are visible instead of hidden inside player matching.
- The highest-value missing joins are obvious enough to prioritize.

#### Sprint 4 — Revealed-value hardening
Goal: turn the existing trade solver into an inspectable value surface.
- Live-verify revealed-preference solves on real Sleeper leagues.
- Persist solved league values by league/season and show coverage/confidence counts.
- Expose revealed-vs-market deltas on player pages, screener rows, and trade verdicts.
- Improve trade verdict consolidation tax using actual roster/bench/taxi settings.

Done when:
- Revealed values are inspectable, labeled, and clearly separated from market values.
- Coverage explains number of trades, solved players, and market-anchored players.
- Trade verdicts reflect league-specific roster pressure, not a flat body count.

#### Sprint 5 — Historical value and moat clock
Goal: deepen value history without confusing sources.
- Decide whether to build the DynastyProcess/FantasyPros-derived historical value series as a separately labeled parallel chart.
- If approved, add it as historical context only, not a FantasyCalc backfill.
- Use the parallel series in charts/watchlists where long-term trend context matters.

Done when:
- Historical charts do not imply a false FantasyCalc backfill.
- Users can distinguish FantasyCalc current/forward snapshots from DynastyProcess-derived history.
- Watchlist and player trend views have a clear long-range option if the series ships.

#### Sprint 6 — Offseason home mode
Goal: make saved leagues open into the offseason jobs-to-be-done.
- Make offseason mode default toward watchlist, screener, trade market, picks, and league portfolio.
- Add watchlist event cards for value moves, new buy/sell flags, depth changes, matched news, and usage changes.
- Show "why changed" explanations instead of only changed numbers.

Done when:
- Saved leagues open into an offseason-useful workflow instead of a generic terminal view.
- Watchlist changes are explainable at a glance.
- Portfolio movement feels active enough to justify daily use.

#### Sprint 7 — Trade market monitor
Goal: convert model edges into concrete trade targets.
- Highlight players whose market/intrinsic/revealed values diverge.
- Show who rosters them, roster fit for the user's team, and likely contention-window logic.
- Add partner roster context and buy-low/sell-high explanations to the monitor.

Done when:
- The user can move from an edge signal to a target manager and rationale.
- Trade ideas explain value basis, roster need, and contention fit.
- Screener, trade terminal, and league roster views tell the same story.

#### Sprint 8 — Pick and rookie center
Goal: make picks less opaque and prepare for rookie draft workflows.
- Add pick provenance and confidence.
- Tie pick value to projected finish / sim outcomes where possible.
- Add rookie board scaffolding with class tiers, league format context, and draft runway.
- Start learning pick discounts from revealed trades once enough trades exist.

Done when:
- Picks show confidence/provenance instead of a single opaque value.
- Pick values react to league context and projected finish.
- Rookie/pick work has a dedicated surface, not scattered helper copy.

#### Sprint 9 — In-season weekly mode
Goal: make weekly usage and market movement test the lead-lag thesis once games return.
- Switch in-season defaults toward weekly usage, game logs, news/injury context, matchup context, and live value movement.
- Add weekly role-change summaries from snaps, routes, targets, and opportunity gap.
- Track whether usage movement precedes value movement during the season.

Done when:
- The mode badge changes actual surface priority, not just header copy.
- Weekly player views explain role movement before market movement.
- Lead-lag validation produces an auditable seasonal report.

#### Sprint 10 — Vegas and live validation
Goal: add prop-implied signals only when the season data is stable enough.
- Add Vegas prop-implied points after lines are live and technically reachable.
- De-vig props and compare to market/intrinsic/revealed values.
- Fold results into the in-season validation report without overstating signal strength.

Done when:
- Prop-implied values are labeled, source-aware, and separable from DWR values.
- In-season reports compare usage, props, and market movement honestly.
- The feature can be disabled cleanly when lines are unavailable.

### A. News — bug fix + source expansion
Bug: when a player has no matched news, the player news panel currently populates around-the-league / random articles. That is misleading.

Fix:
- If a player has no matched news, show a clean empty state: "no recent matched headlines."
- Do **not** show unrelated articles inside a player-specific news panel.
- If we want general headlines, put them in a separately labeled global news wire.

Expansion:
- Pull in news from other prominent sports news websites beyond ESPN where feasible.
- Likely sources to investigate: NFL.com, CBS Sports, Yahoo, Rotoworld/NBC, The Athletic headlines if legally/reachably available, team sites.
- Many sources will block browser CORS; if so, build an Action-side `data/news.json` aggregator.
- Eventually: identify reliable beat reporters and pull from their accounts/feed endpoints, then keyword/entity-match to players and teams.

### B. Value-history backfill — decision pending
History **is** recoverable from DynastyProcess git history (~349 dated commits), but those are **FantasyPros-ECR-derived**, not FantasyCalc — a *parallel* series, not a clean backfill of our moat. Decide:
1. Build a separate DynastyProcess-derived historical series (instant multi-year trends for charts/watchlists, labeled as a different source), or
2. Keep FantasyCalc forward-only (one clean source, slow to deepen).
Recommendation: option 1 if we want multi-year visuals before the FantasyCalc series matures.

### C. Full mode-aware surfaces (in-season vs offseason)
The header **mode badge** ships (offseason / in-season · wk N, from Sleeper `/state/nfl`). Still to do: actually *switch* default surfaces and emphasis by phase —
- Offseason: trade market, rookie/pick analysis, historical trends, portfolio.
- In-season: lead with live game-to-game data, weekly usage, matchup context.
Can't be validated until the season; build the scaffolding, prove it in the fall.

### D. Trade verdict — deeper
Revealed-values basis + contention-window tilt ship. Next: scale the consolidation tax by the league's actual roster/bench/taxi settings (vs the current flat 4%/body), and ultimately let the revealed-preference solver *learn* the discount.

### E. Depth charts — quality follow-up
ESPN is now the primary source for team depth charts, with Sleeper as fallback. Remaining follow-up:
- Validate all 32 ESPN team-id mappings after deployment.
- Decide whether WR should display ESPN's slot/rank structure more explicitly (WR1/WR2/slot) instead of a single flattened list.
- Add a small source/status label per team when ESPN returns partial or unmapped athletes.

---

## In flight / blocked
- **Live-verify the revealed-preference solve** on a real league (needs a Sleeper username; client-side, no hardcoding).
- **Spine-side name-keying** for `signal.json` (deterministic join; spawned task).
- **Survival → value multiplier**: aging survival ships as context; a usable price multiplier needs a proper model (Cox w/ covariates), not just more years.
- **Vegas prop-implied points** — deferred to the season.
- **In-season lead-lag validation** — only provable once games are played.

---

## Shipped
- **Validation harness + integration status** — `node scripts/validate.mjs` checks JSX/Babel transform, core data shapes, and optional ESPN/Sleeper smoke checks; the app now shows runtime source status in the guide/footer.
- **Moat-clock fix** — value snapshots on the orphan `data` branch (local pushes can't clobber).
- **Screener** — sortable mispricing board over the universe.
- **Pick auto-derivation** — owned picks from Sleeper's traded-pick ledger, format-scaled.
- **signal.json name-join fix** — repaired buy flags app-wide (was espn_id-keyed, ~0 hits).
- **nflverse snap + air-yards** (display) — incl. the stats_player air-yards source fix.
- **Gap-aware intrinsic/edge** — edge reflects the backtested usage gap, not just the age tier.
- **Value-history sparkline** — player market tab, from the `data` branch snapshots.
- **Client-side revealed-preference trade-solve** — solves your synced league's real trades (no league id hardcoded).
- **KM survival aging** (context) — fit on deep 2010–25 nflverse history; "aging outlook" panel.
- **Trade 1a/1b** — buy-low fill-needs (gap + flag + snap + youth − price), ALL/QB/RB/WR/TE tabs, top 8, with "why".
- **Trade 1c** — verdict value-basis (market | revealed) + contention-window tilt; **fixed an inverted verdict** (give vs get).
- **Consolidation tax fix** — counts real roster bodies only (picks & throw-ins excluded), capped.
- **Watchlists / portfolio tracking** — ☆ any player; board of edge/gap/value + "since tracked" deltas. The moat clock, personal.
- **News v0** — ESPN feed, entity/name-matched to the player. Known bug remains: player panels should not fall back to unrelated league headlines.
- **Trade partner roster browser** — in the trade feature, click another manager and add players from their roster to **I get**.
- **League tab saved-state view** — saved league opens directly in `lg`; click teams to inspect rosters; change-league path preserved.
- **League season selector** — defaults to 2026 with a dropdown back to 2020 instead of a free-text season field.
- **Year-by-year stat history** — ESPN athlete stats by season, position-appropriate, now opened from the player header next to `yoe` instead of a standalone tab.
- **Game-by-game stat logs** — click a season row inside stat history to expand ESPN regular-season game logs for that player/year.
- **ESPN depth charts** — depth view now uses ESPN team depth charts as primary source, matched back to Sleeper by ESPN id / `data/espn_ids.json`; Sleeper depth is fallback only.
- **Mode badge** — offseason/in-season indicator from Sleeper state.
