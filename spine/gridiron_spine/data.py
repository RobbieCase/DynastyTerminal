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
}
# nflverse moved the weekly offense stats file across releases over time (the legacy
# `player_stats` release is frozen and lacks recent seasons). Try newest-first and use
# whichever the runner can actually fetch; the per-year log line records which won.
PLAYER_STATS_CANDIDATES = [
    "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year}.parquet",
    "https://github.com/nflverse/nflverse-data/releases/download/player_stats/stats_player_week_{year}.parquet",
    "https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_{year}.parquet",
]

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
        # --- snap share (PFR) — already working ---
        s = parquet(NFLVERSE_RELEASES["snap_counts"].format(year=y))
        if s is not None and {"season", "week", "player", "offense_pct"} <= set(s.columns):
            s = s[["season", "week", "player", "offense_pct"]].copy()
            s["nkey"] = s.player.map(_norm)
            s["snap"] = pd.to_numeric(s.offense_pct, errors="coerce")
            snap_parts.append(s[["season", "week", "nkey", "snap"]])

        # --- air-yards share: try each release candidate until one yields data ---
        ps = used = None
        for tmpl in PLAYER_STATS_CANDIDATES:
            cand = parquet(tmpl.format(year=y))
            if cand is not None and len(cand):
                ps, used = cand, tmpl.split("/download/")[1].split("/")[0]
                break
        if ps is None:
            print(f"  player_stats {y}: no candidate fetched")
            continue
        cols = set(ps.columns)
        nm = next((c for c in ("player_display_name", "player_name", "player") if c in cols), None)
        if nm is None or not {"season", "week"} <= cols:
            print(f"  player_stats {y} [{used}]: missing name/season cols; have {sorted(cols)[:8]}")
            continue
        p = ps.copy()
        if "season_type" in cols:                       # drop playoff weeks (avoid week-num collisions)
            p = p[p.season_type.astype(str).str.upper().str.startswith("REG")]
        p["nkey"] = p[nm].map(_norm)
        if "air_yards_share" in cols:
            p["ay"] = pd.to_numeric(p["air_yards_share"], errors="coerce")
            src = "air_yards_share"
        elif "receiving_air_yards" in cols:             # compute share if precomputed col is gone
            tcol = next((c for c in ("team", "recent_team", "posteam") if c in cols), None)
            p["_ray"] = pd.to_numeric(p["receiving_air_yards"], errors="coerce").fillna(0.0)
            if tcol:
                tot = p.groupby(["season", "week", tcol])["_ray"].transform("sum")
                p["ay"] = np.where(tot > 0, p["_ray"] / tot, np.nan)
                src = "receiving_air_yards/team"
            else:
                p["ay"] = np.nan; src = "receiving_air_yards (no team col)"
        else:
            print(f"  player_stats {y} [{used}]: no air-yards column; have {sorted(cols)[:12]}")
            continue
        sub = p[["season", "week", "nkey", "ay"]].dropna(subset=["ay"])
        if len(sub):
            ay_parts.append(sub)
            print(f"  player_stats {y} [{used}]: {len(sub)} ay rows via {src}")

    out = None
    if snap_parts:
        out = pd.concat(snap_parts, ignore_index=True).groupby(["season", "week", "nkey"], as_index=False).snap.max()
    if ay_parts:
        ay = pd.concat(ay_parts, ignore_index=True).groupby(["season", "week", "nkey"], as_index=False).ay.max()
        out = ay if out is None else out.merge(ay, on=["season", "week", "nkey"], how="outer")
    return out

ROSTER_CANDIDATES = [
    "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{year}.parquet",
    "https://github.com/nflverse/nflverse-data/releases/download/rosters/rosters_{year}.parquet",
]

def pull_roster_ages(seasons):
    """Per-season player ages (nflverse rosters), keyed (season, nkey) for the aging fit.
    Uses an `age` column when present, else derives it from `birth_date` at Sept 1.
    Returns None on failure (Action-only release assets)."""
    sess = requests.Session(); sess.headers.update(UA)
    def parquet(url):
        try:
            r = sess.get(url, timeout=60)
            return pd.read_parquet(io.BytesIO(r.content)) if r.status_code == 200 else None
        except Exception:
            return None
    parts = []
    for y in seasons:
        rd = None
        for tmpl in ROSTER_CANDIDATES:
            rd = parquet(tmpl.format(year=y))
            if rd is not None and len(rd):
                break
        if rd is None:
            print(f"  rosters {y}: no candidate fetched"); continue
        cols = set(rd.columns)
        nm = next((c for c in ("full_name", "player_name", "player_display_name") if c in cols), None)
        if nm is None:
            print(f"  rosters {y}: no name column; have {sorted(cols)[:8]}"); continue
        d = rd.copy(); d["nkey"] = d[nm].map(_norm); d["season"] = y
        if "age" in cols and pd.to_numeric(d["age"], errors="coerce").notna().any():
            d["age"] = pd.to_numeric(d["age"], errors="coerce")
        elif "birth_date" in cols:
            bd = pd.to_datetime(d["birth_date"], errors="coerce")
            d["age"] = (pd.Timestamp(year=y, month=9, day=1) - bd).dt.days / 365.25
        else:
            print(f"  rosters {y}: no age/birth_date col"); continue
        sub = d[["season", "nkey", "age"]].dropna(subset=["age"])
        if len(sub):
            parts.append(sub); print(f"  rosters {y}: {len(sub)} ages")
    if not parts:
        return None
    return pd.concat(parts, ignore_index=True).groupby(["season", "nkey"], as_index=False).age.max()

def pull_fantasy_history(seasons):
    """Per-season fantasy PPG by player from nflverse stats_player_week — DEEP history for
    the aging fit, independent of the 2021+ hvpkod usage window. Returns a DataFrame
    [player(nkey), pos, season, ppg, games] or None. Action-only release assets."""
    sess = requests.Session(); sess.headers.update(UA)
    def parquet(url):
        try:
            r = sess.get(url, timeout=60)
            return pd.read_parquet(io.BytesIO(r.content)) if r.status_code == 200 else None
        except Exception:
            return None
    parts = []
    for y in seasons:
        ps = None
        for tmpl in PLAYER_STATS_CANDIDATES:
            ps = parquet(tmpl.format(year=y))
            if ps is not None and len(ps):
                break
        if ps is None:
            continue
        cols = set(ps.columns)
        nm = next((c for c in ("player_display_name", "player_name") if c in cols), None)
        fp = next((c for c in ("fantasy_points_ppr", "fantasy_points") if c in cols), None)
        if nm is None or fp is None or "position" not in cols or not {"season", "week"} <= cols:
            continue
        p = ps.copy()
        if "season_type" in cols:
            p = p[p.season_type.astype(str).str.upper().str.startswith("REG")]
        p = p[p.position.isin(["QB", "RB", "WR", "TE"])]
        p["nkey"] = p[nm].map(_norm)
        p["fp"] = pd.to_numeric(p[fp], errors="coerce")
        g = (p.groupby(["nkey", "position", "season"], as_index=False)
               .agg(ppg=("fp", "mean"), games=("week", "nunique")).rename(columns={"position": "pos"}))
        parts.append(g)
    if not parts:
        return None
    out = pd.concat(parts, ignore_index=True)
    print(f"  fantasy history: {len(out):,} player-seasons over {out.season.min()}–{out.season.max()}")
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
