"""What changed since the last run, per city -> data/changes.md.

    python3 changes.py <snapshot dir>

The snapshot dir holds the previous data/shows_<city>.json files (refresh.sh copies them
before processing). Reports newly listed shows, bills that gained an act since first
seen, and shows that dropped off while still upcoming (often cancellations).
"""
import datetime, json, os, sys

snap = sys.argv[1]
today = str(datetime.date.today())
NAMES = {"nyc": "New York", "chi": "Chicago", "la": "Los Angeles", "nash": "Nashville", "sd": "San Diego"}
out = [f"## Changes since the last refresh ({today})", ""]
total = 0

for city, name in NAMES.items():
    prev_path = os.path.join(snap, f"shows_{city}.json")
    if not os.path.exists(prev_path):
        continue
    prev = {s["id"]: s for s in json.load(open(prev_path))["shows"]}
    cur = {s["id"]: s for s in json.load(open(f"data/shows_{city}.json"))["shows"]}
    line = lambda s: f'{s["date"][5:]} {s["headliner"]}' + (f' + {", ".join(s["support"])}' if s["support"] else "") + f' @ {s["venue"]}'

    # Only compare days both runs cover: the window slides a day each run.
    lo = max(min((s["date"] for s in prev.values()), default=today), today)
    hi = min(max((s["date"] for s in prev.values()), default=today), max((s["date"] for s in cur.values()), default=today))
    added = [cur[i] for i in cur if i not in prev and lo <= cur[i]["date"] <= hi]
    gone = [prev[i] for i in prev if i not in cur and lo <= prev[i]["date"] <= hi]
    grew = []
    for i in cur.keys() & prev.keys():
        more = [a for a in cur[i]["support"] if a not in prev[i]["support"] and a != prev[i]["headliner"]]
        if more:
            grew.append((cur[i], more))

    if not (added or gone or grew):
        continue
    out.append(f"### {name}")
    for s in sorted(added, key=lambda s: s["date"]):
        out.append(f"- **New:** {line(s)}")
    for s, more in sorted(grew, key=lambda x: x[0]["date"]):
        out.append(f'- **Added to the bill:** {", ".join(more)} → {s["date"][5:]} {s["headliner"]} @ {s["venue"]}')
    for s in sorted(gone, key=lambda s: s["date"]):
        out.append(f"- **No longer listed:** {line(s)}")
    out.append("")
    total += len(added) + len(gone) + len(grew)

if total == 0:
    out.append("No changes to the listings already on the page.")
open("data/changes.md", "w").write("\n".join(out) + "\n")
print(f"{total} changes -> data/changes.md")
