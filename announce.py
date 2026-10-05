"""Keep the announcement log: every show the first time a scan sees it, however far out.

    python3 announce.py nyc   (or chi, la)   after scrape.py (window and --announced)

data/ledger_<city>.json is {"meta": {...}, "shows": {omr_id: entry}}, one entry per line:
  seen     UTC time this show was first seen; never changes once set
  how      announced  first seen on OMR's Just Announced list
           added      first seen in the week's listings on a date the previous scan already
                      covered, so it was put up mid-week
           range      first seen only because the window slid onto its date: not news
  since    set when the previous good scan was over 30 hours earlier (a blocked morning,
           say): the show went up somewhere between `since` and `seen`
  date, time, venue, headliner, support, age, ticketUrl   the latest listing; refreshed on
           every sighting, so acts added to a bill later show up here too
meta: lastScan (UTC time of the last good scan) and lastTo (the last date it covered).

Only a scan from today (data/scraped_<city>.txt) adds to the log, so a blocked morning
never reads as a quiet one. Entries go 30 days after the show. The repo is public, so no
client data is stored here; build.py marks THE·TEAM acts at build time.
"""
import datetime, json, os, sys

from process import clean

city = sys.argv[1]
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
today = datetime.date.today()
path = f"data/ledger_{city}.json"
FIELDS = ("date", "time", "venue", "headliner", "support", "age", "ticketUrl")
parse = lambda ts: datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)

announced_raw = json.load(open(f"data/announced_raw_{city}.json"))
window_raw = json.load(open(f"data/omr_raw_{city}.json"))
on_list, _ = clean(city, announced_raw)
in_window, _ = clean(city, window_raw)
on_list_ids = {s["id"] for s in on_list}

if os.path.exists(path):
    ledger = json.load(open(path))
else:
    # First run: carry over first_seen_<city>.json, the tracker this replaces. It never
    # recorded where a show was first seen, so only shows still on Just Announced count
    # as announcements; the rest are kept as "range" so they are never re-announced.
    ledger = {"meta": {}, "shows": {}}
    old = json.load(open(f"data/first_seen_{city}.json")) if os.path.exists(f"data/first_seen_{city}.json") else {}
    for s in on_list + in_window:
        if s["id"] in old and s["id"] not in ledger["shows"]:
            ledger["shows"][s["id"]] = {"seen": old[s["id"]][0], "how": "announced" if s["id"] in on_list_ids else "range",
                                        **{k: s[k] for k in FIELDS}}
    stamps = [v[0] for v in old.values() if v[0] != "backfill"]
    if stamps:
        ledger["meta"] = {"lastScan": max(stamps), "lastTo": max((r[1][:10] for r in window_raw), default=None)}

meta, log = ledger["meta"], ledger["shows"]
scanned = open(f"data/scraped_{city}.txt").read().strip() if os.path.exists(f"data/scraped_{city}.txt") else ""
added = 0
if scanned == str(today):
    prev = meta.get("lastScan")
    gap = bool(prev) and now - parse(prev) > datetime.timedelta(hours=30)
    for s in on_list + in_window:
        e = log.get(s["id"])
        if e:
            e.update({k: s[k] for k in FIELDS})
            continue
        if s["id"] in on_list_ids:
            how = "announced"
        elif meta.get("lastTo") and str(today) <= s["date"] <= meta["lastTo"]:
            how = "added"
        else:
            how = "range"
        log[s["id"]] = {"seen": stamp, **({"since": prev} if gap else {}), "how": how, **{k: s[k] for k in FIELDS}}
        added += how != "range"
    meta["lastScan"] = stamp
    meta["lastTo"] = max((s["date"] for s in in_window), default=meta.get("lastTo"))
    note = f"{added} new announcements" + (f" (first good scan since {prev[:10]})" if gap else "")
else:
    note = f"no scan today (last {scanned or 'never'}), log unchanged"

cutoff = str(today - datetime.timedelta(days=30))
ledger["shows"] = log = {k: v for k, v in sorted(log.items(), key=lambda kv: (kv[1]["seen"], kv[1]["date"], kv[0])) if v["date"] >= cutoff}
with open(path, "w") as f:  # one show per line, so each day's commit diff reads as a list of what's new
    f.write('{"meta": ' + json.dumps(meta) + ', "shows": {\n')
    f.write(",\n".join(json.dumps(k) + ": " + json.dumps(v, ensure_ascii=False) for k, v in log.items()))
    f.write("\n}}\n")
counts = {h: sum(v["how"] == h for v in log.values()) for h in ("announced", "added", "range")}
print(f"{city}: {note}; log holds {counts['announced']} announced, {counts['added']} added mid-week, {counts['range']} other")
