"""Data layer. Weekly player opportunity data for all four skill positions.

Base usage: committed CSVs on raw.githubusercontent (reachable everywhere incl. CI).
Augmentation: snap share (PFR via nflverse) + air-yards share (nflverse player_stats)
from GitHub *release* assets on objects.githubusercontent — reachable only from the
Action runner, NOT a sandbox. pull_nflverse() degrades to empty if unreachable, and
pull_weekly() then falls back to base features with zero regression.
"""
import io, re, requests, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "gridiron-spine/0.2"}
BASE = "https://raw.githubusercontent.com/hvpkod/NFL-Data/main/NFL-data-Players"
NFLVERSE_RELEASES = {
    "snap_counts": "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{year}.parquet",
    "player_stats": "https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_{year}.parquet",
}

def _norm(s):
    """Name normalization for the nflverse<->hvpkod join (no shared player id)."""
    s = str(s or "").lower()
    s = re.sub(r"[.'`]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def pull_nflverse(seasons):
    """Weekly snap share + air-yards share, keyed (season, week, nkey). Returns None
    on any failure so the caller can degrade. Release assets are Action-only."""
    sess = requests.Session(); sess.headers.update(UA)
    def parquet(url):
        try:
            r = sess.get(url, timeout=60)
            return pd.read_parquet(io.BytesIO(r.content)) if r.status_code == 200 else None
        except Exception:
            return None
    snap_parts, ay_parts = [], []
    for y in seasons:
        s = parquet(NFLVERSE_RELEASES["snap_counts"].format(year=y))
        if s is not None and {"season", "week", "player", "offense_pct"} <= set(s.columns):
            s = s[["season", "week", "player", "offense_pct"]].copy()
            s["nkey"] = s.player.map(_norm)
            s["snap"] = pd.to_numeric(s.offense_pct, errors="coerce")
            snap_parts.append(s[["season", "week", "nkey", "snap"]])
        ps = parquet(NFLVERSE_RELEASES["player_stats"].format(year=y))
        if ps is not None and "air_yards_share" in getattr(ps, "columns", []):
            nm = next((c for c in ("player_display_name", "player_name") if c in ps.columns), None)
            if nm and {"season", "week"} <= set(ps.columns):
                p = ps[["season", "week", nm, "air_yards_share"]].copy()
                p["nkey"] = p[nm].map(_norm)
                p["ay"] = pd.to_numeric(p.air_yards_share, errors="coerce")
                ay_parts.append(p[["season", "week", "nkey", "ay"]])
    out = None
    if snap_parts:
        out = pd.concat(snap_parts, ignore_index=True).groupby(["season", "week", "nkey"], as_index=False).snap.max()
    if ay_parts:
        ay = pd.concat(ay_parts, ignore_index=True).groupby(["season", "week", "nkey"], as_index=False).ay.max()
        out = ay if out is None else out.merge(ay, on=["season", "week", "nkey"], how="outer")
    return out

def pull_weekly(seasons, positions=("QB", "RB", "WR", "TE"), max_week=18, workers=16, with_nflverse=True):
    sess = requests.Session(); sess.headers.update(UA)
    def grab(job):
        y, w, p = job
        try:
            r = sess.get(f"{BASE}/{y}/{w}/{p}.csv", timeout=25)
            if r.status_code != 200:
                return None
            d = pd.read_csv(io.StringIO(r.text))
            d["season"], d["week"], d["pos"] = y, w, p
            return d
        except Exception:
            return None
    jobs = [(y, w, p) for y in seasons for w in range(1, max_week + 1) for p in positions]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        parts = [d for d in ex.map(grab, jobs) if d is not None]
    df = pd.concat(parts, ignore_index=True)
    cols = ["PlayerName", "PlayerId", "Team", "season", "week", "pos",
            "Targets", "Touches", "RzTarget", "TouchCarries", "RushingYDS",
            "PassingYDS", "TotalPoints"]
    df = df[cols].copy()
    num = ["Targets", "Touches", "RzTarget", "TouchCarries", "RushingYDS",
           "PassingYDS", "TotalPoints"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    team_tgt = df.groupby(["season", "week", "Team"])["Targets"].transform("sum")
    df["tgt_share"] = np.where(team_tgt > 0, df.Targets / team_tgt, 0.0)
    # --- nflverse augmentation: snap share + air-yards share (Action-only; degrades cleanly) ---
    df["nkey"] = df.PlayerName.map(_norm)
    nv = pull_nflverse(seasons) if with_nflverse else None
    if nv is not None and len(nv):
        df = df.merge(nv, on=["season", "week", "nkey"], how="left")
    for c in ("snap", "ay"):
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    cov = float((df["snap"] > 0).mean())
    print(f"  nflverse snap coverage: {cov:.0%} of player-weeks"
          + ("" if cov > 0 else " — release assets unreachable, base features only"))
    return df
