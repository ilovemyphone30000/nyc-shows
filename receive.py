"""Receive page reads from the browser into data/inbox/ (localhost only).

    python3 receive.py        then, in the page being read:
        const f=document.createElement('form');f.method='post';f.action='http://127.0.0.1:8765/<name>';
        const t=document.createElement('textarea');t.name='d';t.value=JSON.stringify(rows);f.append(t);
        document.body.append(f);f.submit();

A plain form post, because pages may not fetch() a local address. Each post is checked to
be JSON and saved as data/inbox/<name>.json; the tab lands on "saved <name> <count>".
"""
import http.server, json, os, re, urllib.parse

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "inbox")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        name = re.sub(r"[^a-z0-9_]", "", self.path.strip("/").lower())
        body = self.rfile.read(int(self.headers["content-length"]))
        if self.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            body = urllib.parse.parse_qs(body.decode())["d"][0].encode()
        n = len(json.loads(body))
        os.makedirs(OUT, exist_ok=True)
        open(os.path.join(OUT, name + ".json"), "wb").write(body)
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<title>saved {name} {n}</title>saved {name}: {n}".encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    http.server.HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
