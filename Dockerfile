# Minimal Dockerfile for local testing
FROM python:3.12-slim

# Create app user and workdir
RUN useradd --create-home --shell /bin/false appuser
WORKDIR /home/appuser/app

# Install build/runtime deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel (stable layer, rarely changes)
RUN pip install --upgrade pip setuptools wheel

# Copy dependency files only (for better layer caching)
COPY pyproject.toml README.md ./

# Install dependencies (rebuilds only when pyproject.toml or README.md changes)
RUN pip install --no-cache-dir . \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /root/.cache

# Copy application code
COPY . .

# Use non-root user
USER appuser

# Expose the configured port (default 5000)
ENV BOOKMARKS_PORT=5000
EXPOSE ${BOOKMARKS_PORT}

# Default command: run with Gunicorn.
# Using 'sh -c' to expand the environment variable in the command.
CMD ["sh", "-c", "gunicorn wsgi:app --bind 0.0.0.0:${BOOKMARKS_PORT} --workers 3 --log-level info"]
