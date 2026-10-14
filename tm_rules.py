"""Which Ticketmaster events count as real shows for the dashboard. Edit here to clean up.

build.py adds a Ticketmaster event that neither Oh My Rockness nor a venue calendar gave us
(a "TM only" show) to the two-week list, and to Just announced when it's new, if it passes
every rule below. It must also be at a room we already cover: one Oh My Rockness or a venue
calendar has listed, or one in data/venues_reviewed.json. That alone keeps out jazz clubs,
symphony halls and Broadway. Each one carries a "TM only" tag on the page.

To clean up:
  - everything off ......... TM_ONLY = False
  - one room ............... add its name (any spelling) to SKIP_VENUES
  - one act ................ add it, lowercased, to SKIP_ACTS
  - a kind of music ........ add the Ticketmaster genre to SKIP_GENRES
  - one show ............... add its Ticketmaster event id (the tm:... id) to SKIP_EVENTS
"""
import re

from ticketmaster import norm

TM_ONLY = True

SKIP_GENRES = {"Jazz", "Classical", "Blues", "Religious", "Children's Music", "Holiday", "New Age"}
SKIP_NAMES = re.compile(
    r"(?i)\b(tribute|symphony|orchestra|philharmonic|opera|ballet|choir|chorus|big band|happy hour|brunch|"
    r"candlelight|nutcracker|karaoke|bingo|trivia|drag|burlesque|comedy|open mic|jam session|silent disco|"
    r"salute to|the music of|celebrat(?:es|ing) the music|plays the music|sings the|cover band|"
    r"parking|tour experience|guided tour|museum|upgrade|vip package|locker|gift card|membership|suite|"
    r"merch|hotel package|add-on|tailgate|in concert|live to film|film with live|"
    r"reading|film fest|short film|cabaret|awards?|rumble|show and tell|rave|disco|emo night|"
    r"sessions?|in the mix|disney|halloween|dance feat|k-pop night|next level k-pop|real estate|storytelling|podcast)\b")
SKIP_VENUES = set()   # e.g. {"Kingston Mines - Chicago Blues Center"}
# lowercased. Tribute bands, drag and comedy tours, a kids' show: names that don't give it away.
SKIP_ACTS = {"shane dawson", "led zeppelin 2", "bruce in the usa", "alaska thunderf**k", "bianca del rio",
             "the rock and roll playhouse"}
SKIP_EVENTS = set()   # e.g. {"G5diZ_KRvp7Ot"}

STATE = {"nyc": "NY", "chi": "IL", "la": "CA"}
NYC = {"new york", "brooklyn", "queens", "bronx", "the bronx", "staten island", "long island city", "astoria",
       "flushing", "ridgewood", "forest hills", "jamaica", "corona", "queens village", "far rockaway"}
# Words that don't tell two rooms apart ("Riviera Theatre- IL" is "Riviera Theatre").
FILLER = re.compile(r"\b(theatre|theater|ballroom|music hall|hall|club|nightclub|nyc|ny|il|ca|chicago|"
                    r"los angeles|new york|powered by.*|presented by.*|at .*)$")


def room(name):
    """A venue name reduced to what identifies the room."""
    n = norm(name)
    for _ in range(3):
        n = FILLER.sub("", n).strip()
    return n


def in_city(key, r):
    if r.get("state") != STATE[key]:
        return False
    return key != "nyc" or (r.get("city") or "").lower() in NYC


def wanted(r, known_room):
    """Is this Ticketmaster event a show the dashboard wants? known_room: the venue is one we cover."""
    if r["status"] == "cancelled" or r["tmId"] in SKIP_EVENTS:
        return False
    if r["segment"] not in ("Music", "Undefined"):
        return False
    if r["genre"] in SKIP_GENRES:
        return False
    if not known_room:  # only rooms Oh My Rockness, a venue calendar or our review already covers
        return False
    if SKIP_NAMES.search(r["name"] or ""):
        return False
    if any(room(r["venue"] or "") == room(v) for v in SKIP_VENUES):
        return False
    acts = [a.lower() for a in (r["acts"] or [r["name"] or ""])]
    return not any(a in SKIP_ACTS for a in acts)
