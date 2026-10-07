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
    from capacity import BIG
    for show in d["shows"] + announced:
        if show["venue"] in BIG.get(key, ()):
            show["big"] = 1  # about 1,000 capacity or more (capacity.py)
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
    doc["cities"].append({"key": key, "name": name, "checked": d["checked"], "shows": d["shows"], "announced": announced})
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
