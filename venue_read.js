// Readers for the 16 venue calendars, run in the user's own Chrome (javascript_tool) on
// the page listed in venues.py. Each returns a list of {name, support?, start?|date?, time?, url}
// for data/inbox/venue_<slug>.json; venues.py normalizes them. Post the list to the local
// receiver as a form (fetch to localhost is blocked from these pages):
//   const f=document.createElement('form');f.method='post';f.action='http://127.0.0.1:8765/venue_<slug>';
//   const t=document.createElement('textarea');t.name='d';t.value=JSON.stringify(out);f.append(t);document.body.append(f);f.submit();
// Never open axs.com links (Pier 17's "View all shows" goes there; read its own page only).

// 1. schema.org JSON-LD. palladium, radiocity, aragon, chicagotheatre, beacon, hammerstein,
//    terminal5, hollywoodforever. Terminal 5 (Ticketmaster) lists 20 at a time: click
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
  const w = pre.find(s => /^with /i.test(s));
  return { name: pre.find(s => !/^with /i.test(s)), support: w ? w.replace(/^with /i, "") : null, date: L[di] || null, url: a.href };
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
