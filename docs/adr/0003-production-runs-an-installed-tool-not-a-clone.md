# Production runs an installed tool, not a clone

Production runs the `bookmarks` uv tool, installed from a wheel built from one commit, instead of a git clone. The spec (#19, from #16) kept a pinned "deployed clone" that moves forward to `main` at cutover. At cutover the systemd unit, cron and MCP registration were pointed at the development clone instead, so every branch switch there changed what production ran (found 2026-10-17, while building #45). A clone is a working tree: it can be on any branch, dirty, or half-way through a rebase, and "deploy" and "revert" both mean editing it in place.

## Decisions

- **One install, one path.** `scripts/deploy.sh` installs the tool with `uv tool install`; the unit, cron and MCP registration all run `~/.local/bin/bookmarks`. Settings stay in `~/.config/bookmarks/env` and the store in the XDG data directory, neither inside a release.
- **Built from a commit, gated first.** Deploy checks the commit out in a temporary worktree, runs `scripts/gate.sh` there and builds only if it is green; the clone it runs from may be on any branch.
- **Pinned to the lock.** `uv tool install` resolves from the wheel's version ranges, so deploy installs with constraints exported from `uv.lock` (`uv export --frozen --no-dev`): production gets the versions the gate tested.
- **A release is a directory per commit.** `releases/<sha>/` holds the wheel, its constraints, the unit and the probe; `releases/current` names the live one. Every build is version 0.2.0, so the commit, not the version, tells releases apart, and `--reinstall` swaps them.
- **Revert reinstalls the previous release** and probes it with its own probe; it never edits a clone.
- **Code never swaps mid-drain.** Deploy holds the drain's `flock` while it installs, restarts and probes.

## Considered Options

- **Move the deployed clone forward, as the spec said** (`git pull` to deploy, `git reset` to revert). Rejected: production is still a working tree someone can edit, and revert rewrites history in it.
- **Release directories with a `current` symlink, each with its own `.venv`.** Rejected: it works, but each release carries a full environment, and an installed tool is the platform's own form of this.

## Consequences

- The deployed clone `~/bookmarks` (commit `5fddc16`) has no role; it is retired once the legacy data file is confirmed archived on the backup disk.
- Unit changes ship with the code: deploy installs the release's `deploy/bookmarks-web.service`. Cron entries and the MCP registration name only the stable path, so they are set once.
- The first deploy has no previous release: a failed probe there exits 3, and the old unit is restored by hand.
