"""Merge a browser read of Oh My Rockness (data/inbox/omr_<city>.json, announced_, onsale_)
into the files scrape.py would have written. Same window as process.py: today + 30 days.
Old in-window rows a partial read did not re-see are kept, so a short read never shrinks the list."""
import json, datetime

DAYS = 30
today = datetime.date.today(); start = str(today); end = str(today + datetime.timedelta(days=DAYS))
for c in ("nyc", "chi", "la"):
    rows = [r for r in json.load(open(f"data/inbox/omr_{c}.json")) if r[0] and r[1] and start <= r[1][:10] <= end]
    out = f"data/omr_raw_{c}.json"; fresh = {r[0] for r in rows}
    kept = [r for r in json.load(open(out)) if r[0] not in fresh and start <= r[1][:10] <= end]
    json.dump(sorted(kept + rows, key=lambda r: r[1]), open(out, "w"), ensure_ascii=False)
    open(f"data/scraped_{c}.txt", "w").write(start + "\n")
    ann = [r for r in json.load(open(f"data/inbox/announced_{c}.json")) if r[0] and r[1] and r[1][:10] >= start]
    ids = {r[0] for r in ann}
    ann += [r for r in json.load(open(f"data/inbox/onsale_{c}.json")) if r[0] and r[1] and r[1][:10] >= start and r[0] not in ids]
    json.dump(ann, open(f"data/announced_raw_{c}.json", "w"), ensure_ascii=False)
    print(c, len(rows), "scraped +", len(kept), "kept;", len(ann), "announced; last date", max([r[1][:10] for r in rows] or ["-"]))
