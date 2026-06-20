"""Multi-source NFL news spine.

Outputs:
  data/news.json                  legacy/latest app feed
  data/news/latest.json           rolling player-searchable feed
  data/news/index.json            compact metadata/search index
  data/news/archive/YYYY-MM-DD.json daily archive shard

The important split:
  * RSS is a live league/source feed; most sources expose only the newest items.
  * Search backfill is player/team targeted and can recover older ESPN articles.
  * The archive preserves what DWR has already seen, so scheduled runs accumulate
    instead of replacing useful player news.
"""
import os, re, json, html, datetime, ssl, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SIGNAL = os.path.join(DATA, "signal.json")
LEGACY_OUT = os.path.join(DATA, "news.json")
NEWS_DIR = os.path.join(DATA, "news")
LATEST_OUT = os.path.join(NEWS_DIR, "latest.json")
INDEX_OUT = os.path.join(NEWS_DIR, "index.json")
ARCHIVE_DIR = os.path.join(NEWS_DIR, "archive")
UA = "Mozilla/5.0 (compatible; DWR/0.1; +https://dwr.rbbie.com)"
RETENTION_DAYS = int(os.environ.get("DWR_NEWS_RETENTION_DAYS", "365"))
MAX_ARTICLES = int(os.environ.get("DWR_NEWS_MAX_ARTICLES", "5000"))
BACKFILL_LIMIT = int(os.environ.get("DWR_NEWS_BACKFILL_LIMIT", "500"))
SEARCH_LIMIT = int(os.environ.get("DWR_NEWS_SEARCH_LIMIT", "50"))
MAX_WORKERS = int(os.environ.get("DWR_NEWS_WORKERS", "8"))
TODAY = datetime.datetime.now(datetime.timezone.utc).date().isoformat()

SOURCES = [
    ("ESPN", "https://www.espn.com/espn/rss/nfl/news"),
    ("PFT", "https://profootballtalk.nbcsports.com/feed/"),
    ("CBS", "https://www.cbssports.com/rss/headlines/nfl/"),
    ("Yahoo", "https://sports.yahoo.com/nfl/rss.xml"),
    ("Yardbarker", "https://www.yardbarker.com/rss/sport/2"),
]
NFL_TEAM_TERMS = {
    "ARI":["Cardinals","Arizona"],"ATL":["Falcons","Atlanta"],"BAL":["Ravens","Baltimore"],"BUF":["Bills","Buffalo"],
    "CAR":["Panthers","Carolina"],"CHI":["Bears","Chicago"],"CIN":["Bengals","Cincinnati"],"CLE":["Browns","Cleveland"],
    "DAL":["Cowboys","Dallas"],"DEN":["Broncos","Denver"],"DET":["Lions","Detroit"],"GB":["Packers","Green Bay"],
    "HOU":["Texans","Houston"],"IND":["Colts","Indianapolis"],"JAX":["Jaguars","Jacksonville"],"JAC":["Jaguars","Jacksonville"],
    "KC":["Chiefs","Kansas City"],"LAC":["Chargers","Los Angeles"],"LAR":["Rams","Los Angeles"],"LA":["Rams","Los Angeles"],
    "LV":["Raiders","Las Vegas"],"MIA":["Dolphins","Miami"],"MIN":["Vikings","Minnesota"],"NE":["Patriots","New England"],
    "NO":["Saints","New Orleans"],"NYG":["Giants","New York"],"NYJ":["Jets","New York"],"PHI":["Eagles","Philadelphia"],
    "PIT":["Steelers","Pittsburgh"],"SEA":["Seahawks","Seattle"],"SF":["49ers","Niners","San Francisco"],
    "TB":["Buccaneers","Bucs","Tampa Bay"],"TEN":["Titans","Tennessee"],"WAS":["Commanders","Washington"],"WSH":["Commanders","Washington"],
}


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[.'`’]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _clean(text, n=260):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:n] + ("..." if len(text) > n else "")


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read()
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            return r.read()


def _jsonget(url):
    return json.loads(_fetch(url).decode("utf-8"))


def _parse_dt(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).astimezone(datetime.timezone.utc)
    except Exception:
        pass
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except Exception:
        return None


def _iso(s):
    dt = _parse_dt(s)
    return dt.isoformat() if dt else None


def _article_id(link, title):
    base = link or title or ""
    m = re.search(r"/(?:id/|_/id/)(\d+)", base)
    if m:
        return f"espn:{m.group(1)}"
    return _norm(base)[:180]


def _source_row(title, link, published, source, summary="", players=None, match_type="rss", confidence="league", query=None):
    title = html.unescape((title or "").strip())
    link = (link or "").strip()
    return {
        "id": _article_id(link, title),
        "title": title,
        "link": link,
        "published": _iso(published) or published,
        "source": source,
        "summary": _clean(summary),
        "players": sorted(set(players or [])),
        "match_type": match_type,
        "confidence": confidence,
        "query": query,
    }


def _parse_rss(name, url):
    try:
        root = ET.fromstring(_fetch(url))
    except Exception as e:
        print(f"  {name}: FAILED {e}")
        return []
    out = []
    for it in root.findall(".//item"):
        def g(tag):
            el = it.find(tag)
            return el.text if el is not None else ""
        title, link = g("title"), g("link")
        if not title or not link:
            continue
        out.append(_source_row(title, link, g("pubDate"), name, g("description"), match_type="rss", confidence="league"))
    print(f"  {name}: {len(out)} rss items")
    return out


def _load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def _load_existing_articles():
    files = [LEGACY_OUT, LATEST_OUT]
    if os.path.isdir(ARCHIVE_DIR):
        files.extend(os.path.join(ARCHIVE_DIR, f) for f in os.listdir(ARCHIVE_DIR) if re.match(r"\d{4}-\d{2}-\d{2}\.json$", f))
    out = []
    for path in files:
        d = _load_json(path, {})
        out.extend(d.get("articles") or [])
    return out


def _player_universe():
    sig = _load_json(SIGNAL, {})
    rows, seen = [], set()
    for p in (sig.get("players") or {}).values():
        name, pos = p.get("name"), p.get("pos")
        if not name or pos not in {"QB", "RB", "WR", "TE"}:
            continue
        n = _norm(name)
        if len(n.split()) < 2 or n in seen:
            continue
        seen.add(n)
        team = p.get("team") if p.get("team") and p.get("team") != "FA" else ""
        rows.append({
            "name": name, "nkey": n, "last": n.split()[-1], "pos": pos, "team": team,
            "team_terms": [_norm(t) for t in NFL_TEAM_TERMS.get(team, [])],
            "score": float(p.get("z_opp") or 0) + float(p.get("gap") or 0) + (1 if p.get("flag") == "buy" else 0),
        })
    rows.sort(key=lambda r: (r["score"], r["pos"] == "QB"), reverse=True)
    return rows


def _match_players(article, players):
    text = _norm(" ".join([article.get("title") or "", article.get("summary") or ""]))
    matches = []
    for p in players:
        exact = p["nkey"] in text
        team_ctx = any(t and t in text for t in p["team_terms"])
        last_ctx = len(p["last"]) > 3 and p["last"] in text and team_ctx
        if exact or last_ctx:
            matches.append((p["name"], "exact-name" if exact else "team-context"))
    article["players"] = sorted({m[0] for m in matches})
    if matches:
        article["match_type"] = "entity" if article.get("match_type") == "espn-search" else matches[0][1]
        article["confidence"] = "high" if any(m[1] == "exact-name" for m in matches) else "medium"
    return article


def _espn_search_for_player(p):
    q = " ".join([p["name"], p["team"]]).strip()
    url = "https://site.web.api.espn.com/apis/search/v2?" + urllib.parse.urlencode({"query": q, "limit": SEARCH_LIMIT})
    try:
        d = _jsonget(url)
    except Exception as e:
        print(f"  ESPN search {p['name']}: FAILED {e}")
        return []
    group = next((g for g in d.get("results", []) if g.get("type") == "article"), None)
    out = []
    for a in (group or {}).get("contents", []) or []:
        title = a.get("displayName") or a.get("name") or ""
        link = ((a.get("link") or {}).get("web") or "")
        if "/nfl/" not in link or not title:
            continue
        text = _norm(title)
        exact = p["nkey"] in text
        team_ctx = any(t and t in text for t in p["team_terms"])
        last_ctx = len(p["last"]) > 3 and p["last"] in text and team_ctx
        # Search results are broad; keep direct player hits and team-context fallbacks only.
        if not (exact or last_ctx or team_ctx):
            continue
        confidence = "high" if exact else "medium" if last_ctx else "low"
        match_type = "espn-search" if exact or last_ctx else "team-search"
        out.append(_source_row(title, link, a.get("date"), "ESPN search", "", [p["name"]], match_type, confidence, q))
    return out


def _search_backfill(players):
    targets = players[:BACKFILL_LIMIT]
    print(f"backfill: ESPN search for {len(targets)} player/team queries")
    out = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(_espn_search_for_player, p) for p in targets]
        for fut in as_completed(futs):
            out.extend(fut.result())
    print(f"backfill: {len(out)} ESPN search articles before dedupe")
    return out


def _dedupe(articles):
    seen, out = set(), []
    for a in sorted(articles, key=lambda x: x.get("published") or "", reverse=True):
        k = a.get("id") or _article_id(a.get("link"), a.get("title"))
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(a)
    return out


def _within_retention(a, cutoff):
    dt = _parse_dt(a.get("published"))
    return dt is None or dt >= cutoff


def build():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    players = _player_universe()
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as ex:
        parts = list(ex.map(lambda s: _parse_rss(*s), SOURCES))
    rss = [a for part in parts for a in part]
    search = _search_backfill(players)
    existing = _load_existing_articles()
    if not rss and not search and existing:
        print(f"all sources failed — preserving existing news ({len(existing)} articles)")
        return
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=RETENTION_DAYS)
    articles = [a for a in [*rss, *search, *existing] if _within_retention(a, cutoff)]
    matched = [_match_players(a, players) for a in articles]
    deduped = _dedupe(matched)[:MAX_ARTICLES]
    tagged = sum(1 for a in deduped if a.get("players"))
    by_source = {}
    by_conf = {}
    for a in deduped:
        by_source[a.get("source") or "news"] = by_source.get(a.get("source") or "news", 0) + 1
        by_conf[a.get("confidence") or "unknown"] = by_conf.get(a.get("confidence") or "unknown", 0) + 1
    meta = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sources": [s[0] for s in SOURCES] + ["ESPN search"],
        "retention_days": RETENTION_DAYS,
        "max_articles": MAX_ARTICLES,
        "backfill_limit": BACKFILL_LIMIT,
        "article_count": len(deduped),
        "player_tagged": tagged,
        "by_source": by_source,
        "by_confidence": by_conf,
    }
    out = {**meta, "articles": deduped}
    for path in [LEGACY_OUT, LATEST_OUT, os.path.join(ARCHIVE_DIR, f"{TODAY}.json")]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(out, open(path, "w"), separators=(",", ":"))
    index = {**meta, "articles": [{
        "id": a.get("id"), "title": a.get("title"), "published": a.get("published"), "source": a.get("source"),
        "players": a.get("players") or [], "confidence": a.get("confidence"), "match_type": a.get("match_type"), "link": a.get("link")
    } for a in deduped]}
    json.dump(index, open(INDEX_OUT, "w"), separators=(",", ":"))
    print(f"wrote news — {len(deduped)} articles, {tagged} player-tagged, sources {by_source}")


if __name__ == "__main__":
    build()
