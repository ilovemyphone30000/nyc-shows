"""Inject shows.json into page.html -> index.html. Run after process.py."""
import json
page = open("page.html").read()
data = json.dumps(json.load(open("shows.json")), ensure_ascii=False, separators=(",", ":"))
a, b = "/*DATA*/", "/*END*/"
i, j = page.index(a) + len(a), page.index(b)
open("index.html", "w").write(page[:i] + data.replace("</", "<\\/") + page[j:])
print("index.html written")
