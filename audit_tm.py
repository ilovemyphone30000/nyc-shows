"""Audit the show list against Ticketmaster's calendar. No API calls: it reads the last sweep.

    python3 ticketmaster.py && python3 build.py && python3 audit_tm.py

Writes reports/ticketmaster-audit.html (gitignored; no client data in it) with, per city:
  - shows recently announced on Ticketmaster (on sale in the last week, or not yet on sale),
    and whether our site already has them
  - Ticketmaster concerts in the next two weeks that our list is missing
  - our shows with no support listed, and the support Ticketmaster added
  - our shows Ticketmaster marks cancelled, postponed or rescheduled
  - every room with Ticketmaster concerts in the next year, with its size class
"""
import datetime, html, json, os, re

from capacity import BIG
from process import excluded
from ticketmaster import close, norm

CITIES = [("nyc", "New York"), ("chi", "Chicago"), ("la", "Los Angeles")]
TZ_NOTE = {"nyc": "ET", "chi": "CT", "la": "PT"}
NYC = {"new york", "brooklyn", "queens", "bronx", "the bronx", "staten island", "long island city", "astoria",
       "flushing", "ridgewood", "forest hills", "jamaica", "corona", "queens village", "far rockaway"}
STATE = {"nyc": "NY", "chi": "IL", "la": "CA"}
JUNK = re.compile(r"(?i)\b(parking|tour experience|guided tour|museum|upgrade|vip package|locker|gift card|"
                  r"membership|suite|merch|hotel package|add-on|tailgate|brunch|bingo|karaoke|trivia|drag|burlesque|"
                  r"comedy|open mic|jam session|dance party|silent disco)\b")
today = datetime.date.today()
two_weeks = None  # set from the page: the last date our two-week list covers
week_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

page = open("artifact.html").read()
doc = json.loads(page[page.index("/*DATA*/") + 8:page.index("/*END*/")].replace("<\\/", "</"))
two_weeks = doc["week"][1]
e = html.escape


def in_city(key, r):
    if r.get("state") != STATE[key]:
        return False
    return key != "nyc" or (r.get("city") or "").lower() in NYC


def is_concert(r, music_rooms):
    if JUNK.search(r["name"] or "") or r["status"] == "cancelled":
        return False
    return r["segment"] == "Music" or (r["segment"] == "Undefined" and r["venueId"] in music_rooms)


def size(key, venue):
    v = norm(venue)
    return "1,000+" if any(close(v, norm(b)) or norm(b) in v for b in BIG.get(key, ())) else ""


def price(r):
    p = sorted(r["prices"], key=lambda p: p.get("type") != "standard")
    if not p or p[0].get("min") is None:
        return ""
    lo, hi = p[0]["min"], p[0].get("max")
    f = lambda n: f"${n:,.0f}" if float(n).is_integer() else f"${n:,.2f}"
    return f(lo) if hi in (None, lo) else f"{f(lo)}–{f(hi)}"


def when(ts, key):
    if not ts:
        return ""
    import zoneinfo
    tz = {"nyc": "America/New_York", "chi": "America/Chicago", "la": "America/Los_Angeles"}[key]
    d = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).astimezone(zoneinfo.ZoneInfo(tz))
    return d.strftime("%a %-m/%-d, %-I:%M %p").replace(":00 ", " ")


def day(s):
    return datetime.date.fromisoformat(s).strftime("%a %-m/%-d/%y" if s[:4] != str(today.year) else "%a %-m/%-d")


def bill(r):
    acts = r["acts"] or [r["name"]]
    return f"<b>{e(acts[0])}</b>" + (f"<span class=sup> + {e(', '.join(acts[1:]))}</span>" if acts[1:] else "")


def table(head, rows, empty):
    if not rows:
        return f"<p class=none>{e(empty)}</p>"
    return ("<table><thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")


sections, summary = [], []
for key, name in CITIES:
    city = next(c for c in doc["cities"] if c["key"] == key)
    market = json.load(open(f"data/tm/market_{key}.json"))
    matched = json.load(open(f"data/tm/{key}.json"))
    ledger = json.load(open(f"data/ledger_{key}.json"))["shows"]
    feed_tm = {s["tm"]["url"] for s in city["announced"] if s.get("tm")}
    music_rooms = {r["venueId"] for r in market.values() if r["segment"] == "Music"}
    shows = [r for r in market.values() if in_city(key, r) and is_concert(r, music_rooms) and r["date"] >= str(today)
             and not excluded(key, r["venue"] or "", r["acts"] or [r["name"]])]
    ours_ids = {r["tmId"] for r in matched.values()}
    known = {}
    for x in [*ledger.values(), *city["shows"], *city["announced"]]:
        known.setdefault(x["date"], []).append(x["headliner"])
    def on_site(r):
        if r["tmId"] in ours_ids or r["url"] in feed_tm:
            return "Just announced" if r["url"] in feed_tm else "Yes"
        return "Yes" if any(close(a, h) for a in (r["acts"] or [r["name"]]) for h in known.get(r["date"], [])) else ""

    # 1. Recently announced
    fresh = [r for r in shows if (r["onsale"] and r["onsale"] >= week_ago) or (r["presale"] and r["presale"] >= week_ago)]
    fresh.sort(key=lambda r: (r["onsale"] or "", r["date"]))
    rows1 = [[day(r["date"]), bill(r), e(r["venue"]), size(key, r["venue"]), price(r),
              ("<span class=soon>" if (r["onsale"] or "") > now else "<span>") + e(when(r["onsale"], key)) + "</span>",
              e(when(r["presale"], key)), on_site(r) or "<span class=miss>No</span>"] for r in fresh]
    # 2. Missing from the two-week list
    window = [r for r in shows if r["date"] <= two_weeks]
    missing = sorted((r for r in window if not on_site(r)), key=lambda r: (r["date"], r["venue"]))
    runs = {}  # a residency is one row: the act's nights at that room
    for r in missing:
        runs.setdefault((norm((r["acts"] or [r["name"]])[0]), r["venueId"]), []).append(r)
    rows2 = [[", ".join(day(x["date"]) for x in rs) if len(rs) < 4 else f"{day(rs[0]['date'])} – {day(rs[-1]['date'])} ({len(rs)} nights)",
              bill(rs[0]), e(rs[0]["venue"]), size(key, rs[0]["venue"]), price(rs[0]), f"<a href='{e(rs[0]['url'])}'>Ticketmaster</a>"]
             for rs in runs.values()]
    # 3. No support / support added
    nosup = [s for s in city["shows"] if not s["support"]]
    rows3 = [[day(s["date"]), f"<b>{e(s['headliner'])}</b>", e(s["venue"]), "On Ticketmaster, none listed there either" if s.get("tm") else "Not on Ticketmaster"] for s in nosup]
    added = []
    for sid, r in matched.items():
        s = next((x for x in city["shows"] + city["announced"] if x["id"].split(":")[-1] == sid), None)
        if s:
            omr = ledger.get(sid, {}).get("support")
            extra = [a for a in r["acts"] if not close(a, s["headliner"]) and (omr is None or not any(close(a, o) for o in omr))]
            if extra and omr is not None:
                added.append([day(s["date"]), f"<b>{e(s['headliner'])}</b>", e(s["venue"]), e(", ".join(extra))])
    added.sort()
    # 4. Status
    bad = [s for s in city["shows"] + city["announced"] if s.get("tm", {}).get("status")]
    rows4 = [[day(s["date"]), f"<b>{e(s['headliner'])}</b>", e(s["venue"]), e(s["tm"]["status"].capitalize()), f"<a href='{e(s['tm']['url'])}'>Ticketmaster</a>"] for s in sorted(bad, key=lambda s: s["date"])]
    # 5. Rooms
    rooms = {}
    for r in shows:
        rooms.setdefault(r["venue"], []).append(r)
    rows5 = [[e(v), size(key, v), str(len(rs)), str(sum(1 for r in rs if r["date"] <= two_weeks)), day(min(r["date"] for r in rs)) + " – " + day(max(r["date"] for r in rs))]
             for v, rs in sorted(rooms.items(), key=lambda kv: -len(kv[1]))]

    summary.append([name, f"{len(shows):,}", str(len(window)), str(len(fresh)), str(sum(1 for r in fresh if not on_site(r))), str(len(runs)), str(len(nosup)), str(len(added)), str(len(bad))])
    sections.append(f"""<section id={key}><h2>{e(name)}</h2>
<h3>Recently announced on Ticketmaster <span class=n>{len(fresh)}</span></h3>
<p class=note>On sale (or presale) in the last 7 days, or not on sale yet. Times {TZ_NOTE[key]}. "On our site" says whether the dashboard already has the show.</p>
{table(["Show date", "Bill", "Venue", "Size", "Price", "On sale", "Presale", "On our site"], rows1, "None this week.")}
<h3>On Ticketmaster in our two-week window, missing from our list <span class=n>{len(runs)}</span></h3>
<p class=note>Concerts in the city through {day(two_weeks)}, the end of the list's current window, that neither Oh My Rockness nor the venue calendars gave us. A run of nights at one room is one row.</p>
{table(["Date", "Bill", "Venue", "Size", "Price", ""], rows2, "Nothing missing.")}
<h3>Our two-week shows with no support <span class=n>{len(nosup)}</span></h3>
{table(["Date", "Headliner", "Venue", "Ticketmaster"], rows3, "Every show lists support.")}
<h3>Support Ticketmaster added <span class=n>{len(added)}</span></h3>
<p class=note>Acts on the Ticketmaster listing that Oh My Rockness left off; now shown on the dashboard.</p>
{table(["Date", "Headliner", "Venue", "Added"], added, "None.")}
<h3>Cancelled, postponed or rescheduled <span class=n>{len(bad)}</span></h3>
{table(["Date", "Headliner", "Venue", "Status", ""], rows4, "None.")}
<h3>Rooms with Ticketmaster concerts <span class=n>{len(rooms)}</span></h3>
<p class=note>Ticketmaster doesn't publish capacities; "1,000+" is the dashboard's own big-room list (capacity.py).</p>
{table(["Venue", "Size", "Next 12 months", "Next 2 weeks", "Range"], rows5, "None.")}
</section>""")

os.makedirs("reports", exist_ok=True)
out = "reports/ticketmaster-audit.html"
open(out, "w").write(f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Ticketmaster audit</title><style>
:root{{--ink:#1b1b18;--muted:#6b6a63;--line:#e4e1d8;--bg:#fffdf8;--accent:#2e7040;--warn:#b3402a}}
@media (prefers-color-scheme:dark){{:root{{--ink:#ecebe6;--muted:#a3a29b;--line:#34332f;--bg:#171715;--accent:#7cc08f;--warn:#e98a73}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:28px 16px 80px}}h1{{font-size:26px;margin:0 0 4px}}h2{{font-size:22px;margin:48px 0 0;padding-top:16px;border-top:2px solid var(--ink)}}
h3{{font-size:15px;margin:28px 0 6px}}.n{{color:var(--muted);font-weight:400;margin-left:6px}}.note,.lede{{color:var(--muted);margin:0 0 8px}}.none{{color:var(--muted)}}
nav a{{color:var(--accent);margin-right:14px}}.wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th{{text-align:left;font-weight:500;color:var(--muted);border-bottom:1px solid var(--line);padding:6px 10px 6px 0;white-space:nowrap}}
td{{border-bottom:1px solid var(--line);padding:6px 10px 6px 0;vertical-align:top}}td:first-child{{white-space:nowrap;font-variant-numeric:tabular-nums}}.sup{{color:var(--muted)}}a{{color:var(--accent)}}.miss{{color:var(--warn);font-weight:500}}.soon{{color:var(--accent);font-weight:500}}
section table{{display:block;overflow-x:auto}}
</style></head><body><main>
<h1>Ticketmaster audit</h1><p class=lede>Generated {datetime.datetime.now().strftime("%b %-d, %Y %-I:%M %p")} from a sweep of every music event within reach of each city for the next 12 months. Out-of-town rooms, comedy and talks follow the dashboard's own rules.</p>
<nav>{"".join(f"<a href=#{k}>{e(n)}</a>" for k, n in CITIES)}</nav>
<h3>Summary</h3>
{table(["City", "TM concerts, 12 mo", "Next 2 weeks", "Recently announced", "…not on our site", "Missing from 2-week list (acts)", "No support", "Support added", "Status flags"], summary, "")}
{"".join(sections)}
</main></body></html>""")
print(out)
for r in summary:
    print(" | ".join(r))
