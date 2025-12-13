# Minimal Dockerfile for local testing (binds to $BOOKMARKS_PORT or 5000)
FROM python:3.14-slim

# Create app user and workdir
RUN useradd --create-home --shell /bin/false appuser
WORKDIR /home/appuser/app

# Install build/runtime deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml pyproject.toml
COPY README.md README.md
COPY . /home/appuser/app

# Install app (uses pyproject) and remove build deps
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir . \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /root/.cache

# Use non-root user
USER appuser

# Expose the configured port (default 5000)
ARG BOOKMARKS_PORT=5000
ENV BOOKMARKS_PORT=${BOOKMARKS_PORT}
EXPOSE ${BOOKMARKS_PORT}

# Default command: run with Gunicorn (3 workers). The app reads BOOKMARKS_PORT.
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "3", "--log-level", "info"]
