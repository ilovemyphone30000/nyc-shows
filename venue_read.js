// Readers for the tracked venue calendars, run in the user's own Chrome (javascript_tool) on
// the page listed in venues.py. Each returns a list of {name, support?, start?|date?, time?, url}
// for data/inbox/venue_<slug>.json; venues.py normalizes them. Post the list to the local
// receiver as a form (fetch to localhost is blocked from these pages):
//   const f=document.createElement('form');f.method='post';f.action='http://127.0.0.1:8765/venue_<slug>';
//   const t=document.createElement('textarea');t.name='d';t.value=JSON.stringify(out);f.append(t);document.body.append(f);f.submit();
// Never open axs.com links (Pier 17's "View all shows" goes there; read its own page only).

// 1. schema.org JSON-LD. palladium, radiocity, aragon, chicagotheatre, beacon, hammerstein,
//    terminal5, hollywoodforever, nightclub101 (TicketWeb: read ?page=1, 2, ... until one is
//    empty, and keep each event's @type as `type` so readings and screenings drop out). Terminal 5 (Ticketmaster) lists 20 at a time: click
//    "More Events", then add the extra cards from reader 6.
const jsonld = () => {
  const out = [];
  const walk = o => {
    if (!o || typeof o !== "object") return;
    if (Array.isArray(o)) return o.forEach(walk);
    const t = [].concat(o["@type"] || []);
    if (t.some(x => /Event/.test(x)) && o.startDate) {
      const of = [].concat(o.offers || [])[0];
      out.push({ name: o.name, start: o.startDate, url: o.url || of?.url || null,
        perf: [].concat(o.performer || []).map(p => p?.name || p).filter(x => typeof x === "string") });
    }
    Object.values(o).forEach(walk);
  };
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => { try { walk(JSON.parse(s.textContent)); } catch (e) {} });
  return out;
};

// 2. AXS venue sites (Goldenvoice): fonda, websterhall. Lines: title, "with ...", date.
const axsCards = () => [...document.querySelectorAll('a[class*="c-axs-event-card__header"]')].filter(a => a.textContent.trim()).map(a => {
  const L = a.parentElement.innerText.split("\n").map(s => s.trim()).filter(Boolean);
  const di = L.findIndex(s => /\b20\d\d\b/.test(s));
  const pre = L.slice(0, di < 0 ? L.length : di).filter(s => !/presents?$/i.test(s) && !/^BUY|^SELECT/i.test(s));
  // first line is the headliner; every other line before the date is support, "with ..." or not
  // (Webster Hall prints "THIS IS LORELEI" / "@"; Fonda prints "with Zoe Gitter")
  const sup = pre.slice(1).map(s => s.replace(/^with /i, "")).filter(s => !/^(on sale|sold out|postponed|cancel+ed|rescheduled|tbd|tba)\b/i.test(s));
  return { name: pre[0], support: sup.join(", ") || null, date: L[di] || null, url: a.href };
});

// 3. novo: the same AXS cards, but the date comes first and has no year.
const novoCards = () => [...document.querySelectorAll('a[class*="c-axs-event-card__header"]')].filter(a => a.textContent.trim()).map(a => {
  const L = a.parentElement.innerText.split("\n").map(s => s.trim()).filter(Boolean).filter(s => !/presents?$/i.test(s) && !/^BUY|^SELECT|^Doors/i.test(s));
  const w = L.find(s => /^with /i.test(s));
  return { date: L[0], name: L[1], support: w ? w.replace(/^with /i, "") : null, url: a.href };
});

// 4. hollywoodbowl, ford (LA Phil sites): one card per "Full details" link; acts above the date.
const laPhil = () => {
  const seen = new Set(), out = [], D = /^(MON|TUE|WED|THU|FRI|SAT|SUN), [A-Z]{3,5}\.? \d/i;
  for (const a of document.querySelectorAll("a")) {
    if (!/^full details$/i.test(a.textContent.trim())) continue;
    const u = a.href.split("?")[0]; if (seen.has(u)) continue; seen.add(u);
    let c = a; for (let i = 0; i < 6; i++) { c = c.parentElement; if (c.innerText.split("\n").some(s => D.test(s.trim()))) break; }
    const L = c.innerText.split("\n").map(s => s.trim()).filter(Boolean), di = L.findIndex(s => D.test(s));
    const acts = L.slice(0, di).filter(s => !/^\+$|EXPAND/i.test(s));
    out.push({ name: acts[0], support: acts.slice(1).join(", ") || null, date: L[di], time: L[di + 1], url: u });
  }
  return out;
};

// 5. saltshed: Ticketmaster links carry the date (MM-DD-YYYY); the name follows "Doors".
const saltShed = () => {
  const seen = new Set(), out = [];
  for (const a of document.querySelectorAll('a[href*="ticketmaster.com"],a[href*="ticketweb.com"]')) {
    const u = a.href.split("?")[0]; if (seen.has(u)) continue; seen.add(u);
    let c = a; for (let i = 0; i < 6 && c && !/Doors/.test(c.innerText); i++) c = c.parentElement; if (!c) continue;
    const L = c.innerText.split("\n").map(s => s.trim()).filter(Boolean), di = L.findIndex(s => /^Doors/i.test(s));
    const m = u.match(/(\d\d)-(\d\d)-(20\d\d)/);
    out.push({ name: L[di + 1], date: m ? `${m[3]}-${m[1]}-${m[2]}` : L[di - 1], url: u });
  }
  return out;
};

// 6. Ticketmaster venue page cards beyond the JSON-LD: "Name, MM/DD/YY, H:MM PM".
const tmCards = known => {
  const out = [];
  for (const a of document.querySelectorAll('a[href*="/event/"]')) {
    const u = a.href.split("?")[0]; if (known.has(u)) continue; known.add(u);
    let c = a; for (let i = 0; i < 5; i++) { c = c.parentElement; if (/\d\d?\/\d\d?\/\d\d/.test(c.innerText)) break; }
    const m = (c.innerText.split("\n").find(s => /\d\d?\/\d\d?\/\d\d/.test(s)) || "").match(/^(.*), (\d\d?)\/(\d\d?)\/(\d\d), (\d\d?):(\d\d) (AM|PM)$/);
    if (m) out.push({ name: m[1], start: `20${m[4]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}T${String(+m[5] % 12 + (m[7] === "PM" ? 12 : 0)).padStart(2, "0")}:${m[6]}:00`, url: u });
  }
  return out;
};

// 7. pier17: the cards on rooftopatpier17.com/concerts/ ("Event Info" links).
const pier17 = () => [...document.querySelectorAll("a")].filter(a => a.textContent.trim() === "Event Info").map(a => {
  const L = a.closest(".details").innerText.split("\n").map(s => s.trim()).filter(Boolean), di = L.findIndex(s => /\b20\d\d\b/.test(s));
  return { name: L.slice(0, di).filter(s => !/presents$/i.test(s)).join(" "), date: L[di], url: a.href };
});

// 8. greek: ".item" cards, "Oct" / "09" / name / "Fri. 7:00 PM"; no year printed.
const greek = () => {
  const seen = new Set(), out = [];
  for (const it of document.querySelectorAll(".item")) {
    const a = it.querySelector('a[href*="/event/"]'); if (!a) continue;
    const u = a.href.split("?")[0]; if (seen.has(u)) continue; seen.add(u);
    const L = it.innerText.split("\n").map(s => s.trim()).filter(Boolean);
    const tk = [...it.querySelectorAll("a")].map(x => x.href).find(h => /ticketmaster/.test(h));
    out.push({ name: L[2], date: L[0] + " " + L[1], time: L.find(s => /\d:\d\d\s*[AP]M/.test(s)), url: tk || u });
  }
  return out;
};

// 9. unionpool: union-pool.com/calendar is a DICE widget. Click "LOAD MORE" until it's gone, then
//    read the cards. Titles are the whole bill ("A • B • C", or "A + B" when there is no •); dates print as
//    "Wed 27 Jan 2027 ― 7:00pm", year only when it isn't this one.
const unionPool = () => [...document.querySelectorAll("article")].map(a => {
  const t = a.querySelector(".dice_event-title"); if (!t) return null;
  const m = (t.nextElementSibling?.textContent || "").match(/(\d{1,2}) ([A-Z][a-z]{2})(?: (20\d\d))? ― (\d{1,2}:\d\d[ap]m)/);
  if (!m) return null;
  const bill = t.textContent.trim(), [head, ...rest] = bill.split(bill.includes("•") ? /\s+•\s+/ : /\s+\+\s+/);  // "Dr. S + M" is one act
  return { name: head, support: rest.join(", "), date: `${m[2]} ${m[1]}${m[3] ? ", " + m[3] : ""}`, time: m[4], url: t.href };
}).filter(Boolean);

// 10. mercurylounge: mercuryeastpresents.com/mercurylounge/, cards a page at /page/<n>/.
//     Fetch pages from that same site until one has no cards; cancelled shows are skipped. A title
//     sometimes carries the whole bill ("Toona, Kingsland", support "Toona"): the first act not
//     billed as support is the headliner.
const mercuryLounge = async () => {
  const out = [], seen = new Set();
  for (let n = 1; n < 40; n++) {
    const doc = new DOMParser().parseFromString(await (await fetch(n === 1 ? "/mercurylounge/" : `/mercurylounge/page/${n}/`)).text(), "text/html");
    const cards = [...doc.querySelectorAll(".tw-section")].filter(c => c.querySelector(".tw-name a") && c.querySelector(".tw-event-date"));
    if (!cards.length) break;
    for (const c of cards) {
      const a = c.querySelector(".tw-name a");
      if (/cancel/i.test(c.textContent) || seen.has(a.href)) continue;
      seen.add(a.href);
      const sup = [...c.querySelectorAll(".tw-attractions span")].map(s => s.textContent.trim());
      const acts = a.textContent.replace(/^\*[^*]+\*\s*/, "").trim().split(/,\s+(?!and\b)/);
      const key = x => x.toLowerCase().replace(/[^a-z0-9]/g, "");
      const head = acts.length > 1 ? acts.find(x => !sup.some(y => key(y) === key(x))) || acts[0] : acts[0];
      out.push({ name: head, support: [...acts.filter(x => x !== head), ...sup].join(", "),
        date: c.querySelector(".tw-event-date").textContent.trim(), time: c.querySelector(".tw-event-time")?.textContent, url: a.href });
    }
  }
  return out;
};
