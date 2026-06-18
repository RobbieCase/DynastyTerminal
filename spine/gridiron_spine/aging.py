"""Archetype-conditional aging via survival analysis.

For each position we fit a Kaplan-Meier survival curve from historical player-seasons:
P(still fantasy-relevant at age a). Event = a player's final relevant season; players whose
final season is the most recent data year are right-censored (still active, not yet "failed").
This is the trustworthy primitive — it cleanly captures that RBs fall off fast while QBs
persist, with no production-curve selection bias.

The dynasty value multiplier is derived from that survival curve as **expected remaining
relevant seasons** from age a (Σ_{t≥a} S(t)/S(a)), normalized so a prime-age anchor = 1.0
and capped. A young player has more relevant seasons ahead (slight premium); an old player
fewer (discount) — and because each position has its own survival curve, the decline is
position-specific. The market already prices the dynasty horizon, so the multiplier is
deliberately gentle (capped, floored), a relative tilt rather than a steep re-pricing.
"""
import numpy as np, pandas as pd

REL_MIN_PPG = {"QB": 12.0, "RB": 6.0, "WR": 6.0, "TE": 4.0}   # "fantasy-relevant" floor / game
FLOOR, CAP, ANCHOR = 0.5, 1.2, 25                            # multiplier bounds + prime anchor age

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

def _value_mult(S, lo, hi):
    """Expected remaining relevant seasons from age a, normalized to the prime anchor.
    Enforced monotone non-increasing in age (older = less dynasty runway) — this also clips
    the noisy KM tail, where few old survivors rarely 'fail' in-sample and inflate ERS."""
    ers = {a: sum(S.get(t, 0.0) / (S.get(a, 0.0) or 1e-9) for t in range(a, hi + 1))
           for a in range(lo, hi + 1)}
    base = ers.get(ANCHOR) or 1.0
    out, run = {}, CAP
    for a in range(lo, hi + 1):
        run = min(run, ers[a] / base)
        out[a] = round(min(CAP, max(FLOOR, run)), 3)
    return out

def fit_age_curves(df, lo=21, hi=36):
    """df: player-seasons [player, pos, season, age, ppg]. Returns {pos: {mult, surv, n}}."""
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
        out[pos] = {"mult": _value_mult(surv, lo, hi),
                    "surv": {a: round(s, 3) for a, s in surv.items()},
                    "n": int(rel.player.nunique())}
    return out
