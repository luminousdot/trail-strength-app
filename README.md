# Trail Strength Log on goblin

Two files do the work. `index.html` is the app, and `server.py` serves it and saves your log to `data.json`. The server needs only Python 3.8 or newer, with nothing to install.

## 1. Copy the files

```sh
ssh goblin 'mkdir -p ~/trail-app'
scp index.html server.py goblin:~/trail-app/
```

## 2. Try it

```sh
ssh goblin
cd ~/trail-app && python3 server.py
```

It listens on `127.0.0.1:8787`, which only goblin itself can reach. Stop it with Ctrl+C once you've seen it start.

## 3. Make it reachable on your tailnet (HTTPS)

```sh
sudo tailscale serve --bg 8787
```

Open `https://goblin.<your-tailnet>.ts.net/` on your phone, and add it to your home screen. Only devices on your tailnet can open it. The app has no login, so don't use `tailscale funnel`, which would make it public.

If you don't want `tailscale serve`, run `TSL_HOST=0.0.0.0 python3 server.py` and open `http://goblin:8787/`. Then make sure your firewall only lets the tailnet reach port 8787.

## 4. Keep it running (systemd)

Save this as `/etc/systemd/system/trail-app.service`, replacing `YOURUSER`:

```ini
[Unit]
Description=Trail Strength Log
After=network-online.target

[Service]
User=YOURUSER
WorkingDirectory=/home/YOURUSER/trail-app
ExecStart=/usr/bin/python3 /home/YOURUSER/trail-app/server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now trail-app
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
