"""Scrape one week of Oh My Rockness listings for a city with Playwright.

    .venv/bin/python scrape.py nyc 2026-09-28 2026-10-04
    .venv/bin/python scrape.py chi 2026-09-28 2026-10-04
    .venv/bin/python scrape.py la  2026-09-28 2026-10-04

Writes data/omr_raw_<city>.json as rows of
[id, iso_datetime, [acts], venue, extra, age, ticket_label, ticket_url, omr_pick].

House rules (from the handoff brief): one page, one at a time, with a pause between
pages; a challenge page means stop and record the gap, never retry or disguise the
browser; ticket links keep no query string; axs.com is stored as a link, never opened.
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

HOSTS = {"nyc": "www.ohmyrockness.com", "chi": "chicago.ohmyrockness.com", "la": "losangeles.ohmyrockness.com"}
CHALLENGE = ("Just a moment", "Verify you are human", "fair fan experience")

EXTRACT = r"""() => {
  function unwrap(h){ if(!h) return null; try{ let u=new URL(h, location.origin);
    const inner=u.searchParams.get('u')||u.searchParams.get('url')||u.searchParams.get('murl');
    if(inner && /^https?:/.test(inner)) u=new URL(inner); return u.origin+u.pathname; }catch(e){ return null } }
  return [...document.querySelectorAll('.row.vevent')].map(r => {
    const bands = r.querySelector('.bands').cloneNode(true);
    bands.querySelectorAll('.recommended').forEach(e => e.remove());
    const t = r.querySelector('a.ticketLink');
    const info = r.querySelector('a.show-more-info')?.getAttribute('href') || '';
    return [info.match(/\/shows\/(\d+)/)?.[1], r.querySelector('.dtstart .value-title')?.title,
      bands.textContent.replace(/\s+/g,' ').trim().split(/\s*,\s*/).filter(Boolean),
      r.querySelector('.venue .fn')?.textContent.trim(), [], r.querySelector('.age')?.textContent.trim() || null,
      t?.textContent.trim() || null, unwrap(t?.getAttribute('href')), r.querySelector('.recommended') ? 1 : 0];
  });
}"""


def scrape(city, start, end, max_pages=15, pause=1.5):
    host = HOSTS[city]
    rows, seen = [], set()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for n in range(1, max_pages + 1):
            page.goto(f"https://{host}/shows?page={n}", wait_until="domcontentloaded")
            try:  # listings render client-side; ads keep the network busy, so wait for rows
                page.wait_for_selector(".row.vevent", timeout=20000)
            except Exception:
                pass
            text = page.inner_text("body")
            if any(c in text for c in CHALLENGE):
                print(f"  page {n}: challenge page, stopping here", file=sys.stderr)
                break
            got = page.evaluate(EXTRACT)
            if not got:
                break
            for r in got:
                if r[0] in seen or not r[1]:
                    continue
                seen.add(r[0])
                if start <= r[1][:10] <= end:
                    rows.append(r)
            print(f"  page {n}: {len(got)} listings, through {got[-1][1][:10]}", file=sys.stderr)
            if got[-1][1][:10] > end:
                break
            time.sleep(pause)
        browser.close()
    return rows


if __name__ == "__main__":
    city, start, end = sys.argv[1:4]
    rows = scrape(city, start, end)
    os.makedirs("data", exist_ok=True)
    out = f"data/omr_raw_{city}.json"
    # OMR drops a day once it has passed, so keep earlier rows in range that this run
    # no longer sees (yesterday's shows); fresh rows win for anything listed again.
    fresh = {r[0] for r in rows}
    kept = [r for r in (json.load(open(out)) if os.path.exists(out) else [])
            if r[0] not in fresh and start <= r[1][:10] <= end]
    json.dump(sorted(kept + rows, key=lambda r: r[1]), open(out, "w"), ensure_ascii=False)
    print(f"{city}: {len(rows)} scraped + {len(kept)} kept from earlier, {start}..{end} -> {out}")
