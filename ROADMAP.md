# DWR / Dynasty Terminal — Roadmap

Living backlog. Newest direction at top; "shipped" log at the bottom for context.

---

## 1. Trade terminal

### 1a. Smarter fill-needs (prioritize buy-low up-and-comers, not just big names)
Today: fill-needs ranks pool players by `FantasyCalc value × 1.06 if buy-flag` and takes the top of your weak positions ([index.html](index.html) `ranked`/`targets`). This surfaces the *most expensive* names, not the best *gets*.

Want: rank by a **buy-low / up-and-comer score**, not raw market value. Proposed composite (all available in `signal.json` + Sleeper):
- **usage gap** `z_opp − z_pts` (the backtested signal — opportunity ahead of scoring) — primary.
- **buy flag** (top-quartile gap) — boost.
- **snap-share** level/trend (nflverse) — rising role.
- **age** — favor ascending players.
- **market value** — *invert* lightly so we surface under-priced risers, not established stars.

Render each suggestion with the "why" (gap, snap%, age) so it's legible. This is "how to analyze up-and-comers": a player whose usage/role is climbing while market value hasn't caught up.

### 1b. Position sections in fill-needs
Add **ALL / QB / RB / WR / TE** sub-tabs to the suggestions list, each showing buy-low candidates for that position (not just the two weak spots). Bump list length **top 6 → top 8**.

### 1c. Verdict upgrade
Note copy fixed (was claiming a "chunk-2 feed" that's stale). Current verdict = FantasyCalc give-vs-get within an 8% band + 4%/extra-body consolidation tax; the buy signal only tilts *suggestions*, not the verdict. Roadmap:
- Fold the league's **revealed-preference values** (now live in the `lg` tab) into the verdict when available, falling back to market.
- Add **contention-window weighting** (your team's compete-now vs rebuild posture should reweight youth vs production).

---

## 2. Value history — backfill beyond what we've stored?
FantasyCalc's API is **current-only** (no history) — that's exactly why `snapshot.py` accumulates the daily moat. The stored series only goes back to its first run (2026-06-17).

**Open question / to investigate:** third-party *open* historical dynasty-value datasets we could backfill from:
- **DynastyProcess** (`github.com/dynastyprocess/data`) — publishes historical value tables; reachable from the Action.
- KeepTradeCut — has history but no free API.
- FantasyPros / others — mostly paywalled.

If a compatible source exists, one-time backfill the `data/values/` branch so the time-series, sparklines, and any mispricing-over-time work start with real depth instead of forward-only. If not, the moat stays forward-accumulating (still valuable, just slower).

---

## 3. News section
Build the `news` surface (currently a stub):
- Aggregate RSS / sports feeds (ESPN, Rotowire, NFL.com, beat writers).
- **Keyword/entity match to players** (name + team) so each player view shows their relevant news, and a global wire shows league-wide.
- Tie into FAAB monitoring (who's getting bid on, news-driven adds).
- Reachability: RSS/news fetch likely needs the Action or a CORS-friendly source — confirm before building client-side.

---

## 4. Watchlists / Portfolio tracking  ← makes the moat clock visible
Daily-driver feature. "Show me the players I'm tracking and how their intrinsic value changed over time."
- Track an arbitrary set of players (localStorage, like `dwr_myleague`).
- Per-player value sparkline + deltas from the `data` branch snapshots (the `PriceHistory` plumbing already exists — generalize it to a list).
- This is where the value time-series stops being an internal asset and becomes the reason to open DWR daily. **High priority** — it's the visible payoff of the moat.

---

## 5. Eventual overhaul — modes + deep stats

### 5a. Offseason vs in-season modes (auto-switch as the season approaches)
- **Offseason mode:** trade-market monitoring, rookie-draft analysis, pick valuation, historical value trends, league portfolio management, revealed-preference market, news/FAAB.
- **In-season mode:** live game-to-game data, weekly usage updates, lineup/matchup context.
- Auto-detect from the NFL calendar (Sleeper `state`/season type) and switch the default surface.

### 5b. Year-by-year player stat history
- Click into a player → full season-by-season stat history.
- In-season: updates game-by-game.
- Data: hvpkod weekly (2021+) + nflverse `stats_player_week` (deep history, already wired for aging/air-yards).

---

## Previously identified / in flight
- **Live-verify the revealed-preference solve** on a real league (needs a Sleeper username; client-side, no hardcoding).
- **Spine-side name-keying** for `signal.json` (deterministic join; tracked as a spawned task).
- **Survival → value multiplier**: aging survival shipped as context; a usable price multiplier needs a proper model (Cox w/ covariates), not just more years.
- **Vegas prop-implied points** — deferred to the season (props go live, de-vig).
- **In-season lead-lag validation** — can only be proven once games are played (fall).

---

## Shipped (recent)
- Moat-clock fix (snapshots on orphan `data` branch); screener; pick auto-derivation; `signal.json` name-join fix (buy flags); nflverse snap + air-yards (display); gap-aware intrinsic/edge; value-history sparkline; **client-side revealed-preference trade-solve**; KM survival aging (context) fit on deep 2010–25 history.
