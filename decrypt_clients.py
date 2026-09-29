"""On GitHub Actions: decrypt data/clients.enc with the CLIENTS_KEY secret into
data/clients_raw_<city>.json for clients.py. Without the key, those files are left
alone and the page builds with no THE·TEAM highlighting."""
import json, os, sys
from cryptography.fernet import Fernet

key = os.environ.get("CLIENTS_KEY")
if not key:
    sys.exit("CLIENTS_KEY is not set")
data = json.loads(Fernet(key.strip()).decrypt(open("data/clients.enc", "rb").read()))
for city, rows in data.items():
    json.dump(rows, open(f"data/clients_raw_{city}.json", "w"), ensure_ascii=False)
print(", ".join(f"{k}: {len(v)}" for k, v in data.items()))
