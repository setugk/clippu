#!/bin/zsh
# Mac-side Clippery backup — called by launchd daily.
# Downloads JSON export from Clippery → SeaDrive folder.
# SeaDrive syncs it to Seafile, giving an off-NAS copy.

BACKUP_DIR="$HOME/Library/CloudStorage/SeaDrive-SetuKathawate(files.setugk.com)/My Libraries/Setu's Personal Library/2. Work Related/Projects/clippery/backups"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

curl -sf --max-time 30 "http://10.0.0.10:5050/api/export" \
  -o "$BACKUP_DIR/clippery-$DATE.json"

if [ $? -eq 0 ]; then
  # Keep only the 30 most recent JSON backups
  ls -t "$BACKUP_DIR"/clippery-*.json | tail -n +31 | xargs rm -f 2>/dev/null
  echo "$(date): Backup saved to $BACKUP_DIR/clippery-$DATE.json"
else
  echo "$(date): Backup FAILED — NAS unreachable or app down" >&2
fi
