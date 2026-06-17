"""Run the spine: pull -> features -> backtest -> broad feed (+usage detail +comps) -> signal.json."""
import json, os, numpy as np, pandas as pd
from sklearn.neighbors import NearestNeighbors
from gridiron_spine import data, features, backtest, trade_solve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SEASONS = [2021, 2022, 2023, 2024, 2025]
FEATS = ["early_ppg", "z_opp"]
SIM_COLS = ["tgt", "tch", "rz", "shr", "car", "rush", "pas", "pts"]

def comps_for(feed_df, k=4):
    """Nearest-neighbour statistical comps within position, on standardized usage+production."""
    out = {}
    for pos, grp in feed_df.groupby("pos"):
        g = grp.reset_index(drop=True)
        X = g[SIM_COLS].values.astype(float)
        mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
        Xs = (X - mu) / sd
        n = min(k + 1, len(g))
        if n < 2:
            continue
        _, idx = NearestNeighbors(n_neighbors=n).fit(Xs).kneighbors(Xs)
        for i, nbrs in enumerate(idx):
            out[int(g.PlayerId.iloc[i])] = [
                {"name": g.name.iloc[j], "team": g.team.iloc[j], "pos": g.pos.iloc[j]}
                for j in nbrs[1:]]
    return out

def main():
    print("pulling weekly opportunity data (QB/RB/WR/TE)…")
    df = data.pull_weekly(SEASONS)
    print(f"  {len(df):,} player-weeks")

    d = features.build_player_season(df)
    print("=== walk-forward backtest (out-of-sample) ===")
    rep = {}
    for ts in [2024, 2025]:
        wf = backtest.walk_forward(d, FEATS, "late_ppg", train_max=ts - 1, test_season=ts)
        gap = backtest.evaluate_usage_gap(wf)
        rep[ts] = dict(n=wf["n"], r2_base=round(wf["r2_base"], 3), r2_full=round(wf["r2_full"], 3),
                       flag_improve_rate=round(gap["flag_improve_rate"], 3),
                       base_improve_rate=round(gap["base_improve_rate"], 3))
        print(f"  {ts}: buy-flag {gap['flag_improve_rate']:.1%} vs base {gap['base_improve_rate']:.1%}")
    sv = trade_solve.synthetic_validate()
    print(f"trade-solve self-test: Spearman {sv['spearman']:.3f}")

    feed_df = features.build_feed(df)
    feed_df["q"] = feed_df.groupby("pos")["gap"].transform(lambda s: s.quantile(0.75))
    comps = comps_for(feed_df)

    feed = {"meta": {"built_from": SEASONS, "backtest": rep, "trade_solve_selftest": sv,
                     "note": "join to Sleeper via players[].espn_id == key"},
            "players": {}}
    by_pos = {}
    for _, r in feed_df.iterrows():
        pid = int(r.PlayerId); by_pos[r["pos"]] = by_pos.get(r["pos"], 0) + 1
        feed["players"][str(pid)] = dict(
            name=r["name"], pos=r["pos"], team=r["team"], season=int(r.season),
            z_opp=round(float(r.z_opp), 2), gap=round(float(r.gap), 2),
            flag="buy" if r.gap >= r["q"] else None,
            m={c: round(float(r[c]), 1) for c in SIM_COLS},
            z={c: round(float(r["z_" + c]), 2) for c in SIM_COLS},
            comps=comps.get(pid, []))
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "signal.json"), "w") as f:
        json.dump(feed, f, indent=2)
    print(f"\nwrote data/signal.json — {len(feed['players'])} players, by pos {by_pos}")

if __name__ == "__main__":
    main()
