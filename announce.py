"""Track when each show was first seen, and list the newly announced ones.

    python3 announce.py nyc   (or chi, la)   after scrape.py (window and --announced)

data/first_seen_<city>.json maps OMR show id -> [first_seen, show_date]. first_seen is a
UTC timestamp, or "backfill" for shows that were already listed when tracking began, so
a baseline never reads as a burst of fresh announcements. Entries for shows more than a
day in the past are pruned.

Writes data/announced_<city>.json: shows from the Just Announced list first seen in the
last seven days (the page shows the last 24 hours by the viewer's clock), cleaned by the
same rules as process.py and marked with THE·TEAM acts from the client sheet.
"""
import datetime, json, os, re, sys, unicodedata

from process import clean

city = sys.argv[1]
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
today = datetime.date.today()

announced_raw = json.load(open(f"data/announced_raw_{city}.json"))
window_raw = json.load(open(f"data/omr_raw_{city}.json"))

path = f"data/first_seen_{city}.json"
baseline = not os.path.exists(path)
first_seen = {} if baseline else json.load(open(path))
fresh = 0
for r in announced_raw + window_raw:
    if r[0] and r[0] not in first_seen:
        first_seen[r[0]] = ["backfill" if baseline else stamp, r[1][:10]]
        fresh += 0 if baseline else 1
cutoff = str(today - datetime.timedelta(days=1))
first_seen = {k: v for k, v in first_seen.items() if v[1] >= cutoff}
json.dump(first_seen, open(path, "w"), indent=0, sort_keys=True)


def norm(s):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = re.sub(r"\(.*?\)", "", s.lower().replace("&", "and"))
    return re.sub(r"^the ", "", re.sub(r"[^a-z0-9]+", " ", s).strip())


# THE·TEAM acts from the client sheet, by date (rows are [date, artist, venue, ...]).
ours = {}
if os.path.exists(f"data/clients_raw_{city}.json"):
    for r in json.load(open(f"data/clients_raw_{city}.json")):
        if r[0] and r[1]:
            ours.setdefault(r[0], set()).add(norm(str(r[1])))  # a numeric band name arrives as a number

week_ago = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
shows, _ = clean(city, announced_raw)
out = []
for s in shows:
    seen = first_seen.get(s["id"], ["backfill"])[0]
    if seen == "backfill" or seen < week_ago:
        continue
    s["firstSeen"] = seen
    s["clients"] = [{"artist": a} for a in [s["headliner"], *s["support"]] if norm(a) in ours.get(s["date"], ())]
    out.append(s)
json.dump(out, open(f"data/announced_{city}.json", "w"), indent=1, ensure_ascii=False)
print(f"{city}: {'baseline set, ' if baseline else ''}{fresh} newly seen, {len(out)} announced in the last week")
