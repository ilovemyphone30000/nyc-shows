"""data/omr_raw_<city>.json (scrape.py) -> data/shows_<city>.json.

    python3 process.py nyc   (or chi, la)

Raw row: [id, iso_datetime, [acts], venue, extra, age, ticket_label, ticket_url, omr_pick]
"""
import datetime, json, os, re, sys

# Today through two weeks ahead. The page narrows this again by the viewer's own date.
TODAY = datetime.date.today()
WEEK = [str(TODAY), str(TODAY + datetime.timedelta(days=14))]

RENAME = {
    "(Le) Poisson Rouge": "Le Poisson Rouge", "TV EYE": "TV Eye", "ALPHAVILLE": "Alphaville",
    "The Rooftop at Pier 17": "Pier 17", "Night Club 101": "Nightclub 101",
    "Lincoln Center - David Geffen Hall": "David Geffen Hall",
    "Footlight Underground at The Windjammer": "Footlight Underground",
}
OUT_OF_CITY = {"Bearsville Theater", "Starland Ballroom", "PNC Bank Arts Center", "Stone Pony",
               "The Wellmont Theater", "Crossroads", "MetLife Stadium", "The Paramount",
               # Long Island, New Jersey and upstate rooms OMR lists
               "Massapequa VFW Hall", "Amityville Music Hall", "The Count Basie Center for the Arts",
               "Count Basie Center for the Arts", "Basilica Hudson", "Tarrytown Music Hall"}
NOT_BOOKABLE = {"Strand Bookstore", "Columbia University", "Tompkins Square Park",
                "Robert F. Wagner Jr. Park", "Co-Cathedral of Saint Joseph", "St. Francis Xavier Church",
                "St. Bartholomew's Church", "New York Society for Ethical Culture"}
# Comedy, musical comedy and spoken word that share music calendars.
DROP_ACTS = {"michelle buteau", "the moth storyslam", "phoebe robinson", "starbomb",
             "olivia harrison",  # in conversation with Martin Scorsese at BAM
             "iliza shlesinger",
             "comedy bang! bang! live!",
             "the rocky horror picture show"}  # a screening with a shadow cast

# Chicago and LA: OMR's own regions, minus what is plainly out of town or not music.
CITY = {
    "nyc": {"rename": None, "out": None, "acts": None},
    "chi": {"rename": {}, "out": set(), "acts": {"kyle gordon", "iliza shlesinger"}},
    "la": {"rename": {"Amoeba Music- Hollywood": "Amoeba Music Hollywood"},
           "out": {"Pappy & Harriet's"}, "acts": {"dynasty handbag", "carmen christopher"}},
}

MN, BK, QN = "Manhattan", "Brooklyn", "Queens"
BOROUGH = {
    MN: ["Bowery Ballroom", "Central Park Naumburg Bandshell", "Irving Plaza", "Le Poisson Rouge",
         "Mercury Lounge", "Nightclub 101", "Webster Hall", "Beacon Theatre", "Cafe Wha?", "Carnegie Hall",
         "Gramercy Theatre", "Madison Square Garden", "Radio City Music Hall", "Terminal 5", "Pier 17",
         "Bowery Palace", "Central Park SummerStage", "Sony Hall", "Apollo Theater", "DROM",
         "David Geffen Hall", "Pianos", "Cooper Union", "Metropolitan Museum of Art", "The Greene Space",
         "Silver Lining Lounge", "Pacha New York", "Berlin", "Racket", "Rough Trade NYC", "Town Hall"],
    BK: ["Elsewhere", "Music Hall of Williamsburg", "Pioneer Works", "Public Records", "Sleepwalk",
         "Cassette", "Brooklyn Paramount", "Barclays Center", "The Bell House", "The Meadows",
         "The Sultan Room", "Union Pool", "Baby's All Right", "Warsaw", "Brooklyn Steel", "Brooklyn Bowl",
         "Gold Sounds", "Alphaville", "Main Drag Music", "Saint Vitus", "Industry City", "Park Slope",
         "The Broadway", "The Wood Shop", "Maker Park", "99 Scott", "Market Hotel", "National Sawdust",
         "House of Yes", "Littlefield", "The Gutter", "Hart Bar", "Mama Tried", "Maria Hernandez Park",
         "Xanadu", "St. Ann & The Holy Trinity", "Roulette", "Good Room", "Purgatory",
         "BAM: Brooklyn Academy of Music"],
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

def excluded(city, venue, acts):
    """Why a show at this (already renamed) venue with these acts is left off, or None.
    Also applied at build time to the announcement log, so a rule added later clears old entries."""
    nyc = city == "nyc"
    cfg = CITY[city]
    if venue in (OUT_OF_CITY if nyc else cfg["out"]): return "out of town"
    if nyc and venue in NOT_BOOKABLE: return "not a bookable room"
    if acts[0].lower() in (DROP_ACTS if nyc else cfg["acts"]): return "comedy / spoken word"
    if any(re.search(r"\((?:film )?screening\)", a, re.I) for a in acts): return "film screening"
    if re.search(r"\((?:in-?store )?signing\)", acts[0], re.I): return "record-store signing"
    return None


def clean(city, raw, window=None):
    """Raw OMR rows -> (shows, dropped) under this city's rules. window: (from, to) dates, or None for all."""
    nyc = city == "nyc"
    cfg = CITY[city]
    rename = RENAME if nyc else cfg["rename"]
    out_of_town = OUT_OF_CITY if nyc else cfg["out"]
    drop_acts = DROP_ACTS if nyc else cfg["acts"]
    shows, dropped = [], []
    for sid, dt, acts, venue, extra, age, tlabel, turl, pick in raw:
        venue = rename.get(venue, venue)
        acts = [re.sub(r",?\s*and more!?$", "", a, flags=re.I).strip() for a in acts]
        acts = [a for a in acts if a and a.lower() not in ("and more!", "and more")]
        if not acts: continue
        if window and not window[0] <= dt[:10] <= window[1]: continue
        why = excluded(city, venue, acts)
        if why: dropped.append((venue, acts[0], why)); continue
        shows.append({
            "id": sid, "date": dt[:10], "time": dt[11:16], "headliner": acts[0], "support": acts[1:],
            "venue": venue, "borough": BORO_OF.get(venue) if nyc else None, "tier": TIER.get(venue) if nyc else None,
            "age": age, "ticketLabel": "RSVP" if tlabel == "RSVP" else "Tickets", "ticketUrl": turl,
            "pick": bool(pick),
        })
    shows.sort(key=lambda s: (s["date"], s["time"], s["venue"]))
    return shows, dropped


def main(city):
    nyc = city == "nyc"
    path = f"data/omr_raw_{city}.json"  # not there before a city's first scrape
    raw = json.load(open(path)) if os.path.exists(path) else []
    # Venues someone has already looked at. Anything else is kept but logged to
    # data/unreviewed_venues.txt, since the daily run is unattended: the weekly review
    # decides whether a new room is in town and hosts music (see the refresh-shows skill).
    reviewed_all = json.load(open("data/venues_reviewed.json"))
    reviewed = set(reviewed_all.get(city, [])) | (set(BORO_OF) if nyc else set())
    shows, dropped = clean(city, raw, WEEK)
    # "checked" is the last successful scrape, not today: a blocked day must not look fresh.
    scraped = f"data/scraped_{city}.txt"
    checked = open(scraped).read().strip() if os.path.exists(scraped) else str(TODAY)
    json.dump({"checked": checked, "week": WEEK, "shows": shows},
              open(f"data/shows_{city}.json", "w"), indent=1, ensure_ascii=False)
    print(city, len(raw), "raw ->", len(shows), "kept")
    new = sorted({s["venue"] for s in shows} - reviewed)
    log = "data/unreviewed_venues.txt"
    kept = [l for l in (open(log).read().splitlines() if os.path.exists(log) else []) if not l.startswith(city + " | ")]
    for v in new:
        bills = [f'{s["date"][5:]} {s["headliner"]}' for s in shows if s["venue"] == v]
        kept.append(f"{city} | {v} | {'; '.join(bills[:3])}")
        print(f"  NEW VENUE: {v} ({'; '.join(bills[:3])})")
    open(log, "w").write("\n".join(kept) + ("\n" if kept else ""))
    for d in dropped: print("  dropped:", *d)


if __name__ == "__main__":
    main(sys.argv[1])
