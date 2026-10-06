---
name: refresh-shows
description: Refresh the Shows site (NYC, Chicago, LA, Nashville, San Diego) — scrape, review new venues, load a new THE·TEAM client sheet, rebuild the locked page, run the browser checks, and publish. Use when asked to refresh, update or rebuild the shows site, add a client sheet, or do the weekly review.
---

# Refresh the shows site

Project: `/Users/jonahisaac/Downloads/scout-nyc`. Live (password-locked) at
https://ilovemyphone30000.github.io/nyc-shows/ from `main` of `ilovemyphone30000/nyc-shows`.
GitHub Actions (`.github/workflows/refresh.yml`) already refreshes it every day at 11 AM
New York time, so this skill is for the weekly review and for on-demand runs.

## Rules that do not bend

- **The repo is public; client data never goes in it.** Which acts are THE·TEAM's appears
  only inside the StatiCrypt-locked `index.html`, marked at build time. No committed data
  file may carry a `"clients"` field (an old `announced_<city>.json` did, leaking two names,
  2026-10). Agent names appear only encrypted: in `data/clients.enc` and inside the locked page (under
  each THE·TEAM show); never in plain text in any committed file. `.githooks/guard.sh` enforces this: it
  runs as the pre-commit hook (`git config core.hooksPath .githooks`) and inside
  `refresh.sh`, and refuses the commit. Never bypass it with `--no-verify`.
- **A bot-check page stops the scrape.** Never retry around it, change the user agent,
  or add proxies. Record the gap and move on; the city keeps its last good data.
- **Never request axs.com.** AXS ticket links are stored, never opened.
- Commits use the repo's pseudonymous noreply identity. Never a real name or email.

## 1. Pull and run

```bash
cd /Users/jonahisaac/Downloads/scout-nyc && git pull -q --rebase origin main
./refresh.sh --no-push
```

`refresh.sh` scrapes the three cities in parallel (the week window plus each city's
Just Announced list), then runs `process.py`, `clients.py` and `announce.py` per city,
`changes.py`, `build.py`, and `check.py` (the browser checks; all must pass).

`announce.py` keeps `data/ledger_<city>.json`, the log behind the site's **Just announced**
page (`#nyc/announced`): every show the first time a scan sees it, however far out, marked
`announced` (on OMR's Just Announced list), `added` (appeared mid-week) or `range` (only
slid into the window; not news). It only grows on a day with a good scan, and notes the
gap when the previous good scan was over 30 hours earlier.

Nashville (`nash`) and San Diego (`sd`) have no OMR site: their tabs are THE·TEAM's shows
from the client sheet ("Nashville, TN" and "San Diego, CA" tabs) plus any venue calendars
added for them in `venues.py`. San Diego drops the tab's Orange County and Temecula rows.
Both are held off the published page (`HELD` in `build.py`) until the Ticketmaster
Discovery API gives them real listings; remove a city from `HELD` to publish it.

## 1b. Venue calendars (the tracked rooms)

`venues.py` lists them (slug, city, OMR's spelling of the name, calendar URL). Read each
calendar in the user's Chrome, one page at a time, with the reader named for it in
`venue_read.js`. Post each result to the local receiver as `venue_<slug>` so it lands in
`data/inbox/`, then run `python3 venues.py` and `python3 announce.py <city>`. A venue's
first read is a baseline; after that, every show not seen before goes on the Just announced
page (deduped against OMR). Not-music and comedy are dropped by `NOT_MUSIC` in
`venues.py`; extend it rather than letting a comedian through. Never open axs.com.

## 2. Review new venues

Read `data/unreviewed_venues.txt` (`city | venue | example bills`). For each venue decide:

- **Out of town** (outside the five boroughs for NYC; far outside the metro for Chicago
  and LA, e.g. Pappy & Harriet's): add to `OUT_OF_CITY` (NYC) or that city's `out` set
  in `process.py`.
- **Not music** (comedy, podcasts, talks, screenings): add the headliner, lowercased, to
  `DROP_ACTS` (NYC) or the city's `acts` set.
- **Fine**: for NYC add it to the right borough list in `BOROUGH`; for any city add it to
  that city's list in `data/venues_reviewed.json`.

Look venues up rather than guessing when unsure. Rerun `./refresh.sh --no-push` until
`data/unreviewed_venues.txt` is empty or only lists venues you have asked the user about.

## 3. A new client sheet (only when the user provides one)

The user adds client sheets manually ("Client shows in our cities YYYY-MM-DD.xlsx").

```bash
.venv/bin/python export_clients.py "/path/to/Client shows in our cities YYYY-MM-DD.xlsx"
```

That refreshes the local exports and `data/clients.enc`. Then rerun `./refresh.sh --no-push`
and read the `clients.py` output: rows that were added rather than matched to a bill are
worth a glance — a mismatch in venue or artist spelling belongs in that city's `venue` or
`artist` map in `clients.py`.

## 4. Report and publish

Summarise for the user: `data/changes.md` (new shows, acts added to bills, shows no
longer listed), anything newly announced, venues reviewed, and the client-sheet result.
Then publish:

```bash
./refresh.sh
```

## If the daily GitHub run failed

`gh` is not installed; check https://github.com/ilovemyphone30000/nyc-shows/actions in the
browser. Common causes: a missing secret (`STATICRYPT_PASSWORD`, `CLIENTS_KEY`), a bot
check on a city (that city is skipped, the rest publish), or a check failure — reproduce
it locally with `./refresh.sh --no-push` and fix before pushing.
