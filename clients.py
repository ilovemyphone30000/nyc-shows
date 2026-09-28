"""Merge the agency client-show list into shows.json -> shows_merged.json.

clients_raw.json is the "New York, NY" tab of "Client shows in our cities", rows of
[date, artist, venue, city, state, responsible agents, service agent]. It is internal
data and stays out of git.

Each NYC row this week is matched to an Oh My Rockness bill on the same date that
lists the artist, headliner or support. A row with no match becomes its own show,
flagged as not on Oh My Rockness, since its time and bill are unknown.
"""
import json, re

NYC_CITIES = {"New York", "Brooklyn", "Queens", "Forest Hills", "Maspeth", "Ridgewood",
              "Long Island City", "Bronx", "Staten Island", "Flushing", "Astoria"}

# Agency venue name -> the name the page uses.
VENUE = {
    "Elsewhere: Rooftop": "Elsewhere", "The Gramercy Theatre": "Gramercy Theatre",
    "Madison Square Garden Arena": "Madison Square Garden",
    "LPR - (le) poisson rouge": "Le Poisson Rouge", "SummerStage - Central Park": "Central Park SummerStage",
    "The Rooftop at Pier 17": "Pier 17", "Flushing Meadows": "Flushing Meadows-Corona Park",
    "PACHA": "Pacha New York", "Lincoln Center - David Geffen Hall": "David Geffen Hall",
    "Lincoln Center - Alice Tully Hall": "Alice Tully Hall", "H0l0": "H0L0",
}
# Agency artist name -> how Oh My Rockness bills it.
ARTIST = {"PiL (Public Image Ltd)": "Public Image Ltd"}


def norm(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"^the ", "", s)


def split_names(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


data = json.load(open("shows.json"))
lo, hi = data["week"]
shows = data["shows"]
for s in shows:
    s["clients"] = []

rows = [r for r in json.load(open("clients_raw.json"))
        if r[0] and lo <= r[0] <= hi and r[3] in NYC_CITIES and r[4] == "New York"]

added, matched = [], 0
for date, artist, venue, city, state, agents, service in rows:
    venue = VENUE.get(venue, venue)
    billed = ARTIST.get(artist, artist)
    client = {"artist": billed, "agents": split_names(agents), "service": split_names(service)}
    key = norm(billed)
    hit = [s for s in shows if s["date"] == date and s.get("source") != "agency"
           and any(norm(a) == key for a in [s["headliner"], *s["support"]] if a not in s.get("joined", []))]
    if hit:
        for s in hit:
            if not any(c["artist"] == billed for c in s["clients"]):
                s["clients"].append(client)
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
json.dump(data, open("shows_merged.json", "w"), indent=1, ensure_ascii=False)
print(f"{len(rows)} NYC client rows this week: {matched} matched to OMR bills, {len(added)} added")
for a in added:
    print("  added:", a["date"], a["headliner"], "@", a["venue"])
