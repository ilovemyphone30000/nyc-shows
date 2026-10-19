"""Apply the listing auditor's findings. No network.

    python3 audit_apply.py            apply confident findings, report the rest
    python3 audit_apply.py --dry      report only

Reads data/audit/findings_*.json (written by the listing-auditor agent): a list of
  {"id", "city", "action": "drop" | "support" | "keep" | "unsure", "support": [...],
   "reason", "source", "confidence": "high" | "medium" | "low"}
- drop, high confidence      -> data/drops.json   (build.py leaves the show off the page)
- support, high or medium    -> data/corrections.json, the acts added to the show's support
- everything else            -> listed in reports/audit-<date>.md for a person to decide
Nothing is ever deleted from the logs; a drop only hides a show and says why.
"""
import datetime, glob, json, os, sys

dry = "--dry" in sys.argv
# THE·TEAM's own shows are never hidden by the audit, whatever it found: read which ids carry
# client acts from the built page (local only; nothing about them is written anywhere).
page = open("artifact.html").read()
doc = json.loads(page[page.index("/*DATA*/") + 8:page.index("/*END*/")].replace("<\\/", "</"))
ours = {s["id"] for c in doc["cities"] for s in c["shows"] + c["announced"] if s.get("clients")}
found = []
for f in sorted(glob.glob("data/audit/findings_*.json")):
    found += json.load(open(f))
drops = json.load(open("data/drops.json")) if os.path.exists("data/drops.json") else {"_about": "", "nyc": {}, "chi": {}, "la": {}}
drops["_about"] = ("Shows left off the page on purpose (tributes, theme nights, talks, DJ sets, junk), by show id, "
                   "with the reason and the source that settled it. Written by audit_apply.py; edit by hand to undo.")
fixes = json.load(open("data/corrections.json"))
today = str(datetime.date.today())
applied, review = {"drop": [], "support": []}, []
for x in found:
    city, sid = x["city"], x["id"]
    bare = sid.split(":", 1)[1] if sid.startswith(city + ":") else sid
    if x["action"] == "drop" and sid in ours:
        review.append({**x, "reason": "THE·TEAM show, kept: " + x.get("reason", "")})
    elif x["action"] == "drop" and x.get("confidence") == "high":
        drops.setdefault(city, {})[bare] = {"why": x.get("reason", ""), "source": x.get("source", ""), "on": today}
        applied["drop"].append(x)
    elif x["action"] == "support" and x.get("support") and x.get("confidence") in ("high", "medium"):
        cur = fixes.setdefault(city, {}).setdefault(bare, {})
        cur["support"] = list(dict.fromkeys([*cur.get("support", []), *x["support"]]))
        cur["why"] = f"{x.get('reason', 'support confirmed')} ({x.get('source', '')}, audit {today})"
        applied["support"].append(x)
    elif x["action"] in ("drop", "support", "unsure"):
        review.append(x)
if not dry:
    json.dump(drops, open("data/drops.json", "w"), ensure_ascii=False, indent=1)
    json.dump(fixes, open("data/corrections.json", "w"), ensure_ascii=False, indent=1)
os.makedirs("reports", exist_ok=True)
names = {}
for f in glob.glob("data/audit/worklist_*.json"):
    w = json.load(open(f))
    for r in w["listings"] + [r for v in w["no_support"].values() for r in v]:
        names[r["id"]] = f"{r['headliner']} @ {r['venue']}, {r['date']}"
line = lambda x: f"- **{x.get('city', '').upper()}** {names.get(x['id'], x['id'])} ({x.get('action')}, {x.get('confidence', '?')}): {x.get('reason', '')}" + (f" — support: {', '.join(x['support'])}" if x.get("support") else "") + (f" ([source]({x['source']}))" if x.get("source", "").startswith("http") else "")
md = [f"# Listing audit {today}", "",
      f"{len(found)} shows checked: {len(applied['drop'])} hidden, {len(applied['support'])} given support, "
      f"{sum(1 for x in found if x['action'] == 'keep')} confirmed as listed, {len(review)} left for you.", "",
      "## Hidden", *map(line, applied["drop"]), "", "## Support added", *map(line, applied["support"]), "",
      "## For you to decide", *map(line, review)]
out = f"reports/audit-{today}.md"
open(out, "w").write("\n".join(md) + "\n")
print(("would apply" if dry else "applied") + f": {len(applied['drop'])} hidden, {len(applied['support'])} support added; {len(review)} for review -> {out}")
