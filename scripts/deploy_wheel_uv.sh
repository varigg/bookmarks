#!/usr/bin/env bash
set -euo pipefail

# Deploy the most recent wheel to a remote server and install it into a venv.
# Edit SERVER, VENV_DIR and SERVICE_NAME to match your environment.

SERVER="user@server"
VENV_DIR="/opt/bookmarks/venv"
SERVICE_NAME="bookmarks"

WHEEL=$(ls -1 dist/bookmarks-*.whl | tail -n1)
if [ -z "$WHEEL" ]; then
  echo "No wheel found in dist/; build first (./scripts/build_wheel_uv.sh)" >&2
  exit 1
fi

REMOTE_TMP="/tmp/$(basename "$WHEEL")"

echo "Copying $WHEEL to $SERVER:$REMOTE_TMP"
scp "$WHEEL" "$SERVER:$REMOTE_TMP"

echo "Installing on remote server..."
ssh "$SERVER" bash -s <<EOF
set -euo pipefail
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install "$REMOTE_TMP"
sudo systemctl restart "$SERVICE_NAME" || true
EOF

echo "Deployed and (attempted) restarted service: $SERVICE_NAME"
