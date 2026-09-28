"""omr_raw.json (browser scrub of ohmyrockness.com/shows) -> shows.json.

Raw row: [id, iso_datetime, [acts], venue, extra, age, ticket_label, ticket_url, omr_pick]
"""
import json, re

RENAME = {
    "(Le) Poisson Rouge": "Le Poisson Rouge", "TV EYE": "TV Eye", "ALPHAVILLE": "Alphaville",
    "The Rooftop at Pier 17": "Pier 17", "Night Club 101": "Nightclub 101",
    "Lincoln Center - David Geffen Hall": "David Geffen Hall",
    "Footlight Underground at The Windjammer": "Footlight Underground",
}
OUT_OF_CITY = {"Bearsville Theater", "Starland Ballroom", "PNC Bank Arts Center", "Stone Pony",
               "The Wellmont Theater", "Crossroads"}
NOT_BOOKABLE = {"Strand Bookstore", "Columbia University", "Tompkins Square Park",
                "Robert F. Wagner Jr. Park", "Co-Cathedral of Saint Joseph", "St. Francis Xavier Church",
                "St. Bartholomew's Church", "New York Society for Ethical Culture"}
# Comedy, musical comedy and spoken word that share music calendars.
DROP_ACTS = {"michelle buteau", "the moth storyslam", "phoebe robinson", "starbomb"}

MN, BK, QN = "Manhattan", "Brooklyn", "Queens"
BOROUGH = {
    MN: ["Bowery Ballroom", "Central Park Naumburg Bandshell", "Irving Plaza", "Le Poisson Rouge",
         "Mercury Lounge", "Nightclub 101", "Webster Hall", "Beacon Theatre", "Cafe Wha?", "Carnegie Hall",
         "Gramercy Theatre", "Madison Square Garden", "Radio City Music Hall", "Terminal 5", "Pier 17",
         "Bowery Palace", "Central Park SummerStage", "Sony Hall", "Apollo Theater", "DROM",
         "David Geffen Hall", "Pianos", "Cooper Union", "Metropolitan Museum of Art", "The Greene Space",
         "Silver Lining Lounge", "Pacha New York", "Berlin", "Racket"],
    BK: ["Elsewhere", "Music Hall of Williamsburg", "Pioneer Works", "Public Records", "Sleepwalk",
         "Cassette", "Brooklyn Paramount", "Barclays Center", "The Bell House", "The Meadows",
         "The Sultan Room", "Union Pool", "Baby's All Right", "Warsaw", "Brooklyn Steel", "Brooklyn Bowl",
         "Gold Sounds", "Alphaville", "Main Drag Music", "Saint Vitus", "Industry City", "Park Slope",
         "The Broadway", "The Wood Shop", "Maker Park", "99 Scott", "Market Hotel", "National Sawdust",
         "House of Yes", "Littlefield", "The Gutter", "Hart Bar", "Mama Tried", "Maria Hernandez Park",
         "Xanadu", "St. Ann & The Holy Trinity", "Roulette"],
    QN: ["TV Eye", "Knockdown Center", "Trans-Pecos", "Stone Circle Theatre", "Flushing Meadows-Corona Park",
         "Forest Hills Stadium", "Bar Freda", "Footlight Underground"],
}
BORO_OF = {v: b for b, vs in BOROUGH.items() for v in vs}

# The 36-room venue scrub list from the handoff brief.
TIER = {}
for v in ["Nightclub 101", "Mercury Lounge", "Baby's All Right", "The Sultan Room", "Saint Vitus",
          "The Meadows", "TV Eye", "Union Pool", "Market Hotel"]: TIER[v] = "Small room"
for v in ["Bowery Ballroom", "Music Hall of Williamsburg", "Warsaw", "Elsewhere", "Racket",
          "Le Poisson Rouge", "Gramercy Theatre", "Sony Hall", "Brooklyn Monarch", "Brooklyn Bowl",
          "Webster Hall", "Irving Plaza", "Brooklyn Steel", "Terminal 5", "Brooklyn Paramount",
          "S.O.B.'s", "Palladium Times Square"]: TIER[v] = "Club"
for v in ["Madison Square Garden", "Barclays Center", "Radio City Music Hall", "Beacon Theatre",
          "Apollo Theater", "Kings Theatre", "Forest Hills Stadium", "Citi Field", "Yankee Stadium"]: TIER[v] = "Big room"
TIER["Pier 17"] = "Seasonal"

raw = json.load(open("omr_raw.json"))
shows, dropped = [], []
for sid, dt, acts, venue, extra, age, tlabel, turl, pick in raw:
    venue = RENAME.get(venue, venue)
    acts = [re.sub(r",?\s*and more!?$", "", a, flags=re.I).strip() for a in acts]
    acts = [a for a in acts if a and a.lower() not in ("and more!", "and more")]
    if venue in OUT_OF_CITY: dropped.append((venue, acts[0], "outside NYC")); continue
    if venue in NOT_BOOKABLE: dropped.append((venue, acts[0], "not a bookable room")); continue
    if acts[0].lower() in DROP_ACTS: dropped.append((venue, acts[0], "comedy / spoken word")); continue
    assert venue in BORO_OF, venue
    shows.append({
        "id": sid, "date": dt[:10], "time": dt[11:16], "headliner": acts[0], "support": acts[1:],
        "venue": venue, "borough": BORO_OF[venue], "tier": TIER.get(venue),
        "age": age, "ticketLabel": "RSVP" if tlabel == "RSVP" else "Tickets", "ticketUrl": turl,
        "pick": bool(pick),
    })

shows.sort(key=lambda s: (s["date"], s["time"], s["venue"]))
json.dump({"checked": "2026-09-28", "week": ["2026-09-28", "2026-10-04"], "shows": shows},
          open("shows.json", "w"), indent=1, ensure_ascii=False)
print(len(raw), "raw ->", len(shows), "kept")
for d in dropped: print("  dropped:", *d)
