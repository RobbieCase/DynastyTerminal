"""Feature construction — position-appropriate opportunity, two products:

  build_player_season() : early-window features vs late-window outcome, for the
                          point-in-time BACKTEST (no peeking; outcome window excluded).
  build_feed()          : each player's MOST RECENT qualifying season, season-long
                          usage-vs-scoring read, for the live terminal feed. Broad
                          coverage — any player who logged a recent season shows.

Opportunity is defined per position because "opportunity" means different things:
  QB  -> passing volume + rush volume (designed-run value matters in dynasty)
  RB  -> touches + carries + red-zone work
  WR  -> targets + target share + red-zone targets
  TE  -> same as WR
"""
import pandas as pd, numpy as np

METRICS = ["tgt", "tch", "rz", "shr", "car", "rush", "pas", "pts", "snap", "ay"]
# base opportunity is always available (hvpkod). nflverse cols (z_snap = snap share,
# z_ay = air-yards share) are appended per position ONLY when that metric has real
# data this run — so the signal upgrades on the Action and reverts cleanly in a sandbox.
BASE_OPP_BY_POS = {
    "QB": ["z_pas", "z_car", "z_rush"],
    "RB": ["z_tch", "z_car", "z_rz"],
    "WR": ["z_tgt", "z_shr", "z_rz"],
    "TE": ["z_tgt", "z_shr", "z_rz"],
}
EXTRA_OPP_BY_POS = {"QB": [], "RB": ["z_snap"], "WR": ["z_snap", "z_ay"], "TE": ["z_snap", "z_ay"]}

def _z(s):
    sd = s.std()
    return (s - s.mean()) / sd if sd and sd > 0 else s * 0.0

def _agg(g):
    return dict(
        tgt=g.Targets.mean(), tch=g.Touches.mean(), rz=g.RzTarget.mean(),
        shr=g.tgt_share.mean(), car=g.TouchCarries.mean(), rush=g.RushingYDS.mean(),
        pas=g.PassingYDS.mean(), pts=g.TotalPoints.mean(), n=len(g),
        snap=g["snap"].mean() if "snap" in g.columns else 0.0,
        ay=g["ay"].mean() if "ay" in g.columns else 0.0,
    )

def _add_z_opp(d):
    for c in METRICS:
        if c in d.columns:
            d["z_" + c] = d.groupby(["season", "pos"])[c].transform(_z)
    have = {c for c in ("snap", "ay") if c in d.columns and d[c].abs().sum() > 0}
    opp = {p: BASE_OPP_BY_POS[p] + [zc for zc in EXTRA_OPP_BY_POS[p] if zc[2:] in have]
           for p in BASE_OPP_BY_POS}
    d["z_opp"] = d.apply(lambda r: float(np.mean([r[c] for c in opp[r["pos"]]])), axis=1)
    d["gap"] = d["z_opp"] - d["z_pts"]     # opportunity running ahead of scoring
    return d

def build_player_season(df, early_cutoff=8, min_early=4, min_late=3, max_week=17):
    df = df[df.week <= max_week]
    rows = []
    for (pid, season, pos), g in df.groupby(["PlayerId", "season", "pos"]):
        e, l = g[g.week <= early_cutoff], g[g.week > early_cutoff]
        if len(e) < min_early or len(l) < min_late:
            continue
        r = _agg(e); r.update(PlayerId=pid, name=g.PlayerName.iloc[-1], team=g.Team.iloc[-1],
                              season=season, pos=pos, early_ppg=r["pts"], late_ppg=l.TotalPoints.mean())
        rows.append(r)
    return _add_z_opp(pd.DataFrame(rows))

def build_feed(df, min_games=5, max_week=18):
    df = df[df.week <= max_week]
    rows = []
    for (pid, season, pos), g in df.groupby(["PlayerId", "season", "pos"]):
        if len(g) < min_games:
            continue
        r = _agg(g); r.update(PlayerId=pid, name=g.PlayerName.iloc[-1], team=g.Team.iloc[-1],
                              season=season, pos=pos)
        rows.append(r)
    d = _add_z_opp(pd.DataFrame(rows))
    # keep each player's MOST RECENT qualifying season
    d = d.sort_values("season").groupby("PlayerId", as_index=False).last()
    return d
