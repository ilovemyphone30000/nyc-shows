"""The tracked venues, read straight from their own calendars.

    python3 venues.py            data/inbox/venue_<slug>.json -> data/venue_raw_<city>.json

The calendars are read in a real browser (see .claude/skills/refresh-shows/SKILL.md, "Venue
calendars"); each lands in data/inbox/venue_<slug>.json as a list of
{name, support?, start? | date?, time?, url}. This normalizes them into OMR's raw row shape
so process.clean() and announce.py treat them like any other listing:
    [id, iso_datetime, [acts], venue, [], None, "Tickets", url, 0]
data/venue_raw_<city>.json is {"scanned": {venue: date}, "seenAt": {id: UTC time}, "rows": [...]};
seenAt holds announcement times a source states itself (a newsletter's send date). A venue's rows are
replaced whenever that venue is read again, and venues not read this time keep theirs.
"""
import datetime, glob, html, json, os, re, unicodedata

# slug -> (city, venue name as OMR spells it, calendar page)
VENUES = {
    "palladium":       ("la",  "Hollywood Palladium",   "https://www.hollywoodpalladium.com/shows"),
    "fonda":           ("la",  "Fonda Theatre",         "https://www.fondatheatre.com/shows"),
    "novo":            ("la",  "The Novo",              "https://www.thenovodtla.com/shows"),
    "radiocity":       ("nyc", "Radio City Music Hall", "https://www.livenation.com/venue/KovZpZAE7vdA/radio-city-music-hall-events"),
    "websterhall":     ("nyc", "Webster Hall",          "https://www.websterhall.com/shows"),
    "pier17":          ("nyc", "Pier 17",               "https://rooftopatpier17.com/concerts/"),
    "saltshed":        ("chi", "The Salt Shed",         "https://www.saltshedchicago.com/"),
    "aragon":          ("chi", "Aragon Ballroom",       "https://www.aragonballroomchicago.com/shows"),
    "chicagotheatre":  ("chi", "Chicago Theatre",       "https://www.livenation.com/venue/KovZpZA6AJ6A/the-chicago-theatre-events"),
    "beacon":          ("nyc", "Beacon Theatre",        "https://www.livenation.com/venue/KovZpZAEAd6A/beacon-theatre-events"),
    "hammerstein":     ("nyc", "Hammerstein Ballroom",  "https://www.livenation.com/venue/KovZpZAEAE6A/manhattan-center-hammerstein-ballroom-events"),
    "terminal5":       ("nyc", "Terminal 5",            "https://www.ticketmaster.com/terminal-5-tickets-new-york/venue/1112"),
    "greek":           ("la",  "The Greek Theatre",     "https://www.lagreektheatre.com/events-tickets/"),
    "hollywoodbowl":   ("la",  "Hollywood Bowl",        "https://www.hollywoodbowl.com/events/performances"),
    "ford":            ("la",  "The Ford",              "https://www.theford.com/events/performances"),
    "hollywoodforever": ("la", "Hollywood Forever",     "https://hollywoodforever.com/events-calendar/"),
    # Its calendar is on TicketWeb, 20 a page: read ?page=1, 2, ... until a page comes back empty.
    "nightclub101":    ("nyc", "Nightclub 101",         "https://www.ticketweb.com/venue/night-club-101-new-york-ny/686683"),
}
# Not concerts. Jonah's standing rule: never comedy. Also talks, podcasts, drag, wrestling,
# film screenings (incl. live-to-film "in Concert"), open houses, merch and parking listings.
NOT_MUSIC = re.compile(r"(?i)\b(comedy|comedian|stand-?up|podcast|anniversary screening|open house|halloween|"
    r"dia de los muertos|peculiar worlds|jennifer.s body|the thing \(1982\)|carrie 50th|rocky horror|from dusk till dawn|"
    r"main character energy|smartless|world.s largest karaoke|drag race|king of drag|sanderson sister|wwe|"
    r"in concert$|live-to-screen|movie tour|not an event ticket|ga pass|conference|30 rock|rachel maddow|"
    r"jerry seinfeld|aziz ansari|john oliver|seth meyers|kara swisher|lucy darling|gary owen|elon gold|zarna garg|"
    r"mulaney|josh johnson|matt mathews|jeff arcuri|brad williams|ben schwartz|brett goldstein|dl hughley|joey diaz|"
    r"bert kreischer|ron white|nikki glaser|nurse john|george lopez|aries spears|basement yard|ali wong|iliza|"
    r"variety show|vir das|matt rogers|two cuzzos|chicks in the office|yohay sponder|fred armisen|starbomb)")
# Promoters that put their name first: "Insomniac presents Valentino Khan" -> Valentino Khan.
PROMOTERS = re.compile(r"(?i)^(?:ny comedy festival|insomniac|bassrush|mixed feelings|93xrt winter jam|voil[aà]|"
                       r"goldenvoice(?: & cmn)?|lucid live music & aivn|project91)\s+presents?\b[\s:–-]*")
BILL_AS_LIST = {"nightclub101"}  # calendars that title a show with its whole comma-separated bill
WITH_IN_NAME = {"sleeping with sirens"}  # bands whose name contains "with"
KEEP_UPPER = {"DJ", "MC", "UK", "USA", "NYC", "LA", "II", "III", "IV", "AJ", "TV", "EP", "LP", "XRT"}
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
today = datetime.date.today()


def slugify(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def tidy_case(n):
    """ALL-CAPS calendar names -> title case, keeping DJ, D.C. and the like."""
    if not (n.isupper() and len(n) > 4):
        return n
    return " ".join(w if w in KEEP_UPPER or "." in w.strip(".") else w[:1] + w[1:].lower() for w in n.split(" "))


def split_name(name):
    """Calendar title -> (headliner, [support]). Drops tour names, show-added notes and age limits;
    'X with Y' / 'X w/ Y' puts Y in support."""
    n = html.unescape(name or "").strip().strip("“”\"' ")
    n = PROMOTERS.sub("", n)
    n = re.sub(r"(?i)^(?:an evening (?:of mud )?with|a night with)\s+", "", n)
    n = re.sub(r"[’']s\s+[‘'].*$", "", n)  # for KING + COUNTRY’s ‘The Most Beautiful Colours’ Tour
    n = re.sub(r'\s+".*$', "", n)  # EL TRI "ADICTO AL ROCANROL"
    n = re.sub(r"\s+\?{2,}\s+.*$", "", n)  # a dash lost to encoding
    n = re.sub(r"(?i)\s*\((?:\d\d\+[^)]*|\d\d and over|all ages[^)]*|solo|live|moved to[^)]*|concert only)\)", "", n)
    n = re.sub(r"\s*\([^)]*\)", "", n)  # SEX PISTOLS (Steve Jones, Paul Cook, Glen Matlock)
    n = re.sub(r"(?i)\s*-\s*(?:\d\w\w show added!?|ages \d\d\+|all ages.*)$", "", n)
    head, *rest = re.split(r"(?i)\s+[-–—]\s*|[-–—]\s+|:\s+|\s+@\s+|\s+presents?\b\s*", n, maxsplit=1)
    support = []
    m = [head] if head.lower() in WITH_IN_NAME else re.split(r"(?i)\s+(?:with special guests?|with|w/|feat\.|featuring)\s+", head, maxsplit=1)
    if len(m) == 2:
        head = m[0]
        support = [x.strip() for x in re.split(r",\s*(?:and\s+|&\s+)?|\s+and\s+|\s+&\s+", re.sub(r"(?i)^special guests?\s+", "", m[1])) if x.strip()]
    if re.search(r"[a-z]", head):  # mixed case: drop a trailing ALL-CAPS tour name ("San Holo TRUE LOVE ... Tour")
        head = re.sub(r"(?:\s+[A-Z0-9'’.]{2,}){2,}(?:\s+\S+)*?\s+(?i:tour)(?:\s+20\d\d)?$", "", head) or head
    head = re.sub(r"(?i)\s+tour\b.*$", "", head) if re.search(r"(?i)\s+tour\b", head) and head.split()[0].isupper() else head
    return tidy_case(head.strip()), [tidy_case(x) for x in support]


def when(item):
    """-> (YYYY-MM-DD, HH:MM) from whichever date shape the calendar gave."""
    if item.get("start"):
        return item["start"][:10], item["start"][11:16] or None
    for src in (item.get("url") or "", item.get("date") or ""):
        m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", src)
        if m:
            d = m.group(0)
            break
    else:
        t = (item.get("date") or "").replace(".", "")
        m = re.search(r"([A-Za-z]{3})[a-z]*,?\s+(\d{1,2}),?\s+(20\d\d)", t) or re.search(r"([A-Za-z]{3})[a-z]*\s+(\d{1,2})\b", t)
        if not m or m.group(1).lower() not in MONTHS:
            return None, None
        mo, dy = MONTHS[m.group(1).lower()], int(m.group(2))
        if m.lastindex == 3:
            y = int(m.group(3))
        else:  # no year printed: the next time that date comes round (allowing a week of lag)
            y = today.year if datetime.date(today.year, mo, dy) >= today - datetime.timedelta(days=7) else today.year + 1
        d = f"{y}-{mo:02d}-{dy:02d}"
    tm = re.search(r"(\d{1,2}):(\d\d)\s*([ap])m", (item.get("time") or "") + " " + (item.get("date") or ""), re.I)
    t = f"{int(tm.group(1)) % 12 + (12 if tm.group(3).lower() == 'p' else 0):02d}:{tm.group(2)}" if tm else None
    return d, t


def main():
    by_city, seen_at = {}, {}
    for path in sorted(glob.glob("data/inbox/venue_*.json")):
        slug = os.path.basename(path)[6:-5]
        city, venue, _ = VENUES[slug]
        rows = []
        for item in json.load(open(path)):
            if item.get("type") in ("TheaterEvent", "ComedyEvent", "ScreeningEvent", "Event"):
                continue  # TicketWeb types its events honestly (readings, cabaret, screenings)
            raw = html.unescape(item.get("name") or "")
            if not raw or NOT_MUSIC.search(raw) or re.search(r"(?i)\bpostponed\b|\bcancel|\bpresents?$", raw):
                continue
            d, t = when(item)
            if not d or d < str(today):
                continue
            if slug in BILL_AS_LIST and "," in raw:  # "Jawdropped, The Heaven": the whole bill, headliner first
                raw = raw.replace(",", " with ", 1)
            head, support = split_name(raw)
            support += [tidy_case(x.strip().lstrip("& ")) for x in re.split(r",\s*", item.get("support") or "")
                        if x.strip() and not re.search(r"(?i)produced|presented|partnership|anniversary|concerts?$|\btour\b|series|performances", x)]
            support += [p for p in item.get("perf", []) if p.lower() not in (head.lower(), "organization", "person", "performinggroup") and p not in support]
            support = [y for y in (re.sub(r"(?i)\s+presented by .*$", "", x.lstrip("& ")).strip() for x in support) if y]
            key = lambda x: re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", x.lower()))
            perf = [p for p in item.get("perf", []) if key(p)]
            if len(perf) == 1 and key(head).startswith(key(perf[0])) and key(head) != key(perf[0]):
                head = tidy_case(perf[0])  # "CAPYAC NYC Residency Night 1" -> Capyac
            seen_keys, kept = {key(head)}, []
            for x in support:  # one entry per act, and no "tba"
                if key(x) and key(x) not in seen_keys and key(x) != "tba":
                    seen_keys.add(key(x))
                    kept.append(x)
            support = kept
            url = (item.get("url") or "").split("?")[0] or None
            if url and "axs.com" in url:
                url = None  # stored, never opened; the venue's own page is linked instead
            rid = f"v-{slug}-{d}-{slugify(head)[:40]}"
            rows.append([rid, f"{d}T{t}:00" if t else d, [head, *support], venue, [], None, "Tickets", url, 0])
            if item.get("seen"):
                seen_at.setdefault(city, {})[rid] = item["seen"]
        by_city.setdefault(city, {})[venue] = sorted({r[0]: r for r in rows}.values(), key=lambda r: r[1])
        print(f"{city} {venue}: {len(rows)} shows")
    for city, fresh in by_city.items():
        out = f"data/venue_raw_{city}.json"
        old = json.load(open(out)) if os.path.exists(out) else {"scanned": {}, "rows": []}
        old.setdefault("seenAt", {}).update(seen_at.get(city, {}))
        rows = [r for r in old["rows"] if r[3] not in fresh] + [r for rs in fresh.values() for r in rs]
        old["scanned"].update({v: str(today) for v in fresh})
        json.dump({"scanned": old["scanned"], "seenAt": old["seenAt"], "rows": sorted(rows, key=lambda r: (r[3], r[1]))},
                  open(out, "w"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
