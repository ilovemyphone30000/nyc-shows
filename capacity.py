"""Room sizes. BIG: rooms that hold about 1,000 or more, per city (the old "1,000+ cap"
filter. Capacities are approximate (standing or largest configuration). A room left out
counts as under 1,000; add it here when one turns up on the page that belongs.
"""
BIG = {
    "nyc": {
        "Madison Square Garden", "Barclays Center", "UBS Arena", "Citi Field", "Yankee Stadium", "MetLife Stadium",
        "Forest Hills Stadium", "Radio City Music Hall", "Beacon Theatre", "Kings Theatre", "Carnegie Hall",
        "United Palace", "Apollo Theater", "Town Hall", "Hammerstein Ballroom", "Palladium Times Square",
        "Terminal 5", "Brooklyn Paramount", "Brooklyn Steel", "Brooklyn Storehouse", "Knockdown Center",
        "Webster Hall", "Irving Plaza", "Sony Hall", "Warsaw", "Pier 17", "Central Park SummerStage",
        "Riverside Church", "David Geffen Hall", "Avant Gardner", "Brooklyn Mirage", "BAM: Brooklyn Academy of Music",
    },
    "chi": {
        "United Center", "Wintrust Arena", "Allstate Arena", "Soldier Field", "Wrigley Field",
        "Huntington Bank Pavilion", "Credit One Bank Pavilion", "Aragon Ballroom", "Auditorium Theatre",
        "Chicago Theatre", "The Salt Shed", "Riviera Theatre", "House of Blues Chicago", "The Vic Theatre",
        "Concord Music Hall", "Metro", "Park West", "Radius", "Byline Bank Aragon Ballroom", "Cadillac Palace Theatre",
        "Rosemont Theatre", "Credit Union 1 Arena", "Northerly Island",
    },
    "la": {
        "Crypto.com Arena", "Kia Forum", "SoFi Stadium", "Dodger Stadium", "Rose Bowl", "Honda Center",
        "Hollywood Bowl", "The Greek Theatre", "YouTube Theater", "Peacock Theater", "Shrine Auditorium",
        "Shrine Expo Hall", "Hollywood Palladium", "The Novo", "The Wiltern", "Orpheum Theatre", "Palace Theatre",
        "The Mayan Theatre", "The United Theater on Broadway", "Walt Disney Concert Hall", "Dolby Theatre",
        "Fonda Theatre", "The Ford", "The Belasco", "The Regent Theater", "The Observatory", "House Of Blues Anaheim",
        "Garden Amphitheatre", "Pacific Amphitheatre", "Acrisure Arena", "Santa Barbara Bowl",
    },
}


# Approximate capacity of every room on the page (standing, or the largest usual
# configuration), for the cap slider. Rough by design: good for telling a 150-cap bar from a
# 600-cap club from an arena, not for settlements. A room missing here falls back to 1,500 if
# it's in BIG, else counts as unknown (shown only when the slider is at its widest).
CAP = {
    "nyc": {
        "Madison Square Garden": 19500, "Barclays Center": 19000, "UBS Arena": 17000, "Forest Hills Stadium": 13000,
        "Flushing Meadows-Corona Park": 10000, "Radio City Music Hall": 6000, "United Palace": 3400, "Pier 17": 3400,
        "Brooklyn Storehouse": 3000, "Knockdown Center": 3000, "Terminal 5": 3000, "Kings Theatre": 3000,
        "Under the K Bridge Park": 3000, "Beacon Theatre": 2900, "Carnegie Hall": 2800, "New Jersey Performing Arts Center": 2800,
        "Brooklyn Paramount": 2700, "Hammerstein Ballroom": 2200, "David Geffen Hall": 2200, "BAM: Brooklyn Academy of Music": 2100,
        "Industry City": 2000, "Brooklyn Steel": 1800, "The Capitol Theatre": 1800, "Maria Hernandez Park": 1500,
        "Pacha New York": 1500, "Town Hall": 1500, "Webster Hall": 1400, "Alice Tully Hall": 1100, "Irving Plaza": 1025,
        "Sony Hall": 1000, "Warsaw": 1000, "The Brooklyn Monarch": 1000, "MoMA PS1": 1000, "92NY": 900,
        "Pioneer Works": 800, "The Concert Hall at New York Society for Ethical Culture": 800, "Elsewhere": 700,
        "Le Poisson Rouge": 700, "Metropolitan Museum of Art": 700, "Gramercy Theatre": 650, "Music Hall of Williamsburg": 650,
        "Brooklyn Bowl": 600, "Nowadays": 600, "Bowery Ballroom": 575, "Market Hotel": 550, "Good Room": 450,
        "The Bell House": 450, "S.O.B.'s": 450, "Racket": 400, "Roulette": 400, "Crown Hill Theatre": 400,
        "BRIC House": 400, "SILO Brooklyn": 400, "SILO": 400, "Nightclub 101": 350, "Night Club 101": 350,
        "City Winery": 350, "City Winery - Pier 57": 350, "National Sawdust": 350, "Paragon": 350, "The Meadows": 300,
        "The Broadway": 300, "DROM": 300, "Refuge": 300, "David Rubenstein Atrium at Lincoln Center": 300,
        "First Unitarian Congregational Society": 300, "Rubulad": 300, "Guggenheim Museum": 300, "Mission Nightclub": 300,
        "Communities Rising Gala": 300, "H0L0": 300, "Yonkers Brewing Company": 300, "Whitney Museum": 300,
        "Old First Church": 300, "Baby's All Right": 280, "Mercury Lounge": 250, "Public Records": 250, "Union Pool": 250,
        "Saint Vitus": 250, "Rough Trade NYC": 250, "C'mon Everybody": 250, "Bowery Palace": 200, "Cassette": 200,
        "The Sultan Room": 200, "TV Eye": 200, "Purgatory": 200, "Trans-Pecos": 200, "Blue Note": 200,
        "Our Wicked Lady": 200, "Desert 5 Spot NY": 200, "Cherry Lane Theatre": 180, "Joe's Pub": 180,
        "Alphaville": 150, "The Gutter": 150, "Gold Sounds": 150, "The Wood Shop": 150, "Pianos": 150,
        "Stone Circle Theatre": 150, "Xanadu": 150, "The Chocolate Factory": 150, "Nublu Classic": 150, "Nublu 151": 150,
        "Westlight Rooftop": 150, "Union Hall": 150, "20 Meadow St": 150, "The Greene Space": 125, "Berlin": 100,
        "Hart Bar": 100, "Sleepwalk": 100, "Main Drag Music": 100, "Footlight Underground": 100, "Mama Tried": 100,
        "Bleecker Bell": 100, "P.I.T.": 100, "Dead Letter No. 9": 100, "Reforesters Laboratory": 100, "148 Frost Street": 100,
        "The Cobra Club": 100, "Bar Freda": 80, "P&T Knitwear": 80, "Rodrigue's Coffee House": 60,
    },
    "chi": {
        "Soldier Field": 61500, "FirstMerit Bank Pavilion at Northerly Island": 30000, "United Center": 23500,
        "Allstate Arena": 18000, "Hard Rock Casino Northern Indiana - Hard Rock Live": 7000, "Aragon Ballroom": 5000,
        "Auditorium Theatre": 3900, "Chicago Theatre": 3600, "The Salt Shed": 3600, "Radius": 3000, "Riviera Theatre": 2500,
        "Navy Pier": 1800, "Grand Ballroom at Navy Pier": 1800, "House of Blues Chicago": 1800, "Ramova Theatre": 1800,
        "Serum @ Prysm Nightclub": 1500, "The Vic Theatre": 1400, "Concord Music Hall": 1300, "Metro": 1100,
        "Park West": 1000, "Thalia Hall": 800, "Chop Shop": 800, "Outset": 800, "Bottom Lounge": 700,
        "Epiphany Center For The Arts": 600, "Lincoln Hall": 500, "Judson & Moore Distillery": 500, "La Herradura": 500,
        "Nightmare on Chicago Street": 500, "Old Town School of Folk Music": 425, "Subterranean": 400, "Garcia's": 400,
        "Empty Bottle": 400, "Reggie's Rock Club": 400, "Avondale Music Hall": 400, "Spybar": 400, "Smartbar": 400,
        "FitzGerald's": 400, "SPACE": 300, "Color Club": 300, "City Winery": 300, "Howlin' at the Moon": 300,
        "Cobra Lounge": 250, "Beat Kitchen": 250, "Sleeping Village": 250, "Schubas": 165, "The Burlington": 150,
        "Hideout": 150, "Lowdown": 150, "Constellation": 150, "Three Top Lounge": 150, "GMan Tavern": 100, "Cole's": 100,
    },
    "la": {
        "SoFi Stadium": 70000, "Exposition Park": 20000, "Crypto.com Arena": 20000, "Intuit Dome": 18000,
        "Honda Center": 18000, "Kia Forum": 17500, "Hollywood Bowl": 17500, "Ventura County Fairgrounds": 10000,
        "Great Park, Irvine": 10000, "Great Park Live": 10000, "OC Fair & Event Center": 8000, "Shrine Auditorium": 6300,
        "YouTube Theater": 6000, "The Greek Theatre": 5900, "Shrine Expo Hall": 5000, "Sunset Strip": 5000,
        "Santa Barbara Bowl": 4500, "Hollywood Palladium": 4000, "Dolby Theatre": 3400, "Redondo Beach Harbor": 3000,
        "Hollywood Forever": 2500, "The Novo": 2400, "Walt Disney Concert Hall": 2265, "Garden Amphitheatre": 2000,
        "Orpheum Theatre": 2000, "City Market": 2000, "City Hall Park": 2000, "The Wiltern": 1850, "Grove of Anaheim": 1700,
        "The Bellwether": 1600, "United Theater on Broadway": 1600, "The United Theater on Broadway": 1600,
        "The Belasco": 1500, "Exchange LA": 1500, "The Mayan Theatre": 1500, "Avalon": 1500, "Fonda Theatre": 1200,
        "The Ford": 1200, "The Regent Theater": 1100, "The Observatory": 1000, "House Of Blues Anaheim": 1000,
        "Pacific Electric": 1000, "Aviator Nation Dreamland": 1000, "Coast Film and Music Festival Presents Concerts In The Canyon 2026": 1000,
        "LACMA": 1000, "Moon Block Party": 1000, "Catch One": 1000, "El Rey Theatre": 800, "The Glass House": 800,
        "Echoplex": 700, "Teragram Ballroom": 600, "TIME Nightclub": 600, "Whisky a Go-Go": 500, "The Roxy": 500,
        "Lodge Room": 500, "Non Plus Ultra": 500, "1720": 500, "Los Globos": 500, "Chapman University": 500,
        "Troubadour": 400, "Knucklehead Hollywood": 400, "Sound Nightclub": 400, "Ukranian Cultural Center": 400,
        "The Echo": 350, "Blue Note Los Angeles": 300, "Sid The Cat Auditorium": 300, "2220 Arts + Archives": 300,
        "The Haven": 300, "Casita Hollywood": 300, "Amoeba Music Hollywood": 300, "Hollywood Roosevelt Hotel": 300,
        "Pico-Union Project": 300, "Largo": 280, "Moroccan Lounge": 250, "Zebulon": 250, "The Peppermint Club": 250,
        "Gold-Diggers": 250, "El Cid": 250, "Oblivion": 200, "The Airliner": 200, "The Grammy Museum": 200,
        "Alex's Bar": 200, "The Venice West": 200, "Don Quixote": 200, "The Mint": 200, "The Spotlight": 200,
        "The Wayfarer": 200, "Harvard & Stone": 200, "Bob Baker Marionette Theater": 200, "Scribble": 150,
        "The Smell": 150, "Townhouse Venice": 150, "Kiss Kiss Bang Bang": 150, "Permanent Records Roadhouse": 100,
        "Milky's": 100, "The Sardine": 100, "Club Tee Gee": 100, "In Sheep's Clothing HQ": 100, "Run Out Groove Records": 100,
        "Healing Force of the Universe": 50, "Cafe Trieste": 50,
    },
}


def cap(city, venue):
    """A room's approximate capacity, or None when unknown."""
    return CAP.get(city, {}).get(venue) or (1500 if venue in BIG.get(city, ()) else None)
