#!/usr/bin/env bash
set -euo pipefail

# Build a wheel using the project's `uv` wrapper.
# Usage: ./scripts/build_wheel_uv.sh

echo "Building wheel with uv..."
uv build

echo "Built:"
ls -1 dist/*.whl
