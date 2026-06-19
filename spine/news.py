"""Multi-source news aggregator -> data/news.json (Action-side; most feeds block browser CORS).

Fetches NFL RSS from several prominent outlets, normalizes, strips HTML, and entity-matches
each article to player names from data/signal.json so the frontend can show player-specific
news from many sources (not just ESPN). The frontend reads data/news.json (same-origin) and
merges it with the live ESPN client-side feed.
"""
import os, re, json, html, datetime, ssl, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNAL = os.path.join(ROOT, "data", "signal.json")
OUT = os.path.join(ROOT, "data", "news.json")
UA = "Mozilla/5.0 (compatible; DWR/0.1; +https://dwr.rbbie.com)"
RETENTION_DAYS = 7
MAX_ARTICLES = 600

SOURCES = [
    ("ESPN", "https://www.espn.com/espn/rss/nfl/news"),
    ("PFT", "https://profootballtalk.nbcsports.com/feed/"),
    ("CBS", "https://www.cbssports.com/rss/headlines/nfl/"),
    ("Yahoo", "https://sports.yahoo.com/nfl/rss.xml"),
    ("Yardbarker", "https://www.yardbarker.com/rss/sport/2"),
]

def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[.'`’]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _clean(text, n=240):
    text = re.sub(r"<[^>]+>", " ", text or "")          # strip HTML
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:n] + ("…" if len(text) > n else "")

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except Exception as e:
        # Some local/Python cert stores fail against these public RSS endpoints while
        # GitHub Actions succeeds. Fall back only for news RSS; do not blank the feed.
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            return r.read()

def _parse(name, url):
    try:
        root = ET.fromstring(_fetch(url))
    except Exception as e:
        print(f"  {name}: FAILED {e}"); return []
    out = []
    for it in root.findall(".//item"):
        def g(tag):
            el = it.find(tag)
            return el.text if el is not None else ""
        title = html.unescape((g("title") or "").strip())
        link = (g("link") or "").strip()
        if not title or not link:
            continue
        when = g("pubDate")
        try:
            iso = parsedate_to_datetime(when).astimezone(datetime.timezone.utc).isoformat()
        except Exception:
            iso = None
        out.append({"title": title, "link": link, "published": iso,
                    "source": name, "summary": _clean(g("description"))})
    print(f"  {name}: {len(out)} items")
    return out

def _player_index():
    try:
        sig = json.load(open(SIGNAL))
    except Exception:
        return {}
    idx = {}
    for p in sig.get("players", {}).values():
        nm = p.get("name")
        if nm and len(_norm(nm).split()) >= 2:        # full names only (avoid false positives)
            idx[_norm(nm)] = nm
    return idx

def build():
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as ex:
        parts = list(ex.map(lambda s: _parse(*s), SOURCES))
    articles = [a for part in parts for a in part]
    if not articles:
        try:
            old = json.load(open(OUT))
            old_articles = old.get("articles") or []
        except Exception:
            old_articles = []
        if old_articles:
            print(f"all sources failed — preserving existing {OUT} ({len(old_articles)} articles)")
            return
    try:
        old = json.load(open(OUT)).get("articles") or []
    except Exception:
        old = []
    articles.extend(old)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=RETENTION_DAYS)
    kept = []
    for a in articles:
        try:
            dt = parsedate_to_datetime(a.get("published")).astimezone(datetime.timezone.utc)
        except Exception:
            try:
                dt = datetime.datetime.fromisoformat((a.get("published") or "").replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
            except Exception:
                dt = None
        if dt is None or dt >= cutoff:
            kept.append(a)
    articles = kept
    # dedup by normalized title (cross-source)
    seen, deduped = set(), []
    for a in sorted(articles, key=lambda x: x["published"] or "", reverse=True):
        k = _norm(a["title"])
        if k in seen:
            continue
        seen.add(k); deduped.append(a)
    # entity-match to players
    idx = _player_index()
    for a in deduped:
        text = _norm(a["title"] + " " + a["summary"])
        a["players"] = sorted({disp for nkey, disp in idx.items() if nkey in text})
    deduped = deduped[:MAX_ARTICLES]
    tagged = sum(1 for a in deduped if a["players"])
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "sources": [s[0] for s in SOURCES],
           "retention_days": RETENTION_DAYS,
           "articles": deduped}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"))
    print(f"wrote {OUT} — {len(deduped)} articles, {tagged} player-tagged, sources {out['sources']}")

if __name__ == "__main__":
    build()
