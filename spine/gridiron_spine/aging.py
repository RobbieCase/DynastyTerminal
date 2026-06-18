"""Archetype-conditional aging — survival analysis + the delta method.

Replaces the hand-coded frontend age curve with one fit from historical player-seasons.
Two curves per position (descriptive population curves, not per-player forecasts):

  production retention (delta method): the year-over-year PPG ratio averaged across
    players who played BOTH ages, chained into a peak-normalized curve. This controls
    survivorship — a raw mean-PPG-by-age curve is biased upward at old ages because only
    the survivors are left, which would understate real decline.

  survival (Kaplan-Meier): P(still fantasy-relevant at age a). Event = a player's final
    relevant season; players whose final season is the most recent year are right-censored
    (still active, not yet "failed").

The dynasty value multiplier the terminal applies is built from the production curve but
held flat at 1.0 through the peak age (youth shouldn't be penalized — the market already
prices the dynasty horizon; the curve's job is the post-peak decline). The survival curve
is emitted as aging-risk context.
"""
import numpy as np, pandas as pd

REL_MIN_PPG = {"QB": 12.0, "RB": 6.0, "WR": 6.0, "TE": 4.0}   # "fantasy-relevant" floor / game
FLOOR = 0.45                                                  # don't let the multiplier collapse

def _production_curve(g, lo, hi):
    """g: one position's rows [player, age, ppg]. Returns peak-normalized {age: level}."""
    by_player = {pid: dict(zip(s.age.astype(int), s.ppg)) for pid, s in g.groupby("player")}
    ratios = {a: [] for a in range(lo, hi)}
    for ages in by_player.values():
        for a in range(lo, hi):
            if a in ages and (a + 1) in ages and ages[a] > 1.0:
                ratios[a].append(ages[a + 1] / ages[a])
    level, curve = 1.0, {lo: 1.0}
    for a in range(lo, hi):
        r = float(np.median(ratios[a])) if ratios[a] else 1.0
        r = min(max(r, 0.7), 1.4)            # clamp noisy single-year transitions
        level *= r
        curve[a + 1] = level
    peak = max(curve.values()) or 1.0
    return {a: v / peak for a, v in curve.items()}, max(curve, key=curve.get)

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
    """df: player-seasons [player, pos, season, age, ppg]. Returns {pos: {...}}."""
    df = df[(df.age >= lo) & (df.age <= hi) & df.ppg.notna()].copy()
    if not len(df):
        return {}
    last_year = int(df.season.max())
    out = {}
    for pos, g in df.groupby("pos"):
        prod, peak = _production_curve(g, lo, hi)
        surv = _survival_curve(g[g.ppg >= REL_MIN_PPG.get(pos, 5.0)], lo, hi, last_year)
        # value multiplier: flat 1.0 through the peak age, data-driven decline after, floored
        mult = {a: round(max(FLOOR, 1.0 if a <= peak else prod[a]), 3) for a in prod}
        out[pos] = {"mult": mult, "surv": {a: round(s, 3) for a, s in surv.items()},
                    "peak": int(peak), "n": int(g.player.nunique())}
    return out
