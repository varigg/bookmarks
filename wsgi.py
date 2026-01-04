import shutil
from datetime import datetime
from pathlib import Path

from bookmarks import create_app
from bookmarks.config import BACKUP_COUNT, BACKUP_DIR, BACKUP_ENABLED, DATA_SOURCE


def backup_data_file():
    """Create a timestamped backup of the data file and rotate old backups."""
    if not BACKUP_ENABLED:
        return

    # Paths are already resolved by config.py
    src = Path(DATA_SOURCE)
    backup_dir = Path(BACKUP_DIR)

    if not src.exists():
        print(f"Warning: Data file {src} does not exist, skipping backup")
        return

    # Create backup directory
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{src.stem}_{timestamp}{src.suffix}.bck"
    dst = backup_dir / backup_name

    try:
        shutil.copy2(src, dst)
        print(f"Backup created: {dst}")
    except Exception as e:
        print(f"Warning: Could not back up {src}: {e}")
        return

    # Rotate old backups - keep only the most recent BACKUP_COUNT files
    if BACKUP_COUNT > 0:
        backup_pattern = f"{src.stem}_*{src.suffix}.bck"
        backups = sorted(
            backup_dir.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Remove old backups beyond the limit
        for old_backup in backups[BACKUP_COUNT:]:
            try:
                old_backup.unlink()
                print(f"Removed old backup: {old_backup}")
            except Exception as e:
                print(f"Warning: Could not remove old backup {old_backup}: {e}")


# Backup bookmarks file at startup
backup_data_file()

app = create_app()
