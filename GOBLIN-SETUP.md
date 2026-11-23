# Set up goblin (one time)

Run these on goblin, in a terminal. Each block can be pasted as is. It takes about 5 minutes.

## 1. Create the `apps` user

This user owns the app and its log. It can't log in and has no `sudo`.

```sh
sudo useradd --system --create-home --home-dir /var/lib/apps --shell /usr/sbin/nologin apps
sudo mkdir -p /srv/apps
sudo chown apps:apps /srv/apps
```

## 2. Make the read-only deploy key

```sh
sudo -u apps mkdir -p -m 700 /var/lib/apps/.ssh
sudo -u apps ssh-keygen -t ed25519 -N "" -C "goblin trail-strength-app" -f /var/lib/apps/.ssh/trail_deploy
sudo cat /var/lib/apps/.ssh/trail_deploy.pub
```

Copy the line that starts with `ssh-ed25519`.

## 3. Add the key to the repo on GitHub

Open https://github.com/luminousdot/trail-strength-app/settings/keys/new

- Title: `goblin`
- Key: paste the line from step 2
- Leave **Allow write access** unticked

Click **Add key**.

## 4. Clone the repo

```sh
sudo -u apps git -c core.sshCommand="ssh -i /var/lib/apps/.ssh/trail_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
  clone git@github.com:luminousdot/trail-strength-app.git /srv/apps/trail-strength-app
sudo -u apps git -C /srv/apps/trail-strength-app config core.sshCommand \
  "ssh -i /var/lib/apps/.ssh/trail_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
```

## 5. Install the services

If you already ran the app from `~/trail-app` and logged sessions, pass your old log so it's carried over:

```sh
sudo sh /srv/apps/trail-strength-app/deploy/install.sh ~/trail-app/data.json
```

If you haven't logged anything yet, leave the path off:

```sh
sudo sh /srv/apps/trail-strength-app/deploy/install.sh
```

This replaces any earlier `trail-app.service`, so the old copy in `~/trail-app` is no longer used. You can delete that folder once you've checked your log is in the app.

## 6. Reach it from your phone

If you set up `tailscale serve` before, it already points at port 8787 and nothing changes. Otherwise:

```sh
sudo tailscale serve --bg 8787
```

Open `https://goblin.<your-tailnet>.ts.net/`. Don't use `tailscale funnel`, because the app has no login.

## Check that it works

```sh
systemctl status trail-app trail-pull.timer
journalctl -u trail-pull -n 20      # "Deployed ..." appears after each new version
sudo -u apps /srv/apps/trail-strength-app/deploy/pull.sh   # pull right now instead of waiting
```

## If something goes wrong

- `Permission denied (publickey)` in `journalctl -u trail-pull`: the deploy key from step 3 is missing on GitHub.
- The app is down: `journalctl -u trail-app -n 50`.
- Stop automatic updates: `sudo systemctl disable --now trail-pull.timer`.
- Go back one version: `sudo -u apps git -C /srv/apps/trail-strength-app reset --hard HEAD~1 && sudo systemctl restart trail-app`, and disable the timer, or the next pull brings the new version back.
