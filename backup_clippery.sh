#!/bin/sh
# Daily Clippery backup — runs as NAS cron job.
# Keeps last 30 SQLite snapshots in /volume1/backups/clippery/.

BACKUP_DIR="/volume1/backups/clippery"
DB_SRC="/volume1/docker/clipboard/data/clippery.db"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

# Copy the SQLite file with WAL checkpoint first (flushes WAL → main DB)
sqlite3 "$DB_SRC" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
cp "$DB_SRC" "$BACKUP_DIR/clippery-$DATE.db"

# Keep only the 30 most recent backups
ls -t "$BACKUP_DIR"/clippery-*.db | tail -n +31 | xargs rm -f 2>/dev/null || true

echo "Backup done: $BACKUP_DIR/clippery-$DATE.db"
