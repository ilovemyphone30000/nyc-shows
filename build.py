"""Inject the show data into page.html and write the three outputs.

plain/index.html - full document, unencrypted. Gitignored.
artifact.html    - bare fragment for the private Claude artifact (its host adds the
                   doctype/head skeleton). Gitignored; it carries the client data.
index.html       - plain/index.html locked with StatiCrypt. The only page GitHub serves.

Data: shows_merged.json (after clients.py) or shows.json. The password is read from
.staticrypt-password, which is gitignored. Run after process.py and clients.py.
"""
import json, os, subprocess

page = open("page.html").read()
src = "shows_merged.json" if os.path.exists("shows_merged.json") else "shows.json"
doc = json.load(open(src))
for show in doc["shows"]:  # the page marks THE·TEAM acts; agent names never ship
    show["clients"] = [{"artist": c["artist"]} for c in show.get("clients", [])]
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
print(f"built from {src}: artifact.html, plain/index.html, index.html (locked)")
