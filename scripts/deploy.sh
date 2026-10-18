#!/usr/bin/env bash
# Deploy one commit as the `bookmarks` uv tool, reverting on a failed probe
# (ADR 0003). Run on thunderbird from any clone:
#
#   scripts/deploy.sh [ref]        default: origin/main
#
# 1. Gate the commit in a clean temporary worktree; anything but green stops.
# 2. Build its wheel, lock-pinned constraints, unit and probe into releases/<sha>.
# 3. Holding the drain's lock, so code never swaps mid-drain: install the tool,
#    install the unit, restart the web server, probe web and MCP.
# 4. On a failed probe, activate the previous release the same way.
#
# Exit 0 deployed; 1 refused, production untouched; 2 probe failed and the
# previous release is live again; 3 probe failed and no probed release is live.
set -euo pipefail

repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
releases=${XDG_DATA_HOME:-$HOME/.local/share}/bookmarks/releases
config=${XDG_CONFIG_HOME:-$HOME/.config}
bin=$(uv tool dir --bin)/bookmarks
python=$(uv tool dir)/bookmarks/bin/python
lock=/tmp/bookmarks-drain.lock # the cron drain's lock (deploy/crontab)

git -C "$repo" fetch -q origin
sha=$(git -C "$repo" rev-parse --verify "${1:-origin/main}^{commit}")
build=$(mktemp -d)
trap 'git -C "$repo" worktree remove --force "$build/src" 2>/dev/null; rm -rf "$build"' EXIT

git -C "$repo" worktree add -q --detach "$build/src" "$sha"
if ! "$build/src/scripts/gate.sh"; then
  echo "deploy: gate not green for $sha; production untouched" >&2
  exit 1
fi

# ponytail: releases are never pruned; each is ~200 KB. Prune if the list grows.
rel=$releases/$sha
rm -rf "$rel" && mkdir -p "$rel"
uv build -q --wheel --out-dir "$rel" "$build/src"
uv --directory "$build/src" export -q --frozen --no-dev --no-hashes \
  --no-emit-project -o "$rel/constraints.txt"
cp "$build/src/deploy/bookmarks-web.service" "$build/src/scripts/probe.py" "$rel/"
previous=$(cat "$releases/current" 2>/dev/null || true)

activate() { # <release-dir>; && throughout: set -e is off inside an `if`
  uv tool install -q --reinstall -c "$1/constraints.txt" "$1"/*.whl &&
    install -Dm644 "$1/bookmarks-web.service" "$config/systemd/user/bookmarks-web.service" &&
    systemctl --user daemon-reload &&
    systemctl --user restart bookmarks-web &&
    (set -a && source "$config/bookmarks/env" && set +a && "$python" "$1/probe.py" "$bin")
}

exec 9>"$lock"
if ! flock -w 900 9; then
  echo "deploy: the drain held its lock for 15 minutes; production untouched" >&2
  exit 1
fi

if activate "$rel"; then
  echo "$sha" >"$releases/current"
  echo "deploy: $sha is live"
  exit 0
fi
echo "deploy: probe failed for $sha" >&2
if [[ -n $previous && -d $releases/$previous ]] && activate "$releases/$previous"; then
  echo "deploy: reverted; $previous is live" >&2
  exit 2
fi
echo "deploy: no probed release is live${previous:+ (revert to $previous failed)}" >&2
exit 3
