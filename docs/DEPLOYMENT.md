# Deployment Guide

This document describes several ways to distribute and run the Bookmarks application on a Linux server. It covers quick single-file deployments (wheel and zipapp), a traditional systemd + virtualenv approach, and the Docker approach (recommended for portability).

Pick the approach that best fits your environment and comfort level.

---

## Quick choices (summary)

- Use a **wheel**: build a wheel locally, copy the wheel to the server, install into a virtualenv, and run with Gunicorn (recommended minimal-effort approach).
- Use a **zipapp**: create a single `.pyz` file that bundles your app and vendored dependencies (useful when you want one file, but harder to maintain).
- Use **systemd + virtualenv**: native, lightweight, suitable for long-running service on a dedicated server.
- Use **Docker**: best for reproducibility and portability (single artifact, easy upgrades, use named volumes for persistent data).
- Use **Makefile targets**: `make service-install` provides a guided setup and automated deployment.

---

## A. Build a wheel and deploy (recommended minimal-effort)

This is the simplest reliable approach if you want to copy a single file to the server and have the server install dependencies.

1. On your development machine, build the wheel:

```bash
# from the project root
python -m pip install --upgrade build
python -m build
# result will be in dist/, e.g. dist/bookmarks-0.1.0-py3-none-any.whl
```

2. Copy the wheel to the server (scp or rsync):

```bash
scp dist/bookmarks-*.whl user@server:/tmp/
```

3. On the server, create a virtualenv and install the wheel:

```bash
ssh user@server
# create venv and activate
python3 -m venv /opt/bookmarks/venv
source /opt/bookmarks/venv/bin/activate
# install the wheel (this installs dependencies too)
pip install /tmp/bookmarks-*.whl
```

4. Run with Gunicorn (recommended for production):

```bash
# inside the venv
/opt/bookmarks/venv/bin/gunicorn 'wsgi:app' --bind 0.0.0.0:5000 --workers 3
```

**Important**: Use `--bind 0.0.0.0:5000` to accept connections from any network interface. If you use `--bind 127.0.0.1:5000` or omit the bind address, the app will only be accessible from localhost and not from other machines on your network.

For development with Flask:

```bash
# Flask development server (accessible from network)
uv run flask --app wsgi run --host 0.0.0.0 --port 5000 --debug
```

5. Optional: create a `systemd` unit (see section C below) to run as a service.

Notes:

- The wheel approach installs dependencies on the server via pip, so the server needs network access to pip indexes (or you can vendor wheels).
- Use `BOOKMARKS_PORT`, `BOOKMARKS_DATA_SOURCE`, and other env vars to configure the app. Example:

```bash
export BOOKMARKS_PORT=5000
export BOOKMARKS_DATA_SOURCE=/var/lib/bookmarks/bookmarks.js
export BOOKMARKS_BACKUP_DIR=/var/lib/bookmarks/backup
```

---

## B. Single-file zipapp (one `.pyz` to copy)

This creates an executable zip archive (`.pyz`) containing your app and (optionally) vendored dependencies. It's convenient as a single file you can copy and run, but bundling dependencies is the tricky part.

1. Prepare a clean build directory and vendor dependencies (on a machine with the same platform as the server):

```bash
mkdir -p build/app
# copy your package sources into build/app (preserve package name and wsgi.py)
cp -r bookmarks build/app/
cp wsgi.py build/app/

# vendor dependencies (install into build/vendor)
python -m venv .build-venv
source .build-venv/bin/activate
pip install --upgrade pip
pip install --target build/vendor -r requirements.txt
deactivate
```

2. Create a `__main__.py` at `build/__main__.py` that sets up `sys.path` so the vendored packages and your app package are importable, then starts the app (note: for production you'd usually run Gunicorn outside the zipapp, but for a simple single-file runner you can call `app.run()`):

```python
# build/__main__.py
import sys
from pathlib import Path
base = Path(__file__).parent
sys.path.insert(0, str(base / 'vendor'))
sys.path.insert(0, str(base / 'app'))

from wsgi import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

3. Create the zipapp:

```bash
python -m zipapp -o bookmarks.pyz -m '__main__:main' build
# or if your __main__ logic runs on import, just
python -m zipapp -o bookmarks.pyz build
```

4. Copy `bookmarks.pyz` to the server and run:

```bash
scp bookmarks.pyz user@server:/opt/bookmarks/
ssh user@server
python3 /opt/bookmarks/bookmarks.pyz
```

Caveats:

- You must vendor platform-specific binary dependencies on a matching platform.
- Keeping the zipapp updated with security fixes is manual.
- For most deployments, the wheel + venv approach is easier.

---

## C. systemd + virtualenv (native service)

This is a standard approach for a Linux server where you want the app to run as a service without containers.

1. Create a system user and directories:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin bookmarks
sudo mkdir -p /var/lib/bookmarks /opt/bookmarks/current
sudo chown -R bookmarks:bookmarks /var/lib/bookmarks /opt/bookmarks
```

2. Create a virtualenv and install the app (example uses wheel copied earlier):

```bash
python3 -m venv /opt/bookmarks/venv
source /opt/bookmarks/venv/bin/activate
pip install /tmp/bookmarks-*.whl
deactivate
```

3. Create an environment file `/etc/default/bookmarks` or `/etc/bookmarks.env`:

```
BOOKMARKS_PORT=5000
BOOKMARKS_DATA_SOURCE=/var/lib/bookmarks/bookmarks.js
BOOKMARKS_BACKUP_DIR=/var/lib/bookmarks/backup
```

4. Create a `systemd` unit at `/etc/systemd/system/bookmarks.service`:

```ini
[Unit]
Description=Bookmarks Flask app
After=network.target

[Service]
Type=simple
User=bookmarks
Group=bookmarks
WorkingDirectory=/opt/bookmarks/current
EnvironmentFile=/etc/default/bookmarks
ExecStart=/opt/bookmarks/venv/bin/gunicorn 'wsgi:app' --bind 0.0.0.0:${BOOKMARKS_PORT} --workers 3
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

5. Start and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bookmarks
sudo journalctl -u bookmarks -f
```

Notes:

- Use the `BOOKMARKS_*` environment variables to configure data file paths, backup directory, and port.
- Ensure the `bookmarks` user has read/write access to the `bookmarks.js` file and backup dir.

---

## D. Docker (portable and recommended for reproducibility)

If you prefer the one-step, reproducible experience, Docker is the recommended path for self-hosting. A minimal `Dockerfile` and `docker-compose.yml` were added to the project root.

### Build and run locally

```bash
# build locally
docker build -t bookmarks:local .

# run (maps host 5000 to container 5000)
docker run -d --name bookmarks -p 5000:5000 -v "$(pwd)/data:/data" \
  -e BOOKMARKS_PORT=5000 -e BOOKMARKS_DATA_SOURCE=/data/bookmarks.js bookmarks:local

# or use the guided installation (recommended)
make service-install
```

### Guided Installation (`make service-install`)

The project includes an interactive configuration wizard and a one-command installation target:

1.  **Configure**: Run `make configure` (or let `service-install` call it for you) to generate a `.env` file with a secret key and your LLM API keys.
2.  **Install**: Run `make service-install`. This will:
    -   Run the configuration wizard if `.env` is missing.
    -   Build the Docker image.
    -   Start the containerized service with a **named volume** for persistent data.

This approach ensures a standard, repeatable setup with minimal manual steps.

### Notes about volumes and persistence

-   **Named Volumes (Recommended)**: By default, `docker-compose.yml` uses a named volume `bookmarks_data`. This is more robust than bind mounts for production as it avoids host permission issues.
-   **Data Location**: The service maps the volume to `/data` inside the container. Your `bookmarks.js` and `backup/` directory will persist here even if the container is removed.

### Development vs production

- For production, run Gunicorn behind an nginx reverse proxy or use a managed TLS terminator like Caddy.

---

## E. Reverse proxy and TLS

For any public or local-network deployment you'll usually run a reverse proxy (nginx or Caddy) to terminate TLS and forward requests to the app:

Example minimal `nginx` config (proxy to localhost 5000):

```nginx
server {
    listen 80;
    server_name bookmarks.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name bookmarks.example.com;

    ssl_certificate /etc/letsencrypt/live/bookmarks.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bookmarks.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Use Certbot (nginx plugin) or Caddy for automatic TLS management.

---

## F. Security and operational notes

- If you keep the server local only, prefer binding to `0.0.0.0` and using firewall rules to restrict external access, or bind to a loopback/host-only interface and rely on reverse proxy.
- Use HTTPS for any public deployment. Consider an API key or authentication if exposing publicly.
- Keep backups: the app creates a startup backup, but consider periodic backups via cron or host snapshots.
- Monitor logs with `journalctl` (systemd) or container logs (`docker logs -f bookmarks`).

---

## G. Quick helper script ideas (optional)

You can automate the wheel build + deploy with two scripts (not provided here by default):

`build_wheel.sh` (local):

```bash
#!/usr/bin/env bash
python -m pip install --upgrade build
python -m build
```

`deploy_wheel.sh` (remote):

```bash
#!/usr/bin/env bash
WHEEL=$(ls dist/bookmarks-*.whl | tail -n 1)
scp "$WHEEL" user@server:/tmp/
ssh user@server bash -s <<'SSH'
python3 -m venv /opt/bookmarks/venv || true
source /opt/bookmarks/venv/bin/activate
pip install --upgrade pip
pip install /tmp/$(basename "$WHEEL")
# restart systemd if you have a unit
sudo systemctl restart bookmarks || true
SSH
```

---

## H. Which to choose?

- Quick personal server: **wheel + virtualenv + systemd** — small, easy, no Docker required.
- Portable reproducible deployment: **Docker** — easiest to run the same image everywhere.
- Single-file distribution (special cases): **zipapp**, only if you want one file and can vendor dependencies reliably.

If you'd like, I can:

- Add the example `systemd` unit and environment file to the repo (as templates),
- Add `build_wheel.sh` and `deploy_wheel.sh` helper scripts, or
- Update the `Dockerfile` `CMD` to read `BOOKMARKS_PORT` dynamically.

Tell me which of those you want next and I'll add it to the repo.

## Using the `uv` wrapper (optional)

If you use the project's `uv` wrapper locally you can run the same commands shown here prefixed with `uv run`. Below are quick examples and two helper scripts included in `scripts/` that automate the most common tasks.

Build wheel locally with `uv`:

```bash
uv build
# wheel will be in dist/
ls -l dist/*.whl
```

Copy and install the wheel on the server (simple manual flow):

```bash
scp dist/bookmarks-*.whl user@server:/tmp/
ssh user@server
# create venv (first time)
python3 -m venv /opt/bookmarks/venv
source /opt/bookmarks/venv/bin/activate
/opt/bookmarks/venv/bin/pip install --upgrade pip
/opt/bookmarks/venv/bin/pip install /tmp/bookmarks-*.whl
```

Run the server (development):

```bash
uv run flask --app wsgi run --host=0.0.0.0 --port=5000
```

Run the server (production with Gunicorn):

```bash
uv run gunicorn 'wsgi:app' --bind 0.0.0.0:5000 --workers 3
```

Helper scripts

Two small helper scripts are provided in `scripts/`:

- `scripts/build_wheel_uv.sh` — builds the wheel locally using `uv`.
- `scripts/deploy_wheel_uv.sh` — copies the wheel to the server and installs it into a venv, then optionally restarts a `systemd` unit named `bookmarks`.

Make the scripts executable before use:

```bash
chmod +x scripts/build_wheel_uv.sh scripts/deploy_wheel_uv.sh
```

These scripts are intentionally small and opinionated; edit them to match your usernames, server hostnames, or paths before using in production.
