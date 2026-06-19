# Dynasty Terminal Tab Product Outline

Standard format for each current app tab: what the tab is for, what data powers it, what metrics it exposes, and what needs to improve to reach the larger DWR vision.

The north star: DWR should not be a prettier API mirror. It should combine market prices, league behavior, usage signals, identity confidence, and time-series movement into decision-ready dynasty football judgment.

---

## `val` Value

### Purpose
- Primary player intelligence page.
- Shows the market price, DWR intrinsic v0, edge, revealed value context, usage signal, and aging context for the selected player.

### Data Sources
- Sleeper players API: player identity, team, position, age inputs, injury status, search universe.
- FantasyCalc current values: format-aware market value and 30-day trend.
- `data/signal.json`: usage z-score, usage gap, buy flag, snap share, air-yards share, comps, backtest metadata.
- Client-side revealed-preference solve: league-specific values from completed Sleeper trades, anchored to FantasyCalc.
- nflverse-derived aging curves emitted in `signal.json` metadata.

### Current Metrics
- Market value.
- FantasyCalc 30-day trend.
- DWR intrinsic v0: `market * age curve * momentum * usage-gap tilt`.
- Edge: `(intrinsic - market) / market`.
- Revealed value and revealed delta.
- Usage z/opportunity.
- Usage gap: opportunity z minus scoring z.
- Buy flag: top-quartile usage gap by position.
- Aging survival context.

### Needs Improvement
- Replace heuristic intrinsic v0 with validated position-specific value models.
- Add uncertainty/confidence bands to intrinsic, edge, sleeper, and revealed value.
- Make reason codes explicit: age, usage, role, trend, market liquidity, league behavior.
- Separate "market-anchored" from "directly solved" revealed values in every surface.
- Add stronger identity/source confidence labels beside each metric.
- Convert aging survival context into a validated value component only after proper modeling.

---

## `use` Usage

### Purpose
- Explain why a player has a usage signal.
- Show whether opportunity is running ahead of fantasy scoring.

### Data Sources
- `data/signal.json` from the Python spine.
- hvpkod weekly player data.
- nflverse snap share and air-yards share where joined.

### Current Metrics
- Usage z/opportunity by position.
- Usage gap.
- Raw usage metrics: targets, touches, red-zone usage, target share, carries, rushing yards, passing yards, fantasy points.
- Standardized metric bars by position.
- Snap share and air-yards share where available.

### Needs Improvement
- Improve snap and air-yards identity coverage before folding them into the backtested opportunity score.
- Add route participation, routes per dropback, designed rush share, and high-value touch rate.
- Split season-long usage from recent-week usage once in-season data is live.
- Add role-change detection: "last 3 weeks vs season baseline."
- Validate whether usage moves precede FantasyCalc value movement during the season.
- Show confidence when usage data is stale, sparse, or joined by weak name matching.

---

## `mkt` Market

### Purpose
- Show market history and current crowd price for the selected player.
- Distinguish market movement from DWR intrinsic or league revealed value.

### Data Sources
- FantasyCalc current values.
- Daily FantasyCalc snapshots accumulated on the orphan `data` branch.

### Current Metrics
- Current market value.
- 30-day FantasyCalc trend.
- Snapshot sparkline / historical market points when available.

### Needs Improvement
- Decide whether to add a parallel DynastyProcess/FantasyPros historical value series, clearly labeled as a different source.
- Add liquidity/coverage labels for thin-market players.
- Track value movement before and after news, depth, and usage events.
- Add market velocity, acceleration, and percentile rank within position/value tier.
- Add source comparison once multiple historical value sources exist.

---

## `comp` Comps

### Purpose
- Show statistically similar players by usage and production profile.
- Help the user reason from role profile rather than name-brand vibes.

### Data Sources
- `data/signal.json`.
- Python spine nearest-neighbor comps built from standardized usage and production metrics.
- Sleeper player map for clickable matching back to app players.

### Current Metrics
- Nearest-neighbor comps within position.
- Comp name, team, and position.
- Underlying standardized usage/production inputs from the spine.

### Needs Improvement
- Add comp similarity score and reason labels.
- Include historical outcome comps, not just same-season role twins.
- Add age, draft capital, and market-value context to comps.
- Show what happened to similar profiles over 4, 8, and 16 weeks.
- Separate "role comp" from "career/value trajectory comp."

---

## `news` Wire

### Purpose
- Show player-specific news matched from the ESPN NFL feed.
- Keep unrelated league headlines separate from player pages.

### Data Sources
- ESPN NFL news API.
- ESPN athlete/entity tags when present.
- Name fallback matching against the selected player.

### Current Metrics
- Matched article title.
- Published date.
- Source/description snippet.
- Article link.

### Needs Improvement
- Classify news by type: injury, depth-chart move, contract, suspension, coach quote, transaction.
- Measure which news classes historically predict value movement.
- Add confidence for entity-tag vs name-text match.
- Connect news events to value, usage, and depth changes.
- Avoid treating news as signal unless role/usage/depth confirms it.

---

## `scr` Screener

### Purpose
- Cross-player mispricing board.
- Find players whose price, usage, edge, revealed value, and sleeper profile diverge.

### Data Sources
- Sleeper players API.
- FantasyCalc current values.
- `data/signal.json`.
- Client-side revealed-preference solve from synced league trades.

### Current Metrics
- Sleeper score: MVP 0-100 target score.
- Market value.
- Edge.
- Revealed delta.
- Usage z/opportunity.
- Usage gap.
- Buy flag.
- Position and name filters.
- Sleeper and buy-flag filters.

### Needs Improvement
- Backtest the sleeper score itself against future value movement and future production.
- Split sleeper score into reason-code components visible in the UI.
- Add confidence/coverage for every row.
- Add price-tier filters: cheap stash, mid-market breakout, premium buy.
- Add roster availability and manager ownership once a league is synced.
- Add alerting when a player newly crosses sleeper, edge, or usage thresholds.
- Learn score weights from historical outcomes instead of fixed MVP weights.

---

## `wl` Watchlist

### Purpose
- Personal portfolio tracker for players the user cares about.
- Convert the value time-series into a daily monitoring surface.

### Data Sources
- LocalStorage watchlist.
- Sleeper players API.
- FantasyCalc current values.
- `data/signal.json`.
- FantasyCalc snapshot series from the `data` branch.

### Current Metrics
- Current market value.
- Edge.
- Usage gap.
- Value movement since tracked.

### Needs Improvement
- Add event cards: value move, new buy flag, depth change, news match, usage change.
- Store the exact tracking baseline date/value per player.
- Add watchlist notes, target price, and roster context.
- Add alert thresholds and daily summary.
- Make watchlist the default offseason home surface.
- Connect tracked players to trade targets and manager ownership.

---

## `trd` Trade

### Purpose
- Turn values and signals into concrete trade construction.
- Compare offer sides using market or revealed basis and roster-window tilt.

### Data Sources
- Sleeper synced league: rosters, users, transactions, draft-pick ledger.
- FantasyCalc current values.
- Client-side revealed-preference solve.
- `data/signal.json`.
- Saved league/team state in LocalStorage.

### Current Metrics
- Give/get side totals.
- Verdict: fair, overpay, win value.
- Market or revealed basis.
- Contention-window tilt.
- Buy-low target score.
- Roster need by position.
- Owned picks and estimated pick values.
- Trade partner roster browser.

### Needs Improvement
- Learn roster-pressure/consolidation costs from actual drop/replacement context.
- Add manager preference fingerprints only when sample size supports it.
- Model pick values by projected finish, class year, league format, and revealed league discounts.
- Suggest full offer structures, not just target names.
- Explain why the other manager might accept.
- Add trade confidence and comparable accepted trades.
- Validate revealed trade values against future accepted trades.

---

## `sim` Season

### Purpose
- Estimate playoff/title odds for a synced league.
- Contextualize pick values, contention windows, and team direction.

### Data Sources
- Sleeper synced league rosters.
- Sleeper matchups/schedule.
- FantasyCalc roster value when available.
- Sleeper current record fallback.

### Current Metrics
- Monte Carlo playoff probability.
- Monte Carlo title probability.
- Team strength based on roster value or record.

### Needs Improvement
- Use player projections, injuries, bye weeks, and weekly lineup strength.
- Model lineup slots and replacement level rather than full-roster value only.
- Tie pick values to projected finish distribution.
- Add contender/rebuild classification.
- Show team fragility and positional exposure.
- Backtest sim calibration against real league outcomes.

---

## `lg` My League

### Purpose
- Sync and persist the user's Sleeper league.
- Provide roster browsing and revealed-value computation.

### Data Sources
- Sleeper user lookup.
- Sleeper user leagues by season.
- Sleeper league rosters/users/settings.
- Sleeper transactions across current and previous league IDs.
- FantasyCalc current values.
- LocalStorage saved league and revealed solves.

### Current Metrics
- Team market value / power ranking.
- Team record.
- Roster player list.
- Revealed values beta: trades, seasons, solved count, market-anchored count.
- Revealed-vs-market deltas for solved players.

### Needs Improvement
- Add league-level source/status panel: transactions loaded, seasons followed, solved coverage.
- Show revealed-value confidence by player and asset type.
- Add league behavior summaries: position premiums, pick discounts, age preferences, consolidation tendency.
- Persist solve history and show deltas over time.
- Support multiple saved leagues cleanly.
- Add league construction analysis: surplus, need, age curve, pick runway, contention window.

---

## `depth` Depth Chart

### Purpose
- Inspect team depth charts and connect external ESPN depth data back to Sleeper players.
- Support role/path-to-playing-time analysis.

### Data Sources
- ESPN team depth-chart API.
- Sleeper players API.
- `data/espn_ids.json` identity map.
- ESPN athlete lookup fallback for unmapped athletes.
- FantasyCalc current values for player prices.

### Current Metrics
- Depth rank/slot.
- Team and position grouping.
- Market value per player when available.
- Partial/unmapped athlete labels.

### Needs Improvement
- Validate all 32 team mappings during the season.
- Add role semantics: slot WR, third-down RB, goal-line RB, receiving TE, backup QB.
- Compare ESPN depth with Sleeper team/position and news/usage reality.
- Track depth changes over time.
- Feed depth changes into watchlist alerts and sleeper score.
- Add identity confidence on each matched/unmatched athlete.

---

## `?` Guide

### Purpose
- Explain the terminal's data sources, source status, and metric definitions.
- Build user trust by labeling what is market, DWR, revealed, or third-party.

### Data Sources
- Runtime app state.
- `data/identity_coverage.json`.
- `data/signal.json`.
- Sleeper/FantasyCalc/ESPN availability checks.

### Current Metrics
- Integration status.
- Identity coverage rows and priority gaps.
- Glossary definitions for market, intrinsic, edge, sleeper, usage, buy flag, comps, revealed values.

### Needs Improvement
- Turn guide/status into a compact trust layer available from every tab.
- Add per-metric provenance badges.
- Add confidence language to model outputs.
- Add validation/backtest summaries readable by non-technical users.
- Keep FantasyCalc, DWR intrinsic, and revealed-preference language strictly separated.

---

## Cross-Tab Grand Vision Work

### Data Spine
- Move identity guards and source confidence out of frontend-only logic into spine artifacts.
- Split raw, normalized, features, model, and app-output data artifacts.
- Add source scorecards and conflict reports.
- Improve snap, air-yards, ESPN id, and name-join coverage before leaning harder on those fields.

### Modeling
- Replace intrinsic v0 and sleeper MVP weights with validated models.
- Backtest against future production, future market movement, and blended dynasty utility.
- Add uncertainty bands and reason codes.
- Track model drift by position, age bucket, value tier, and season phase.

### Revealed Preference
- Validate on multiple real leagues.
- Persist solve history by league/season.
- Add coverage and confidence counts.
- Learn pick discounts, position premiums, age preferences, and package preferences.
- Compare solved values against future accepted trades.

### Product Modes
- Offseason default: portfolio, trades, rookies, picks, value movement, league construction.
- In-season default: weekly usage, depth changes, injuries, game logs, matchup context, lead-lag validation.
- Watchlist should become the daily home surface, with alerts and explanations.

### Decision Surfaces
- Convert signals into actions: target manager, rationale, expected price, offer structure, confidence.
- Show when the model does not know enough.
- Prefer fewer, better recommendations over more sortable columns.

