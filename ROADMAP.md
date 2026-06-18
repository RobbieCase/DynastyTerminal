# DWR / Dynasty Terminal — Roadmap

Living backlog. Open items at top; shipped log at the bottom.

---

## Open / next

### A. Value-history backfill — decision pending
History **is** recoverable from DynastyProcess git history (~349 dated commits), but those are **FantasyPros-ECR-derived**, not FantasyCalc — a *parallel* series, not a clean backfill of our moat. Decide:
1. Build a separate DynastyProcess-derived historical series (instant multi-year trends for charts/watchlists, labeled as a different source), or
2. Keep FantasyCalc forward-only (one clean source, slow to deepen).
Recommendation: option 1 if we want multi-year visuals before the FantasyCalc series matures.

### B. Full mode-aware surfaces (in-season vs offseason)
The header **mode badge** ships (offseason / in-season · wk N, from Sleeper `/state/nfl`). Still to do: actually *switch* default surfaces and emphasis by phase —
- Offseason: trade market, rookie/pick analysis, historical trends, portfolio.
- In-season: lead with live game-to-game data, weekly usage, matchup context.
- Add the ESPN **gamelog** (game-by-game) to the stat tab for the in-season current row.
Can't be validated until the season; build the scaffolding, prove it in the fall.

### C. News — extensions
Per-player ESPN news ships. Follow-ups: a **global league-wide news wire**, injury surfacing, and **FAAB-bid monitoring** (news-driven adds) once leagues are synced.

### D. Trade verdict — deeper
Revealed-values basis + contention-window tilt ship. Next: scale the consolidation tax by the league's actual roster/bench/taxi settings (vs the current flat 4%/body), and ultimately let the revealed-preference solver *learn* the discount.

---

## In flight / blocked
- **Live-verify the revealed-preference solve** on a real league (needs a Sleeper username; client-side, no hardcoding).
- **Spine-side name-keying** for `signal.json` (deterministic join; spawned task).
- **Survival → value multiplier**: aging survival ships as context; a usable price multiplier needs a proper model (Cox w/ covariates), not just more years.
- **Vegas prop-implied points** — deferred to the season.
- **In-season lead-lag validation** — only provable once games are played.

---

## Shipped
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
- **News** — ESPN feed, entity/name-matched to the player, with an around-the-league fallback.
- **Year-by-year stat history** — ESPN athlete stats by season (`stat` tab), position-appropriate.
- **Mode badge** — offseason/in-season indicator from Sleeper state.
