---
name: refresh-shows
description: Refresh the Shows site (NYC, Chicago, LA) — scrape, review new venues, load a new THE·TEAM client sheet, rebuild the locked page, run the browser checks, and publish. Use when asked to refresh, update or rebuild the shows site, add a client sheet, or do the weekly review.
---

# Refresh the shows site

Project: `/Users/jonahisaac/Downloads/scout-nyc`. Live (password-locked) at
https://ilovemyphone30000.github.io/nyc-shows/ from `main` of `ilovemyphone30000/nyc-shows`.
Nothing runs on a schedule: the daily GitHub Actions run (`.github/workflows/refresh.yml`) was
turned off on 2026-10-11 because Oh My Rockness blocked it most mornings. Refreshes happen when
the user asks; read OMR in their Chrome at a human pace (the browser fallback) and publish.
The workflow can still be started by hand from the repo's Actions tab.

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
`announced` (on OMR's Just Announced or On Sale Soon list), `added` (appeared mid-week) or `range` (only
slid into the window; not news). It only grows on a day with a good scan, and notes the
gap when the previous good scan was over 30 hours earlier.

## 1a. Ticketmaster (Discovery API)

`ticketmaster.py` runs inside `refresh.sh`. It needs `TICKETMASTER_API_KEY`, from the
environment or `.env` (gitignored; the guard also refuses any commit containing the key).
One sweep per city pulls every Music and "Undefined" event within a radius of the city for a
year (about 35 requests in all), then matches our shows locally by date and act. A show with a
Ticketmaster ticket link the sweep missed gets one lookup by headliner; misses wait 3 days.
It paces itself at 4 requests a second and stops well short of the 5,000-a-day quota.
Output, all gitignored, in `data/tm/`: `market_<city>.json` (the whole calendar, with
`firstSeen`), `<city>.json` (our shows matched). `build.py` adds the acts Oh My Rockness left
off to each show's support, plus price range, on-sale/presale date and a cancelled/postponed
tag. Ticketmaster events no other source has ("TM only", tagged on the page) are added to the
two-week list and Just announced when they pass `tm_rules.py`: a room we already cover, not
jazz/classical/blues/religious/kids, no tributes, theme nights or talks. Clean up there
(`TM_ONLY = False` turns them all off; or skip a venue, act, genre or event id). `python3 audit_tm.py` writes `reports/ticketmaster-audit.html`: recently announced on
Ticketmaster (and whether we have it), Ticketmaster concerts missing from the two-week list,
shows with no support, support added, status flags, and every room with its size class.

## 1c. Export (on the page)

Just announced has an **Export** button: cities, announced window (24h / 3 / 7 / 14 / 30 days or
since a date), optional show-date range, the page's own filters (cap slider, THE·TEAM only, no
support, search), a "Favorite venues only" box, columns and sort, then **Copy text** (venue headings,
`* [Artist](tickets) – Tue 9/29`), **Download CSV** (headliners as HYPERLINK cells) or **Save PDF**
(the browser's print dialog; grouped by city, headliners linked). Favorite venues are `FAV_VENUES`
in page.html, with a toggle on both pages. A headliner naming 3+ artists is a "Shared bill", not
"No support". Agents export only when their column is ticked. To make one for the user without the
page, drive plain/index.html with Playwright the same way and save to reports/ (gitignored).

## 1d. Listing audit (agent)

`python3 audit_prep.py --parts 2` writes worklists to data/audit/ (gitignored). Run the (Sonnet)
`listing-auditor` agent (.claude/agents/listing-auditor.md) once per worklist, in parallel. It
drops tributes, theme and DJ nights, talks, film, packages and duplicates, and checks every
"No support listed" show against a second source (venue site, allowed ticket page, web search;
never Ticketmaster/Live Nation/TicketWeb/AXS pages). Then `python3 audit_apply.py`: confident
drops go to data/drops.json (build hides them), found support to data/corrections.json, the
rest to reports/audit-<date>.md for the user. THE·TEAM shows are never hidden by the audit.

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

## If a GitHub run failed

`gh` is not installed; check https://github.com/ilovemyphone30000/nyc-shows/actions in the
browser. Common causes: a missing secret (`STATICRYPT_PASSWORD`, `CLIENTS_KEY`), a bot
check on a city (that city is skipped, the rest publish), or a check failure — reproduce
it locally with `./refresh.sh --no-push` and fix before pushing.
