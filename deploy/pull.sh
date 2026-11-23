#!/bin/sh
# Runs as the "apps" user from trail-pull.timer.
# Fetches the repo with the read-only deploy key and, when main has moved,
# updates the checkout and touches a stamp file. trail-restart.path watches
# that stamp and restarts trail-app.service.
set -eu

REPO=${TSL_REPO:-/srv/apps/trail-strength-app}
STAMP=${TSL_STAMP:-/var/lib/apps/trail-strength-app.deployed}
BRANCH=main

cd "$REPO"
git fetch --quiet origin "$BRANCH"

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0

# The log is stored in /srv/apps-data, outside this folder, so a hard reset
# can never touch it.
git reset --quiet --hard "origin/$BRANCH"
echo "$(date -Is) $REMOTE" > "$STAMP"
echo "Deployed $(git log -1 --format='%h %s')"
