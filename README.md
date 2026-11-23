# Trail Strength Log

A training log for the Divča and Jablanik strength plan. `index.html` is the app, and `server.py` serves it and saves the log to `data.json`. The server needs only Python 3.8 or newer, with nothing to install.

## How it gets to goblin

goblin pulls this repo every 3 minutes with a read-only deploy key. When `main` has a new commit, it updates its copy and restarts the app. Nothing outside goblin can reach it: to ship a change, push to `main`.

| What | Where on goblin |
| --- | --- |
| App checkout (owned by user `apps`) | `/srv/apps/trail-strength-app` |
| Your log | `/srv/apps-data/trail-strength-app/data.json` (and `.bak`) |
| Read-only deploy key | `/var/lib/apps/.ssh/trail_deploy` |
| App service | `trail-app.service`, listening on `127.0.0.1:8787` |
| Updater | `trail-pull.timer` → `deploy/pull.sh`, then `trail-restart.path` restarts the app |

The log is outside the checkout, so a pull can never overwrite it. First-time setup is in [GOBLIN-SETUP.md](GOBLIN-SETUP.md).

Changes to the files in `deploy/` that end in `.service`, `.timer` or `.path` need `sudo sh /srv/apps/trail-strength-app/deploy/install.sh` once more on goblin. Changes to `index.html` and `server.py` go live by themselves.

## Run it locally

```sh
python3 server.py   # http://127.0.0.1:8787
```

## How syncing works

- Every save goes to this browser first, then to goblin. If goblin can't be reached, the app says so and syncs the next time you open it.
- If the same session is saved on two devices, the later save wins.
- `data.json` is your whole log, and the previous version is kept as `data.json.bak`. Back up that file. Export on the History tab gives you a copy as well.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `TSL_HOST` | `127.0.0.1` | Address to listen on |
| `TSL_PORT` | `8787` | Port |
| `TSL_DATA` | `data.json` next to `server.py` | Where the log is stored |
