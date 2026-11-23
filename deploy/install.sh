#!/bin/sh
# One-time install on goblin. Run with sudo after cloning:
#   sudo sh /srv/apps/trail-strength-app/deploy/install.sh [path/to/old/data.json]
# Safe to run again; it never overwrites an existing log.
set -eu

REPO=/srv/apps/trail-strength-app
DATA_DIR=/srv/apps-data/trail-strength-app
OLD_DATA=${1:-}

install -d -o apps -g apps -m 750 "$DATA_DIR"
install -d -o apps -g apps -m 750 /var/lib/apps

if [ -n "$OLD_DATA" ]; then
  if [ -e "$DATA_DIR/data.json" ]; then
    echo "Keeping existing $DATA_DIR/data.json, not copying $OLD_DATA"
  else
    install -o apps -g apps -m 640 "$OLD_DATA" "$DATA_DIR/data.json"
    echo "Copied your log from $OLD_DATA"
  fi
fi

touch /var/lib/apps/trail-strength-app.deployed
chown apps:apps /var/lib/apps/trail-strength-app.deployed

for u in trail-app.service trail-pull.service trail-pull.timer trail-restart.path trail-restart.service; do
  install -m 644 "$REPO/deploy/$u" /etc/systemd/system/$u
done

systemctl daemon-reload
systemctl enable --now trail-app.service trail-restart.path trail-pull.timer
systemctl restart trail-app.service
systemctl --no-pager --lines=0 status trail-app.service trail-pull.timer
