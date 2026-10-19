"""Inject the show data into page.html and write the three outputs.

plain/index.html - full document, unencrypted. Gitignored.
artifact.html    - bare fragment for the private Claude artifact (its host adds the
                   doctype/head skeleton). Gitignored; it carries the client data and agents.
index.html       - plain/index.html locked with StatiCrypt. The only page GitHub serves.

Data: data/shows_merged_<city>.json (after clients.py) or data/shows_<city>.json, plus the
announcement log data/ledger_<city>.json, for nyc, chi, la. The password is read from
.staticrypt-password, which is gitignored. Run after process.py and clients.py.
"""
import datetime, json, os, re, subprocess, unicodedata

FEED_DAYS = 30  # how far back the Just announced page reaches


def norm(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)", "", s.lower().replace("&", "and"))
    return re.sub(r"^the ", "", re.sub(r"[^a-z0-9]+", " ", s).strip())


def client_acts(city):
    """THE·TEAM acts by date, from the (gitignored) client sheet:
    {date: {normalized act: {"agents": [...], "service": [...]}}}."""
    names = lambda s: [x.strip() for x in str(s or "").split(",") if x.strip()]
    ours = {}
    if os.path.exists(f"data/clients_raw_{city}.json"):
        for r in json.load(open(f"data/clients_raw_{city}.json")):
            if r[0] and r[1]:  # a numeric band name arrives as a number
                ours.setdefault(r[0], {})[norm(str(r[1]))] = {"agents": names(r[5] if len(r) > 5 else None),
                                                              "service": names(r[6] if len(r) > 6 else None)}
    return ours


def mark(show, ours):
    """THE·TEAM acts on a bill, with their agents, by the act's spelling on the bill."""
    day = ours.get(show["date"], {})
    return [{"artist": x, **day[norm(x)]} for x in [show["headliner"], *show["support"]] if norm(x) in day]


def tm_only(key, d, announced, ledger, tm, near):
    """Ticketmaster events no other source gave us, at rooms we already cover (tm_rules.py):
    added to the two-week list when in its window, and to Just announced when new."""
    import collections, tm_rules
    from process import BOROUGH, excluded
    mpath = f"data/tm/market_{key}.json"
    if not tm_rules.TM_ONLY or not os.path.exists(mpath):
        return
    market = json.load(open(mpath))
    swept = datetime.datetime.fromtimestamp(os.path.getmtime(mpath), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reviewed = json.load(open("data/venues_reviewed.json")).get(key, []) if os.path.exists("data/venues_reviewed.json") else []
    vrows = json.load(open(f"data/venue_raw_{key}.json"))["rows"] if os.path.exists(f"data/venue_raw_{key}.json") else []
    spellings = collections.Counter([e["venue"] for e in ledger.values()] + [s["venue"] for s in d["shows"]] + [r[3] for r in vrows]
                                    + list(reviewed) + ([v for vs in BOROUGH.values() for v in vs] if key == "nyc" else []))
    rooms = {}
    for v, _ in spellings.most_common():  # a room's most common spelling is the one we show
        rooms.setdefault(tm_rules.room(v), v)
    have = {}
    for x in [*ledger.values(), *d["shows"], *announced]:
        have.setdefault(x["date"], []).append((norm(x["venue"]), {norm(a) for a in [x["headliner"], *x["support"]]}))
    matched = {r["tmId"] for r in tm.values()}
    today, (_, week_to) = str(datetime.date.today()), d["week"]
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=FEED_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = [0, 0]
    for r in sorted(market.values(), key=lambda r: (r["date"], r["time"] or "")):
        if r["date"] < today or r["tmId"] in matched or not tm_rules.in_city(key, r):
            continue
        venue = rooms.get(tm_rules.room(r["venue"] or ""))
        if not tm_rules.wanted(r, bool(venue)):
            continue
        # the bill: Ticketmaster's acts, or the event name less its age note ("... (21 and Over)");
        # a bill typed as one name, "A | B | C", is split
        acts = r["acts"] or [re.sub(r"\s*[-–(]?\s*(ages? )?\d\d\s*(\+|and over).*$|\s*\(.*?\)\s*$", "", r["name"], flags=re.I).strip()]
        if len(acts) == 1 and " | " in acts[0]:
            acts = [a.strip() for a in acts[0].split(" | ") if a.strip()]
        nacts = {norm(a) for a in acts}
        if any(any(near(a, h) for a in nacts for h in hs) for _, hs in have.get(r["date"], [])):
            continue  # already listed that night (any room): OMR or a venue calendar has it
        if excluded(key, venue, acts):
            continue
        have.setdefault(r["date"], []).append((norm(venue), nacts))
        age = re.search(r"(?i)(\d\d)\s*(?:\+|and over)|all ages", r["name"] or "")
        show = {"id": "tm:" + r["tmId"], "date": r["date"], "time": r["time"], "headliner": acts[0], "support": acts[1:],
                "venue": venue, "age": (age.group(1) + "+" if age and age.group(1) else "All Ages" if age else None),
                "ticketUrl": r["url"], "tmOnly": 1, "_tm": r}
        show["clients"] = mark(show, client_acts(key))
        if r["date"] <= week_to:
            d["shows"].append(dict(show))
            added[0] += 1
        # Just announced: first seen by a sweep after the first one; or, in the first sweep's
        # calendar, a show whose first sale opened in the last FEED_DAYS or hasn't opened yet.
        first = r.get("firstSeen")
        opened = [t for t in (r["presale"], r["onsale"]) if t and t >= "2000"]
        if opened and min(opened) < cutoff:
            first = None  # tickets went out long ago: Ticketmaster only just listed an old show
        elif not first or first == "baseline":
            sale = min([t for t in (r["presale"], r["onsale"]) if t] or [None]) if (r["presale"] or r["onsale"]) else None
            first = sale if sale and sale <= now else swept if sale else None
        if first and first >= cutoff:
            announced.append({**show, "firstSeen": first})
            added[1] += 1
    d["shows"].sort(key=lambda s: (s["date"], s["time"] or "99", s["venue"]))
    print(f"  {key}: {added[0]} Ticketmaster-only shows in the two-week list, {added[1]} in Just announced (tm_rules.py)")


# Words that fill a bill without naming an act.
FILLER_ACTS = re.compile(r"(?i)^(and )?more( tba)?!?$|^tb[ad]$|^special guests?$|^guests?$|^\+ ?more$|nights? only|^presents?$|^and friends$")


def cross_support(key, shows, near):
    """Every source's lineup for the same night and room, merged into each show's support:
    Oh My Rockness (listings and Just Announced), the venue calendars and Ticketmaster's whole
    calendar. A show matched to one source can still be missing an act another source lists."""
    import tm_rules
    rows = []
    for p in (f"data/omr_raw_{key}.json", f"data/announced_raw_{key}.json"):
        if os.path.exists(p):
            rows += [(r[1][:10], r[3], r[2]) for r in json.load(open(p))]
    if os.path.exists(f"data/venue_raw_{key}.json"):
        rows += [(r[1][:10], r[3], r[2]) for r in json.load(open(f"data/venue_raw_{key}.json"))["rows"]]
    if os.path.exists(f"data/tm/market_{key}.json"):
        rows += [(r["date"], r["venue"] or "", r["acts"]) for r in json.load(open(f"data/tm/market_{key}.json")).values() if r["acts"]]
    by = {}
    for date, venue, acts in rows:
        by.setdefault((date, tm_rules.room(venue)), []).append(acts)
    for show in shows:
        billed = [norm(x) for x in [show["headliner"], *show["support"]]]
        for acts in by.get((show["date"], tm_rules.room(show["venue"])), []):
            if not acts or not near(norm(acts[0]), billed[0]):
                continue  # another show in the room that night
            for a in acts[1:]:
                if norm(a) and not FILLER_ACTS.search(a.strip()) and not any(near(norm(a), b) for b in billed):
                    show["support"] = [*show["support"], a]
                    billed.append(norm(a))
                    show["_grew"] = 1
    ours = None
    for show in shows:
        if show.pop("_grew", None):  # an act added here may be a THE·TEAM client
            ours = ours or client_acts(key)
            have = {c["artist"] for c in show.get("clients", [])}
            show["clients"] = [*show.get("clients", []), *[c for c in mark(show, ours) if c["artist"] not in have]]


page = open("page.html").read()
CITIES = [("nyc", "New York"), ("chi", "Chicago"), ("la", "Los Angeles")]
doc = {"cities": []}
for key, name in CITIES:
    src = f"data/shows_merged_{key}.json"
    if not os.path.exists(src):
        src = f"data/shows_{key}.json"
    d = json.load(open(src))
    doc["week"] = d["week"]
    # Shows a tracked venue lists on its own calendar (venues.py) that OMR doesn't carry join
    # the two-week list too, so a venue's whole bill shows, not just what OMR picked up.
    vpath = f"data/venue_raw_{key}.json"
    if os.path.exists(vpath):
        from process import clean
        acts = lambda s: {norm(x) for x in [s["headliner"], *s["support"]]}
        have = {}
        for s in d["shows"]:
            have.setdefault(s["date"], []).append((s["venue"], norm(s["headliner"]), acts(s)))
        same = lambda a, b: a == b or (min(len(a), len(b)) > 3 and (a.startswith(b) or b.startswith(a)))
        ours_v = client_acts(key)
        for s in clean(key, json.load(open(vpath))["rows"], window=tuple(d["week"]))[0]:
            # the same show: same headliner that night, or the same room sharing any act
            if any(same(norm(s["headliner"]), h) or (v == s["venue"] and acts(s) & a) for v, h, a in have.get(s["date"], [])):
                continue
            have.setdefault(s["date"], []).append((s["venue"], norm(s["headliner"]), acts(s)))
            s["clients"] = mark(s, ours_v)
            d["shows"].append(s)
        d["shows"].sort(key=lambda s: (s["date"], s["time"] or "99", s["venue"]))
    # The announcement log (announce.py). Shows count as news only if first seen on Just
    # Announced or added mid-week; one that merely slid into the window is not "New".
    ledger = json.load(open(f"data/ledger_{key}.json"))["shows"] if os.path.exists(f"data/ledger_{key}.json") else {}
    news = {i: e for i, e in ledger.items() if e["how"] != "range" and e["seen"] != "backfill"}
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=FEED_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ours = client_acts(key)
    announced = []
    for i, e in news.items():
        if e["seen"] >= cutoff and e["date"] >= str(datetime.date.today() - datetime.timedelta(days=1)):
            a = {"id": i, **{k: e[k] for k in ("date", "time", "venue", "headliner", "support", "age", "ticketUrl")}}
            a["clients"] = mark(a, ours)
            announced.append(a)
    # One row per show: a venue-calendar entry and OMR's listing of the same night are the
    # same show. Keep whichever was seen first, with OMR's details when it has them.
    same_show = lambda s: (s["date"], norm(s["headliner"]))
    week_keys = {same_show(s) for s in d["shows"]}
    best = {}
    for a in sorted(announced, key=lambda a: (news[a["id"]]["seen"], news[a["id"]]["how"] == "venue")):
        k = same_show(a)
        if k in best:
            if news[best[k]["id"]]["how"] == "venue" and news[a["id"]]["how"] != "venue":
                best[k] = {**a, "id": best[k]["id"]}
            continue
        best[k] = a
    announced = [a for k, a in best.items() if not (news[a["id"]]["how"] == "venue" and k in week_keys)]
    # Rules added since a show was logged still apply (an out-of-town room, a comedian).
    from process import excluded
    announced = [a for a in announced if not excluded(key, a["venue"], [a["headliner"], *a["support"]])]
    from capacity import BIG, cap as room_cap
    # Ticketmaster's record of each show (ticketmaster.py; gitignored, local only): the acts
    # Oh My Rockness leaves off, the price range and the on-sale date.
    tm = json.load(open(f"data/tm/{key}.json")) if os.path.exists(f"data/tm/{key}.json") else {}
    near = lambda a, b: a == b or (min(len(a), len(b)) > 3 and (a.startswith(b) or b.startswith(a)))
    tm_only(key, d, announced, ledger, tm, near)
    cross_support(key, d["shows"] + announced, near)
    # Shows the listing audit (audit_apply.py) or a person decided to leave off: data/drops.json
    dropped = json.load(open("data/drops.json")).get(key, {}) if os.path.exists("data/drops.json") else {}
    d["shows"] = [x for x in d["shows"] if x["id"] not in dropped]
    announced[:] = [x for x in announced if x["id"] not in dropped]
    fixes = json.load(open("data/corrections.json")).get(key, {}) if os.path.exists("data/corrections.json") else {}
    for show in d["shows"] + announced:  # hand fixes win over every source (data/corrections.json)
        for k, v in fixes.get(show["id"], {}).items():
            if k == "support":  # merged: a source may add acts after the fix was made
                show[k] = list(dict.fromkeys([*show.get("support", []), *v]))
            elif k in ("headliner", "venue", "date", "time", "ticketUrl", "age"):
                show[k] = v
        if show["id"] in fixes:
            show["clients"] = mark(show, client_acts(key))
    for show in d["shows"] + announced:
        r = tm.get(show["id"]) or show.pop("_tm", None)
        if not r:
            continue
        billed = [norm(x) for x in [show["headliner"], *show["support"]]]
        extra = [a for a in r["acts"] if norm(a) and not any(near(norm(a), b) for b in billed)]
        if extra:
            show["support"] = [*show["support"], *extra]
            show["clients"] = [*show.get("clients", []), *[c for c in mark(show, client_acts(key)) if c["artist"] in extra]]
        prices = sorted(r["prices"], key=lambda p: p.get("type") != "standard")
        show["tm"] = {k: v for k, v in {
            "url": r["url"], "onsale": r["onsale"], "presale": r["presale"],
            "price": [prices[0].get("min"), prices[0].get("max"), prices[0].get("currency")] if prices else None,
            "status": r["status"] if r["status"] not in ("onsale", "offsale") else None,
        }.items() if v}
        if not show.get("ticketUrl"):
            show["ticketUrl"] = r["url"]
    for show in d["shows"] + announced:
        c = room_cap(key, show["venue"])
        if c:
            show["cap"] = c  # approximate room capacity (capacity.py), for the cap slider
        # THE·TEAM acts with their agents. Only inside the locked page; never in a committed file.
        show["clients"] = [{"artist": c["artist"], "agents": c.get("agents", []), "service": c.get("service", [])}
                           for c in show.get("clients", [])]
        e = news.get(show["id"])
        if e:
            show["firstSeen"] = e["seen"]
            if e.get("since"):
                show["since"] = e["since"]
        if key != "nyc":  # OMR ids are per region; keep NYC's bare so existing saved hearts survive
            show["id"] = f"{key}:{show['id']}"
        for k in ("borough", "tier", "pick", "joined"):
            show.pop(k, None)
    # When each source was last read: the header shows Oh My Rockness's date, the tooltip all three.
    tm_day = (datetime.date.fromtimestamp(os.path.getmtime(f"data/tm/market_{key}.json")).isoformat()
              if os.path.exists(f"data/tm/market_{key}.json") else None)
    v_day = max(json.load(open(vpath))["scanned"].values(), default=None) if os.path.exists(vpath) else None
    sources = {k: v for k, v in (("Oh My Rockness", d["checked"]), ("Ticketmaster", tm_day), ("Venue calendars", v_day)) if v}
    doc["cities"].append({"key": key, "name": name, "checked": d["checked"], "sources": sources, "shows": d["shows"], "announced": announced})
data = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
a, b = "/*DATA*/", "/*END*/"
i, j = page.index(a) + len(a), page.index(b)
body = page[:i] + data.replace("</", "<\\/") + page[j:]

open("artifact.html", "w").write(body)
os.makedirs("plain", exist_ok=True)
open("plain/index.html", "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="robots" content="noindex, nofollow">\n'
    '<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n'
    + body + "\n</html>\n")

password = open(".staticrypt-password").read().strip()
subprocess.run([
    "npx", "--no-install", "staticrypt", "plain/index.html", "-d", ".", "--short", "--remember", "30",
    "-p", password,
    "--template-title", "Shows",
    "--template-instructions", "Enter the password to see this week's shows.",
    "--template-button", "Open",
    "--template-placeholder", "Password",
    "--template-remember", "Remember me for 30 days",
    "--template-error", "That password isn't right. Try again.",
    "--template-color-primary", "#2e7040",
    "--template-color-secondary", "#fffdf8",
], check=True, stdout=subprocess.DEVNULL)
# StatiCrypt writes its own <head>: keep search engines off the lock page too.
locked = open("index.html").read()
if 'name="robots"' not in locked:
    locked = locked.replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1)
    open("index.html", "w").write(locked)
print("built " + ", ".join(f"{c['name']} {len(c['shows'])}" for c in doc["cities"]) + ": artifact.html, plain/index.html, index.html (locked)")
