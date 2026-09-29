"""Inject the show data into page.html and write the three outputs.

plain/index.html - full document, unencrypted. Gitignored.
artifact.html    - bare fragment for the private Claude artifact (its host adds the
                   doctype/head skeleton). Gitignored; it carries the client data.
index.html       - plain/index.html locked with StatiCrypt. The only page GitHub serves.

Data: data/shows_merged_<city>.json (after clients.py) or data/shows_<city>.json, for nyc, chi, la. The password is read from
.staticrypt-password, which is gitignored. Run after process.py and clients.py.
"""
import json, os, subprocess

page = open("page.html").read()
CITIES = [("nyc", "New York"), ("chi", "Chicago"), ("la", "Los Angeles")]
doc = {"cities": []}
for key, name in CITIES:
    src = f"data/shows_merged_{key}.json"
    if not os.path.exists(src):
        src = f"data/shows_{key}.json"
    d = json.load(open(src))
    doc["week"] = d["week"]
    for show in d["shows"]:
        show["clients"] = [{"artist": c["artist"]} for c in show.get("clients", [])]  # agent names never ship
        if key != "nyc":  # OMR ids are per region; keep NYC's bare so existing saved hearts survive
            show["id"] = f"{key}:{show['id']}"
        for k in ("borough", "tier", "pick", "joined"):
            show.pop(k, None)
    doc["cities"].append({"key": key, "name": name, "checked": d["checked"], "shows": d["shows"]})
data = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
a, b = "/*DATA*/", "/*END*/"
i, j = page.index(a) + len(a), page.index(b)
body = page[:i] + data.replace("</", "<\\/") + page[j:]

open("artifact.html", "w").write(body)
os.makedirs("plain", exist_ok=True)
open("plain/index.html", "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n'
    + body + "\n</html>\n")

password = open(".staticrypt-password").read().strip()
subprocess.run([
    "npx", "--no-install", "staticrypt", "plain/index.html", "-d", ".", "--short", "--remember", "30",
    "-p", password,
    "--template-title", "NYC Shows",
    "--template-instructions", "Enter the password to see this week's shows.",
    "--template-button", "Open",
    "--template-placeholder", "Password",
    "--template-remember", "Remember me for 30 days",
    "--template-error", "That password isn't right. Try again.",
    "--template-color-primary", "#2e7040",
    "--template-color-secondary", "#fffdf8",
], check=True, stdout=subprocess.DEVNULL)
print("built " + ", ".join(f"{c['name']} {len(c['shows'])}" for c in doc["cities"]) + ": artifact.html, plain/index.html, index.html (locked)")
