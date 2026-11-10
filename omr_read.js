// Oh My Rockness browser read (the built-in browser, one tab). Each city is its own origin,
// so run this whole file once on each city's first page; it defines two helpers in
// sessionStorage and reads that first page.
//   per page:   navigate to ?page=N, then run  await eval(sessionStorage.__acc)
//               -> [path, rows on page, first date, last date, total so far, bot check?]
//   when done:  eval(sessionStorage.__post)('omr_nyc')   (posts to the receive.py on PORT)
//   new list:   sessionStorage.__rows='[]'  before the first page of the next list
// Stop the moment the last field is true (bot check): never retry around it.
const PORT = 8767;
sessionStorage.__acc = `(async()=>{for (let i=0;i<20 && !document.querySelector('.row.vevent');i++) await new Promise(r=>setTimeout(r,500));
function unwrap(h){ if(!h) return null; try{ let u=new URL(h, location.origin);
  const inner=u.searchParams.get('u')||u.searchParams.get('url')||u.searchParams.get('murl');
  if(inner && /^https?:/.test(inner)) u=new URL(inner); return u.origin+u.pathname; }catch(e){ return null } }
const rows=[...document.querySelectorAll('.row.vevent')].map(r => {
  const bands = r.querySelector('.bands').cloneNode(true);
  bands.querySelectorAll('.recommended').forEach(e => e.remove());
  const acts = [];
  for (const n of bands.childNodes) {
    if (n.nodeName === 'A') { const t = n.textContent.replace(/\\s+/g,' ').trim(); if (t) acts.push(t); }
    else acts.push(...n.textContent.replace(/\\s+/g,' ').split(/\\s*,\\s*/).map(x => x.trim()).filter(Boolean));
  }
  const t = r.querySelector('a.ticketLink');
  const info = r.querySelector('a.show-more-info')?.getAttribute('href') || '';
  return [info.match(/\\/shows\\/(\\d+)/)?.[1], r.querySelector('.dtstart .value-title')?.title, acts,
    r.querySelector('.venue .fn')?.textContent.trim(), [], r.querySelector('.age')?.textContent.trim() || null,
    t?.textContent.trim() || null, unwrap(t?.getAttribute('href')), r.querySelector('.recommended') ? 1 : 0];
});
const all=JSON.parse(sessionStorage.__rows||'[]').concat(rows);
sessionStorage.__rows=JSON.stringify(all);
return [location.pathname+location.search, rows.length, rows[0]?.[1]?.slice(0,10), rows.at(-1)?.[1]?.slice(0,10), all.length, /Just a moment|Verify you are human|security verification/.test(document.title+document.body.innerText)]})()`;
sessionStorage.__post = `(n)=>{const f=document.createElement('form');f.method='post';f.action='http://127.0.0.1:${PORT}/'+n;const t=document.createElement('textarea');t.name='d';t.value=sessionStorage.__rows;f.append(t);document.body.append(f);f.submit();}`;
sessionStorage.__rows = '[]';
await eval(sessionStorage.__acc)
