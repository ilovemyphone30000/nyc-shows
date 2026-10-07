"""Export the agency client-show workbook for the pipeline.

    .venv/bin/python export_clients.py "path/to/Client shows in our cities YYYY-MM-DD.xlsx"
    .venv/bin/python export_clients.py --from-local     (re-encrypt the current local export)

Writes data/clients_raw_<city>.json (gitignored) and data/clients.enc, the same rows
(date, artist, venue, city, state, agents, service agent) encrypted with the key in
.clients-key (gitignored; also the CLIENTS_KEY secret on GitHub). The daily GitHub run
decrypts clients.enc so its rebuild can show agents under THE·TEAM shows. Agent names
are only ever stored encrypted: in clients.enc and inside the password-locked page.
"""
import json, os, sys
from cryptography.fernet import Fernet

TABS = {"nyc": "New York, NY", "chi": "Chicago IL", "la": "Los Angeles, CA"}

if sys.argv[1:] == ["--from-local"]:
    by_city = {k: json.load(open(f"data/clients_raw_{k}.json")) for k in TABS}
else:
    import openpyxl
    wb = openpyxl.load_workbook(sys.argv[1], data_only=True)
    by_city = {}
    for key, tab in TABS.items():
        if tab not in wb.sheetnames:
            sys.exit(f'tab "{tab}" not found; tabs are: {", ".join(wb.sheetnames)}')
        by_city[key] = [[r[0].strftime("%Y-%m-%d") if r[0] else None, *r[1:7]]
                        for r in wb[tab].iter_rows(min_row=2, values_only=True) if any(r)]
        json.dump(by_city[key], open(f"data/clients_raw_{key}.json", "w"), ensure_ascii=False)

# date, artist, venue, city, state, agents, service agent: the first seven columns, encrypted.
slim = {k: [list(r[:7]) + [None] * (7 - len(r[:7])) for r in rows] for k, rows in by_city.items()}
if not os.path.exists(".clients-key"):
    open(".clients-key", "w").write(Fernet.generate_key().decode())
key = open(".clients-key").read().strip()
open("data/clients.enc", "wb").write(Fernet(key).encrypt(json.dumps(slim, ensure_ascii=False).encode()))
print(", ".join(f"{k}: {len(v)} rows" for k, v in slim.items()) + " -> data/clients.enc")
