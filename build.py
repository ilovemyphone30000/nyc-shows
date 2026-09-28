"""Inject shows.json into page.html.

index.html    - full document for GitHub Pages (doctype, charset, viewport added here).
artifact.html - bare fragment for the Claude artifact, whose host adds that skeleton itself.
Run after process.py.
"""
import json
page = open("page.html").read()
data = json.dumps(json.load(open("shows.json")), ensure_ascii=False, separators=(",", ":"))
a, b = "/*DATA*/", "/*END*/"
i, j = page.index(a) + len(a), page.index(b)
body = page[:i] + data.replace("</", "<\\/") + page[j:]
open("artifact.html", "w").write(body)
open("index.html", "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n'
    + body + "\n</html>\n")
print("index.html + artifact.html written")
