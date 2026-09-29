"""Merge the agency client-show list into data/shows_<city>.json -> data/shows_merged_<city>.json.

    python3 clients.py nyc   (or chi, la)

data/clients_raw_<city>.json is that city's tab of "Client shows in our cities", rows of
[date, artist, venue, city, state, responsible agents, service agent]. It is internal
data and stays out of git.

Each row this week is matched to an Oh My Rockness bill on the same date that lists
the artist, headliner or support. A row with no match becomes its own show, since its
time and bill are unknown.
"""
import json, re, sys, unicodedata

NYC_CITIES = {"New York", "Brooklyn", "Queens", "Forest Hills", "Maspeth", "Ridgewood",
              "Long Island City", "Bronx", "Staten Island", "Flushing", "Astoria"}

# Agency venue name -> the name the page uses.
NYC_VENUE = {
    "Elsewhere: Rooftop": "Elsewhere", "The Gramercy Theatre": "Gramercy Theatre",
    "Madison Square Garden Arena": "Madison Square Garden",
    "LPR - (le) poisson rouge": "Le Poisson Rouge", "SummerStage - Central Park": "Central Park SummerStage",
    "The Rooftop at Pier 17": "Pier 17", "Flushing Meadows": "Flushing Meadows-Corona Park",
    "PACHA": "Pacha New York", "Lincoln Center - David Geffen Hall": "David Geffen Hall",
    "Lincoln Center - Alice Tully Hall": "Alice Tully Hall", "H0l0": "H0L0",
}
# Agency artist name -> how Oh My Rockness bills it.
NYC_ARTIST = {"PiL (Public Image Ltd)": "Public Image Ltd"}

CITY = {
    "nyc": {"keep": lambda r: r[3] in NYC_CITIES and r[4] == "New York", "venue": NYC_VENUE, "artist": NYC_ARTIST},
    # Chicago and LA tabs are already the metro area (Evanston; Orange County, Inglewood, WeHo).
    "chi": {"keep": lambda r: True, "artist": {"Johnny Blue Skies & the Dark Clouds": "Johnny Blue Skies (Sturgill Simpson)"},
            "venue": {"House of Blues": "House of Blues Chicago", "The Salt Shed Outdoors": "The Salt Shed",
                      "Schubas Tavern": "Schubas", "The Auditorium Theatre": "Auditorium Theatre",
                      "Vic Theatre": "The Vic Theatre", "Cahn Auditorium": "Northwestern University"}},
    "la": {"keep": lambda r: True, "artist": {},
           "venue": {"The Moroccan Lounge": "Moroccan Lounge", "The Fonda Theatre": "Fonda Theatre",
                     "The Roxy Theatre": "The Roxy", "Masonic Lodge at Hollywood Forever Cemetery": "Hollywood Forever",
                     "The Observatory Festival Grounds": "The Observatory",
                     # the sheet files Willo's Kettama dates under the Auditorium; OMR bills them in the Expo Hall
                     "Shrine Auditorium": "Shrine Expo Hall"}},
}


def norm(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = s.lower().replace("&", "and")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"^the ", "", s)


def split_names(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


city = sys.argv[1]
cfg = CITY[city]
VENUE, ARTIST = cfg["venue"], cfg["artist"]

data = json.load(open(f"data/shows_{city}.json"))
lo, hi = data["week"]
shows = data["shows"]
for s in shows:
    s["clients"] = []

rows = [r for r in json.load(open(f"data/clients_raw_{city}.json"))
        if r[0] and lo <= r[0] <= hi and cfg["keep"](r)]

added, matched = [], 0
for date, artist, venue, _city, _state, agents, service in rows:
    venue = VENUE.get(venue, venue)
    billed = ARTIST.get(artist, artist)
    client = {"artist": billed, "agents": split_names(agents), "service": split_names(service)}
    key = norm(billed)
    hit = [s for s in shows if s["date"] == date and s.get("source") != "agency"
           and any(norm(a) == key for a in [s["headliner"], *s["support"]] if a not in s.get("joined", []))]
    if hit:
        for s in hit:
            # record the act under the spelling on the bill, so the page can mark it
            as_billed = next(a for a in [s["headliner"], *s["support"]] if norm(a) == key)
            if not any(c["artist"] == as_billed for c in s["clients"]):
                s["clients"].append({**client, "artist": as_billed})
        matched += 1
        continue
    # Not billed by name, but OMR has a show at that venue that night: the agency list
    # says this act plays it, so it joins that bill as support.
    same_room = [s for s in shows if s["date"] == date and s["venue"] == venue]
    if len(same_room) == 1:
        s = same_room[0]
        s["support"].append(billed)
        s.setdefault("joined", []).append(billed)
        s["clients"].append(client)
        matched += 1
        continue
    # Another agency act already added for that venue and night: same bill.
    prior = next((a for a in added if a["date"] == date and a["venue"] == venue), None)
    if prior:
        if norm(prior["headliner"]) != key and key not in map(norm, prior["support"]):
            prior["support"].append(billed)
            prior["clients"].append(client)
        continue
    added.append({
        "id": f"agency-{date}-{key.replace(' ', '-')}", "date": date, "time": None,
        "headliner": billed, "support": [], "venue": venue, "borough": None, "tier": None,
        "age": None, "ticketLabel": None, "ticketUrl": None, "pick": False,
        "source": "agency", "clients": [client],
    })

shows = sorted(shows + added, key=lambda s: (s["date"], s["time"] or "99", s["venue"]))
data["shows"] = shows
json.dump(data, open(f"data/shows_merged_{city}.json", "w"), indent=1, ensure_ascii=False)
print(f"{city}: {len(rows)} client rows this week: {matched} matched to OMR bills, {len(added)} added")
for a in added:
    print("  added:", a["date"], a["headliner"], "@", a["venue"])
