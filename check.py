"""End-to-end check of the built page in a real browser. Run after build.py:

    .venv/bin/python check.py

Opens plain/index.html (the unlocked build) at desktop and phone sizes and exercises
the controls. Prints one line per check and exits non-zero if any fail.
"""
import os, re, sys
from playwright.sync_api import sync_playwright

URL = "file://" + os.path.abspath("plain/index.html")
failures = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


def rows(page):
    return page.locator("#out .row").count()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for label, size in [("desktop", {"width": 1280, "height": 900}), ("phone", {"width": 390, "height": 844})]:
        ctx = browser.new_context(viewport=size, accept_downloads=True, timezone_id="Asia/Tokyo")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.goto(URL)
        page.wait_for_selector("#out .row")
        print(f"--- {label} {size['width']}px")

        check("no script errors on load", not errors, "; ".join(errors[:2]))
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("no sideways scroll", overflow <= 0, f"{overflow}px too wide")
        check("compact view always", page.evaluate("document.body.classList.contains('compact')"))
        n = rows(page)
        check("shows render", n > 100, f"{n} rows")

        # cities
        for key, name in [("chi", "Chicago"), ("la", "Los Angeles"), ("nyc", "New York")]:
            page.click(f'.city[data-city="{key}"]')
            active = page.locator(".city[aria-pressed=true]").inner_text()
            check(f"{name} tab switches", name in active and rows(page) > 50, f"{rows(page)} rows")

        # filters
        all_rows = rows(page)
        page.click("#oursOnly")
        ours = rows(page)
        check("every THE·TEAM row shows its agents",
              page.locator("#out .row.ours").count() == page.locator("#out .row.ours .agents-line").count() > 0)
        check("THE·TEAM filter narrows to client shows", 0 < ours < all_rows and page.locator("#out .row:not(.ours)").count() == 0, f"{ours}")
        page.click("#oursOnly")
        page.click("#noSupport")
        check("No support filter leaves no support acts", page.locator("#out .support:not(.none)").count() == 0)
        page.click("#noSupport")
        page.fill("#q", "zzzz-no-such-act")
        check("empty search shows a message", rows(page) == 0 and page.locator(".empty").count() == 1)
        page.fill("#q", "")
        day = page.locator("#dayChips .chip").nth(2)
        day_value = day.get_attribute("data-day")
        day.click()
        heads = page.locator(".sect-head h2").all_inner_texts()
        check("day filter shows one day", len(heads) == 1, heads[0] if heads else "none")
        page.locator("#dayChips .chip").first.click()

        # venue view and back
        page.click('.tab[data-view="venue"]')
        check("venue view renders", page.locator(".venue").count() > 10)
        page.click('.tab[data-view="date"]')

        # the Just announced page: the log of shows as first seen
        page.click('#pages a[data-page="new"]')
        check("Just announced page opens", page.inner_text("#range") == "Just announced" and page.evaluate("location.hash") == "#nyc/announced")
        check("day buttons and Saved hide there", page.locator("#dayChips").is_hidden() and page.locator(".tab.saved").is_hidden())
        check("no period buttons", page.locator(".tab[data-period]").count() == 0)
        found = rows(page)
        check("30 days of announcements render", found > 0 or page.locator(".empty").count() == 1, f"{found} rows")
        heads = page.locator(".sect-head h2").all_inner_texts()
        check("grouped by day announced", all(h.startswith("Announced") for h in heads), heads[0] if heads else "none")
        page.click('.tab[data-group="date"]')
        first = page.locator("#out .row .when").all_inner_texts()
        check("show date is one list with no date headings", rows(page) == found and page.locator("#out .sect-head").count() == 0)
        ids = page.locator("#out .row").evaluate_all("rs => rs.map(r => r.dataset.ids)")
        page.click('.tab[data-group="date"]')
        rev = page.locator("#out .row").evaluate_all("rs => rs.map(r => r.dataset.ids)")
        check("clicking Show date again reverses the order", rev[:1] == ids[-1:] and "↓" in page.inner_text('.tab[data-group="date"]'))
        page.click('.tab[data-group="date"]')
        page.click('.tab[data-group="found"]')
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("announced page has no sideways scroll", overflow <= 0, f"{overflow}px")
        page.click('#pages a[data-page="week"]')
        check("back to This week", page.inner_text("#range") != "Just announced" and rows(page) > 50)

        # open a compact row by click and by keyboard
        first = page.locator("#out .row").first
        first.click(position={"x": 30, "y": 8})
        check("clicking a compact row opens it", "open" in (first.get_attribute("class") or ""))
        first.click(position={"x": 30, "y": 8})
        page.locator("#out .row").nth(1).focus()
        page.keyboard.press("Enter")
        check("Enter opens a focused row", "open" in (page.locator("#out .row").nth(1).get_attribute("class") or ""))

        # hearts, saved view, favorites export
        check("calendar button hidden with no favorites", page.locator("#icsBtn").is_hidden())
        page.locator("#out .save").first.click()
        page.click('.city[data-city="la"]')
        page.locator("#out .save").first.click()
        page.click('.city[data-city="nyc"]')
        check("Saved count is this city's", page.inner_text("#savedN") == "1", page.inner_text("#savedN"))
        btn = page.inner_text("#icsBtn")
        check("calendar button counts favorites in all cities", "2 favorites" in btn, btn)
        with page.expect_download() as dl:
            page.click("#icsBtn")
        path = dl.value.path()
        ics = open(path, encoding="utf-8", newline="").read()  # keep CRLF as written
        starts = re.findall(r"DTSTART[^:]*:(\S+)", ics)
        check("favorites file has 2 events", ics.count("BEGIN:VEVENT") == 2, dl.value.suggested_filename)
        check("event times are in UTC", all(s.endswith("Z") or len(s) == 8 for s in starts), ", ".join(starts))
        check("lines use CRLF and fold under 76 bytes",
              "\r\n" in ics and all(len(l.encode()) <= 75 for l in ics.split("\r\n")))
        with page.expect_download() as dl:
            page.locator("#out .cal").first.click()
        check("per-show calendar file downloads", dl.value.suggested_filename.endswith(".ics"), dl.value.suggested_filename)
        page.click('.tab[data-view="saved"]')
        check("Saved view shows the hearted show", rows(page) == 1)
        page.click('.tab[data-view="date"]')

        check("no expanded-view button", page.locator("#compactBtn").count() == 0)

        # deep link
        page.goto(URL + "#chicago")
        page.wait_for_selector("#out .row")
        check("#chicago opens Chicago", "Chicago" in page.locator(".city[aria-pressed=true]").inner_text())
        page.evaluate("location.hash = 'la'")
        page.wait_for_timeout(200)
        check("changing the hash switches city", "Los Angeles" in page.locator(".city[aria-pressed=true]").inner_text())
        page.goto(URL + "#chicago/announced")
        page.wait_for_timeout(300)
        check("#chicago/announced opens Chicago's Just announced", "Chicago" in page.locator(".city[aria-pressed=true]").inner_text() and page.inner_text("#range") == "Just announced")

        check("no script errors after all that", not errors, "; ".join(errors[:2]))
        ctx.close()
    browser.close()

print(f"\n{len(failures)} failed" if failures else "\nall checks passed")
sys.exit(1 if failures else 0)
