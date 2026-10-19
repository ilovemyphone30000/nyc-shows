"""Ticketmaster's whole music calendar for each city, from the Discovery API v2.

    python3 ticketmaster.py            all cities
    python3 ticketmaster.py nyc        one city

One sweep per city pulls every music event within a set distance of the city for the next
year, 200 at a time: a few dozen requests in all, however many shows we list. Everything
else happens locally:
  - data/tm/market_<city>.json  every event, with date, venue, city, on-sale and presale
    dates, price ranges, status, the Ticketmaster URL and the full list of acts, plus
    `firstSeen`, the first sweep that saw it (so a later sweep can tell what is new)
  - data/tm/<city>.json         the shows on our page matched to their Ticketmaster event
    (by date and act), which build.py reads: support Oh My Rockness leaves out ("Carly Rae
    Jepsen" with Sarah Kinsley), price, on-sale date
A show on our page with a Ticketmaster ticket link that the sweep did not match is looked
up by headliner on its date, one request each (there are only a handful).

The key is read from the TICKETMASTER_API_KEY environment variable, or from .env next to
this file; it is never printed and never committed (.gitignore, .githooks/guard.sh).
Rate limits: at most 4 requests a second (the API allows 5), and the run stops well short
of the 5,000-a-day quota, using the API's own Rate-Limit-Available header and a local count.
data/tm/ is gitignored.
"""
import datetime, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://app.ticketmaster.com/discovery/v2/"
OUT = os.path.join(HERE, "data", "tm")
# Each city's sweep area: a centre and radius in miles. Not Ticketmaster's market (DMA) ids,
# which leave out every venue Ticketmaster never assigned one (Empty Bottle, Thalia Hall,
# Night Club 101). LA reaches Anaheim and Garden Grove, which our list covers.
AREA = {"nyc": (40.7306, -73.9866, 15), "chi": (41.8781, -87.6298, 20), "la": (34.0522, -118.2437, 35)}
STATE = {"nyc": "NY", "chi": "IL", "la": "CA"}
# Ticketmaster segments swept: Music and Undefined. The rest of a market is mostly theater,
# museum time slots and venue tours (30,000 NYC events a year); a concert filed under one of
# those is still caught by the per-show lookup below when its ticket link is Ticketmaster's.
SEGMENTS = ("KZFzniwnSyZfZ7v7nJ", "KZFzniwnSyZfZ7v7nl")
TM_HOSTS = ("ticketmaster.com", "livenation.com", "ticketweb.com")
AHEAD = 365           # days of the market calendar to pull
MIN_GAP = 0.25        # seconds between requests: 4 a second, under the limit of 5
DAILY_CAP = 4500      # stop here even if the API would allow more (quota is 5,000)
FLOOR = 200           # ...or when the API says fewer than this remain today
FEED_DAYS = 30        # the Just announced window (build.py)
MISS_DAYS = 3         # days before a show the per-show lookup missed is tried again


def api_key():
    key = os.environ.get("TICKETMASTER_API_KEY")
    if not key and os.path.exists(os.path.join(HERE, ".env")):
        for line in open(os.path.join(HERE, ".env")):
            k, _, v = line.strip().partition("=")
            if k == "TICKETMASTER_API_KEY":
                key = v.strip().strip("'\"")
    return key


class OutOfQuota(Exception):
    pass


class Client:
    """Discovery API calls, paced and counted. Errors never echo the URL (it holds the key)."""

    def __init__(self, key):
        self.key, self.last, self.calls = key, 0.0, 0
        self.usage_path = os.path.join(OUT, "usage.json")
        u = json.load(open(self.usage_path)) if os.path.exists(self.usage_path) else {}
        today = str(datetime.date.today())
        self.usage = u if u.get("date") == today else {"date": today, "count": 0}

    def get(self, path, **params):
        if self.usage["count"] >= DAILY_CAP:
            raise OutOfQuota(f"local daily cap of {DAILY_CAP} reached")
        url = API + path + "?" + urllib.parse.urlencode({**params, "apikey": self.key})
        for attempt in range(4):
            wait = self.last + MIN_GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.usage["count"] += 1
            self.calls += 1
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    left = r.headers.get("Rate-Limit-Available")
                    body = json.load(r)
                if left is not None and int(left) < FLOOR:
                    raise OutOfQuota(f"Ticketmaster reports {left} requests left today")
                return body
            except urllib.error.HTTPError as e:
                if e.code == 429:  # spike arrest or quota: back off, then give up for the day
                    if "quota" in e.read().decode("utf-8", "replace").lower():
                        raise OutOfQuota("Ticketmaster daily quota reached")
                    time.sleep(2 * (attempt + 1))
                    continue
                if e.code == 404:
                    return {}
                if e.code >= 500 and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"Ticketmaster API error {e.code} on {path}") from None
            except urllib.error.URLError as e:
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"Ticketmaster API unreachable ({e.reason})") from None
        raise RuntimeError(f"Ticketmaster API kept refusing {path}")

    def save(self):
        json.dump(self.usage, open(self.usage_path, "w"))


def norm(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)", " ", s.lower())  # "(DJ set)", "(of Dashboard Confessional)"
    return re.sub(r"^the ", "", re.sub(r"[^a-z0-9]+", " ", s).strip())


def close(a, b):
    a, b = norm(a), norm(b)
    return bool(a and b) and (a == b or (min(len(a), len(b)) > 3 and (a.startswith(b) or b.startswith(a))))


def geohash(lat, lon, n=9):
    """The API's geoPoint parameter: a geohash of the sweep's centre."""
    chars, la, lo, out, bits, ch, even = "0123456789bcdefghjkmnpqrstuvwxyz", [-90.0, 90.0], [-180.0, 180.0], "", 0, 0, True
    while len(out) < n:
        r, v = (lo, lon) if even else (la, lat)
        mid = (r[0] + r[1]) / 2
        ch, r[v <= mid] = ch * 2 + (v > mid), mid
        even, bits = not even, bits + 1
        if bits == 5:
            out, bits, ch = out + chars[ch], 0, 0
    return out


def real(ts):
    """A sale time, or None for Ticketmaster's placeholders (1900-01-01 means "no date")."""
    return ts if ts and ts >= "2000" else None


def record(ev):
    """The fields kept from one Discovery event."""
    v = (ev.get("_embedded", {}).get("venues") or [{}])[0]
    sales, start = ev.get("sales", {}), ev.get("dates", {}).get("start", {})
    pre = sorted((p for p in sales.get("presales", []) if p.get("startDateTime")), key=lambda p: p["startDateTime"])
    cls = (ev.get("classifications") or [{}])[0]
    return {
        "tmId": ev["id"],
        "url": ev.get("url"),
        "name": ev.get("name"),
        "date": start.get("localDate"),
        "time": (start.get("localTime") or "")[:5] or None,
        "status": ev.get("dates", {}).get("status", {}).get("code"),
        "venue": v.get("name"),
        "venueId": v.get("id"),
        "city": v.get("city", {}).get("name"),
        "state": v.get("state", {}).get("stateCode"),
        "onsale": real(sales.get("public", {}).get("startDateTime")),
        "presale": real(pre[0]["startDateTime"]) if pre else None,
        "prices": [{k: p.get(k) for k in ("type", "min", "max", "currency")} for p in ev.get("priceRanges", [])],
        "acts": [a["name"] for a in ev.get("_embedded", {}).get("attractions", []) if a.get("name")],
        "segment": (cls.get("segment") or {}).get("name"),
        "genre": (cls.get("genre") or {}).get("name"),
    }


def sweep(cl, city):
    """Every music event in the city's market, today through AHEAD days. The API serves at
    most 1,000 results per query, so a date range holding more is split in half until each
    piece fits."""
    out = {}

    def window(a, b):
        # Music, plus "Undefined", where small rooms often file their concerts
        lat, lon, miles = AREA[city]
        params = dict(segmentId=",".join(SEGMENTS), geoPoint=geohash(lat, lon), radius=miles, unit="miles",
                      size=200, sort="date,asc",
                      startDateTime=f"{a}T00:00:00Z", endDateTime=f"{b}T23:59:59Z")
        first = cl.get("events.json", page=0, **params)
        total = first.get("page", {}).get("totalElements", 0)
        if total > 1000 and a < b:
            mid = a + (b - a) // 2
            window(a, mid)
            window(mid + datetime.timedelta(days=1), b)
            return
        pages = [first] + [cl.get("events.json", page=p, **params) for p in range(1, min(first.get("page", {}).get("totalPages", 1), 5))]
        for res in pages:
            for ev in res.get("_embedded", {}).get("events", []):
                out[ev["id"]] = record(ev)

    today = datetime.date.today()
    window(today - datetime.timedelta(days=1), today + datetime.timedelta(days=AHEAD))
    return out


def targets(city):
    """Every show the page will list: the two-week list plus the Just announced feed."""
    today = str(datetime.date.today())
    out = {s["id"]: s for s in json.load(open(os.path.join(HERE, f"data/shows_{city}.json")))["shows"] if s["date"] >= today}
    vp = os.path.join(HERE, f"data/venue_raw_{city}.json")
    if os.path.exists(vp):  # venue-calendar shows build.py merges into the two-week list
        from process import clean
        week = json.load(open(os.path.join(HERE, f"data/shows_{city}.json")))["week"]
        for v in clean(city, json.load(open(vp))["rows"], window=(today, week[1]))[0]:
            out.setdefault(v["id"], v)
    lp = os.path.join(HERE, f"data/ledger_{city}.json")
    if os.path.exists(lp):
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=FEED_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i, e in json.load(open(lp))["shows"].items():
            if e["how"] != "range" and e["seen"] != "backfill" and e["seen"] >= cutoff and e["date"] >= today:
                out.setdefault(i, {"id": i, **e})
    return list(out.values())


def matches(show, ev):
    if ev["date"] != show["date"]:
        return False
    if any(close(show["headliner"], n) for n in ev["acts"]):
        return True
    h = norm(show["headliner"])
    return bool(h) and f" {h} " in f" {norm(ev['name'])} "


def pick(show, evs):
    hits = [e for e in evs if matches(show, e)]
    if len(hits) > 1:  # prefer a live listing, the same room, then the same start time
        hits = [e for e in hits if e["status"] != "cancelled"] or hits
        hits = [e for e in hits if close(e["venue"], show["venue"])] or hits
        hits = [e for e in hits if e["time"] == show.get("time")] or hits
    return hits[0] if hits else None


def run(cl, city):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mpath = os.path.join(OUT, f"market_{city}.json")
    old = json.load(open(mpath)) if os.path.exists(mpath) else {}
    try:
        market = sweep(cl, city)
    except OutOfQuota as e:
        print(f"  {city}: sweep stopped, {e}; keeping the last market calendar")
        market = old
    else:
        for i, r in market.items():
            r["firstSeen"] = old.get(i, {}).get("firstSeen") or (stamp if old else "baseline")
        json.dump(market, open(mpath, "w"), ensure_ascii=False, indent=0)

    by_date = {}
    for r in market.values():
        by_date.setdefault(r["date"], []).append(r)
    shows, found = targets(city), {}
    for s in shows:
        r = pick(s, by_date.get(s["date"], []))
        if r:
            found[s["id"]] = r
    # Shows ticketed through Ticketmaster that the music sweep missed (filed under another
    # category, say): one lookup each by headliner on the night.
    # A show that lookup can't find is left alone for MISS_DAYS before it is tried again.
    mpath2 = os.path.join(OUT, f"misses_{city}.json")
    misses = json.load(open(mpath2)) if os.path.exists(mpath2) else {}
    retry = str(datetime.date.today() - datetime.timedelta(days=MISS_DAYS))
    try:
        for s in shows:
            host = urllib.parse.urlparse(s.get("ticketUrl") or "").netloc
            if s["id"] in found or not host.endswith(TM_HOSTS) or misses.get(s["id"], "") > retry:
                continue
            res = cl.get("events.json", keyword=s["headliner"], stateCode=STATE[city], size=20,
                         localStartDateTime=f"{s['date']}T00:00:00,{s['date']}T23:59:59")
            r = pick(s, [record(e) for e in res.get("_embedded", {}).get("events", [])])
            if r:
                found[s["id"]] = r
                misses.pop(s["id"], None)
            else:
                misses[s["id"]] = str(datetime.date.today())
    except OutOfQuota as e:
        print(f"  {city}: artist lookups stopped, {e}")
    # keep earlier per-show finds the sweep can't see (a concert filed under theater, say)
    oldf = json.load(open(os.path.join(OUT, f"{city}.json"))) if os.path.exists(os.path.join(OUT, f"{city}.json")) else {}
    for s in shows:
        if s["id"] not in found and s["id"] in oldf and oldf[s["id"]]["tmId"] not in market:
            found[s["id"]] = oldf[s["id"]]
    json.dump({k: v for k, v in misses.items() if v > retry}, open(mpath2, "w"))
    json.dump(found, open(os.path.join(OUT, f"{city}.json"), "w"), ensure_ascii=False, indent=0)
    extra = sum(1 for s in shows if s["id"] in found and
                any(not close(a, s["headliner"]) and not any(close(a, x) for x in s.get("support", [])) for a in found[s["id"]]["acts"]))
    new = sum(1 for r in market.values() if r.get("firstSeen") == stamp)
    print(f"{city}: market holds {len(market)} music events" + (f" ({new} new since the last sweep)" if old else " (first sweep: baseline)")
          + f"; {len(found)} of our {len(shows)} shows matched, {extra} with acts Oh My Rockness doesn't list")


if __name__ == "__main__":
    key = api_key()
    if not key:
        sys.exit("ticketmaster.py: no TICKETMASTER_API_KEY in the environment or .env; skipped")
    os.makedirs(OUT, exist_ok=True)
    cl = Client(key)
    try:
        for city in sys.argv[1:] or list(AREA):
            run(cl, city)
    finally:
        cl.save()
        print(f"Ticketmaster: {cl.calls} requests this run, {cl.usage['count']} today")
