#!/usr/bin/env python3
"""Trail Strength Log server: serves index.html and keeps the training log in data.json.

Standard library only (Python 3.8+). Run:  python3 server.py
Settings come from environment variables:
  TSL_HOST  address to listen on (default 127.0.0.1, put `tailscale serve` in front)
  TSL_PORT  port (default 8787)
  TSL_DATA  path of the JSON data file (default data.json next to this script)
"""
import json
import os
import shutil
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("TSL_HOST", "127.0.0.1")
PORT = int(os.environ.get("TSL_PORT", "8787"))
DATA = os.environ.get("TSL_DATA", os.path.join(HERE, "data.json"))
MAX_BODY = 5 * 1024 * 1024
LOCK = threading.Lock()


def load():
    try:
        with open(DATA, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"logs": {}, "knee": {}}
    data.setdefault("logs", {})
    data.setdefault("knee", {})
    return data


def save(data):
    if os.path.exists(DATA):
        shutil.copyfile(DATA, DATA + ".bak")
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DATA)


def merge(server, client):
    """Per session, the newer savedAt wins. Knee test values merge per date, client wins."""
    changed = False
    for key, entry in (client.get("logs") or {}).items():
        if not isinstance(entry, dict):
            continue
        mine = server["logs"].get(key)
        if mine is None or str(entry.get("savedAt", "")) > str(mine.get("savedAt", "")):
            server["logs"][key] = entry
            changed = True
    for date, vals in (client.get("knee") or {}).items():
        if isinstance(vals, dict):
            merged = {**server["knee"].get(date, {}), **vals}
            if merged != server["knee"].get(date):
                server["knee"][date] = merged
                changed = True
    return changed


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/sync":
            with LOCK:
                return self._json(200, load())
        if path in ("/", "/index.html"):
            self.path = "/index.html"
            return super().do_GET()
        self.send_error(404)  # never serve server.py or data.json

    def do_POST(self):
        if self.path.split("?")[0] != "/api/sync":
            return self.send_error(404)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._json(413, {"error": "too large"})
        try:
            client = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json(400, {"error": "invalid JSON"})
        with LOCK:
            data = load()
            if merge(data, client):
                data["updatedAt"] = datetime.now().isoformat(timespec="seconds")
                save(data)
            return self._json(200, data)


if __name__ == "__main__":
    print(f"Trail Strength Log on http://{HOST}:{PORT}  (data: {DATA})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
