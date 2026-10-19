"""Build the listing auditor's worklists from the built page. No network.

    python3 build.py && python3 audit_prep.py          then run the listing-auditor agent
    python3 audit_prep.py --parts 2                    split each city's work in two

Writes data/audit/worklist_<city>[_<n>].json (gitignored), each:
  listings          every show the page lists (two-week list and Just announced), with `flags`
                    for names that look like tributes, theme nights, DJ sets, talks and so on
  no_support        shows the page says have no support, grouped by venue, two-week shows and
                    the newest announcements first; each carries Ticketmaster's act list when
                    the sweep matched it (`tmActs`), so the agent knows what one source says
  ticket links      `allowed` is false for sites never to be opened (Ticketmaster, Live Nation,
                    TicketWeb, AXS): the agent researches those shows another way
No THE·TEAM client data goes into a worklist.
"""
import datetime, json, os, re, sys

FORBIDDEN = ("ticketmaster.com", "livenation.com", "ticketweb.com", "axs.com")
FLAGS = [
    ("tribute", r"\btributes?\b|\bsalute to\b|\bthe music of\b|\bexperience\b|\bplays the music\b|\bplays? (the )?(songs|hits|album)\b|\bcelebrat(es|ing)\b|\blegacy\b|\blegend(s|ary)?\b|\breunion\b|\blive!?$"),
    ("cover/theme night", r"\b(night|party|rave|disco|prom|bash|jam|session|sessions|brunch|karaoke|bingo|trivia|emo|y2k|[0-9]0s|nineties|eighties|seventies|throwback|halloween|xmas|christmas|nye|new year)\b"),
    ("dj", r"\bdj\b|\bdj set\b|\bb2b\b|\ball night\b|\bextended set\b|\bvinyl\b|\bboiler room\b"),
    ("talk/comedy/film", r"\b(comedy|comedian|stand-?up|podcast|in conversation|conversation with|talk|lecture|reading|book|screening|film|movie|documentary|q&a|storytelling|improv|drag|burlesque|cabaret|magic|variety)\b"),
    ("festival/package", r"\b(fest|festival|presents|showcase|vip|package|upgrade|parking|tour experience|pass)\b"),
    ("generic title", r"^(the )?[A-Z0-9 &'!:-]{18,}$"),
]


def flags(s):
    text = " ".join([s["headliner"], *s["support"]])
    out = [name for name, rx in FLAGS if re.search(rx, text, re.I if name != "generic title" else 0)]
    if s.get("tmOnly"):
        out.append("ticketmaster-only")
    return out


def host(u):
    return re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*$", r"\1", u or ""))


page = open("artifact.html").read()
doc = json.loads(page[page.index("/*DATA*/") + 8:page.index("/*END*/")].replace("<\\/", "</"))
parts = int(sys.argv[sys.argv.index("--parts") + 1]) if "--parts" in sys.argv else 1
os.makedirs("data/audit", exist_ok=True)
week = set()
for c in doc["cities"]:
    week |= {s["id"] for s in c["shows"]}
for c in doc["cities"]:
    shows = list({s["id"]: s for s in c["shows"] + c["announced"]}.values())
    tm = json.load(open(f"data/tm/{c['key']}.json")) if os.path.exists(f"data/tm/{c['key']}.json") else {}
    rows = []
    for s in shows:
        bare = s["id"].split(":", 1)[1] if s["id"].startswith(c["key"] + ":") else s["id"]
        url = s.get("ticketUrl") or (s.get("tm") or {}).get("url") or ""
        rows.append({"id": s["id"], "date": s["date"], "time": s.get("time"), "headliner": s["headliner"], "support": s["support"],
                     "venue": s["venue"], "cap": s.get("cap"), "ticketUrl": url, "ticketHost": host(url),
                     "allowed": bool(url) and not host(url).endswith(FORBIDDEN), "inTwoWeeks": s["id"] in week,
                     "announced": (s.get("firstSeen") or "")[:10], "tmOnly": bool(s.get("tmOnly")),
                     "tmActs": (tm.get(bare) or {}).get("acts") or (s.get("_tmActs")), "flags": flags(s)})
    shared = lambda r: r["headliner"].count(",") >= 2
    nosup = sorted((r for r in rows if not r["support"] and not shared(r)),
                   key=lambda r: (not r["inTwoWeeks"], r["announced"] and -int(r["announced"].replace("-", "")) or 0, r["date"]))
    for n in range(parts):
        mine = nosup[n::parts]
        by_venue = {}
        for r in mine:
            by_venue.setdefault(r["venue"], []).append(r)
        name = f"data/audit/worklist_{c['key']}" + (f"_{n + 1}" if parts > 1 else "") + ".json"
        json.dump({"city": c["key"], "cityName": c["name"], "part": n + 1, "parts": parts, "made": str(datetime.date.today()),
                   "listings": rows if n == 0 else [], "no_support": by_venue}, open(name, "w"), ensure_ascii=False, indent=1)
        print(f"{name}: {len(rows) if n == 0 else 0} listings to review, {len(mine)} no-support shows at {len(by_venue)} venues"
              f", {sum(1 for r in rows if r['flags'] and r['flags'] != ['ticketmaster-only']) if n == 0 else 0} flagged")
