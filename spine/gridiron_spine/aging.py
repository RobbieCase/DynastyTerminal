"""Archetype-conditional aging via survival analysis.

For each position we fit a Kaplan-Meier survival curve from historical player-seasons:
P(still fantasy-relevant at age a). Event = a player's final relevant season; players whose
final season is the most recent data year are right-censored (still active, not yet "failed").
The curve cleanly captures that RBs fall off fast while QBs persist.

We deliberately DO NOT turn this into a value multiplier on market price: every formulation
tried (delta-method production retention, normalized expected-remaining-seasons) either
inherited selection bias or double-counted the dynasty horizon the market already prices,
producing curves far steeper / less sane than the hand-coded one (e.g. QB@30 ≈ 0.5×, which
is wrong). So the survival curve ships as honest aging-RISK context; the intrinsic keeps the
hand-coded age curve until a multiplier can be validated as an improvement.
"""
import numpy as np, pandas as pd

REL_MIN_PPG = {"QB": 12.0, "RB": 6.0, "WR": 6.0, "TE": 4.0}   # "fantasy-relevant" floor / game

def _survival_curve(rel, lo, hi, last_year):
    """Kaplan-Meier by age over relevant player-seasons. Right-censor still-active players."""
    last_age, censored = {}, {}
    for pid, s in rel.groupby("player"):
        s = s.sort_values("age")
        last_age[pid] = int(s.age.iloc[-1])
        censored[pid] = int(s.season.iloc[-1]) >= last_year
    surv, S = 1.0, {}
    for a in range(lo, hi + 1):
        n = sum(1 for pid in last_age if last_age[pid] >= a)            # reached age a
        d = sum(1 for pid in last_age if last_age[pid] == a and not censored[pid])  # failed at a
        if n > 0:
            surv *= (1 - d / n)
        S[a] = surv
    return S

def fit_age_curves(df, lo=21, hi=36):
    """df: player-seasons [player, pos, season, age, ppg]. Returns {pos: {surv, n}}."""
    df = df[(df.age >= lo) & (df.age <= hi) & df.ppg.notna()].copy()
    if not len(df):
        return {}
    last_year = int(df.season.max())
    out = {}
    for pos, g in df.groupby("pos"):
        rel = g[g.ppg >= REL_MIN_PPG.get(pos, 5.0)]
        if rel.player.nunique() < 20:
            continue
        surv = _survival_curve(rel, lo, hi, last_year)
        out[pos] = {"surv": {a: round(s, 3) for a, s in surv.items()},
                    "n": int(rel.player.nunique())}
    return out
