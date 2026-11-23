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
import re
from datetime import date, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("TSL_HOST", "127.0.0.1")
PORT = int(os.environ.get("TSL_PORT", "8787"))
DATA = os.environ.get("TSL_DATA", os.path.join(HERE, "data.json"))
MAX_BODY = 5 * 1024 * 1024
LOCK = threading.Lock()

# For /api/summary (goblin's home page). Keep in step with START and RACES in index.html.
START = date(2026, 11, 23)
WEEKS = 22
RACES = [
    {"name": "Divča Winter Trail", "date": "2027-03-07", "spec": "15 km · 640 m+"},
    {"name": "Jablanik Trail", "date": "2027-04-25", "spec": "34 km · 1800 m+"},
]
SESSION_KEY = re.compile(r"^(\d{4}-\d\d-\d\d)_(A|B|P\d|SS|ME|W\d+)$")


def session_name(sid):
    if sid.startswith("P"):
        return "Precision circuit"
    if sid == "SS":
        return "Simple & Sinister"
    if sid == "ME":
        return "Uphill strength"
    if sid in ("W13", "W14"):
        return "Power workout"
    if sid.startswith("W"):
        return "Performance workout"
    return "Strength session"


# Mirrors PHASES, ME_SESSION and autoSession() in index.html. Keep them in step.
PHASE_KIND = {}
for first, last, kind in [(1, 3, "build"), (4, 4, "rec"), (5, 7, "build"), (8, 8, "rec"), (9, 11, "build"),
                          (12, 12, "rec"), (13, 14, "build"), (15, 15, "race"), (16, 16, "rec"),
                          (17, 19, "power"), (20, 20, "rec"), (21, 21, "power"), (22, 22, "race")]:
    for w in range(first, last + 1):
        PHASE_KIND[w] = kind
HALF_WEEKS = {21, 22}
ME_WEEKS = {5, 6, 7, 9, 10, 11, 13, 14}
RACE_DAYS = {r["date"] for r in RACES}


def planned_session(day):
    """The strength session the app plans for a day, or None (same rules as autoSession in index.html)."""
    w = (day - START).days // 7 + 1
    kind = PHASE_KIND.get(w)
    if not kind:
        return None
    dow = day.isoweekday()  # Mon 1 .. Sun 7
    if dow == 1:
        if kind == "race" and w in HALF_WEEKS:
            return "W13"
        return "P%d" % ((w - 1) % 3 + 1)
    if dow == 3:
        if kind in ("build", "rec"):
            return "SS"
        if kind == "power":
            return {17: "W13", 18: "W14", 19: "W13", 21: "W14"}.get(w, "W13")
        return None
    if dow == 6 and w in ME_WEEKS:
        return "ME"
    if dow == 6 and kind in ("build", "power"):
        return "SS"
    return None


def short_name(sid):
    return {"Precision circuit": "Precision", "Simple & Sinister": "S&S", "Uphill strength": "Uphill",
            "Power workout": "Power", "Performance workout": "Strength"}.get(session_name(sid), "Strength")


def day_card(day, logged):
    """One day of the week strip: what's planned and whether a session was logged."""
    sid = planned_session(day)
    w = (day - START).days // 7 + 1
    dow = day.isoweekday()
    if day.isoformat() in RACE_DAYS:
        kind, label = "race", "Race"
    elif sid:
        kind, label = "strength", short_name(sid)
    elif dow == 2:
        kind, label = "run", "Hills + speed" if 1 <= w <= 14 else "Speed"
    elif dow == 5:
        kind, label = "run", "Speed"
    elif dow == 7:
        kind, label = "run", "Long run"
    else:
        kind, label = "rest", "Rest"
    done = logged.get(day.isoformat())
    if done and kind == "rest":
        kind, label = "strength", short_name(done[0])
    return {"date": day.isoformat(), "kind": kind, "label": label, "done": bool(done)}


def summary(data, today=None):
    """Counts only, no notes or weights: safe to show on goblin's home page."""
    today = today or date.today()
    week = (today - START).days // 7 + 1
    week_start = START.toordinal() + (week - 1) * 7
    total = sets = this_week = 0
    last = None
    logged = {}  # date -> session ids
    for key, entry in data["logs"].items():
        m = SESSION_KEY.match(key)
        if not m or not isinstance(entry, dict):
            continue
        day = date.fromisoformat(m.group(1))
        logged.setdefault(day.isoformat(), []).append(m.group(2))
        total += 1
        sets += sum(sum(1 for d in (e.get("done") or []) if d)
                    for e in (entry.get("ex") or {}).values() if isinstance(e, dict))
        if week_start <= day.toordinal() < week_start + 7:
            this_week += 1
        if last is None or day.isoformat() > last["date"]:
            last = {"date": day.isoformat(), "name": session_name(m.group(2))}
    monday = date.fromordinal(today.toordinal() - today.weekday())
    week_days = [day_card(date.fromordinal(monday.toordinal() + i), logged) for i in range(7)]
    weeks = []
    for w in range(1, WEEKS + 1):
        first = START.toordinal() + (w - 1) * 7
        days = [date.fromordinal(first + i) for i in range(7)]
        weeks.append({
            "week": w,
            "kind": PHASE_KIND[w],
            "planned": sum(1 for d in days if planned_session(d)),
            "done": sum(len(logged.get(d.isoformat(), [])) for d in days),
        })
    return {
        "today": today.isoformat(),
        "weekDays": week_days,
        "weekly": weeks,
        "week": week if 1 <= week <= WEEKS else None,
        "weeks": WEEKS,
        "races": RACES,
        "sessions": total,
        "sessionsThisWeek": this_week,
        "sets": sets,
        "last": last,
    }


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

    def _json(self, code, obj, cors=False):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Always revalidate the page, so a phone never keeps showing an old version of the app.
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/sync":
            with LOCK:
                return self._json(200, load())
        if path == "/api/summary":
            with LOCK:
                return self._json(200, summary(load()), cors=True)
        if path in ("/", "/index.html"):
            self.path = "/index.html"
            return super().do_GET()
        self.send_error(404)  # never serve server.py or data.json

    def do_HEAD(self):
        if self.path.split("?")[0] in ("/", "/index.html"):
            self.path = "/index.html"
            return super().do_HEAD()
        self.send_error(404)

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
