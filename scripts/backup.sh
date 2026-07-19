#!/usr/bin/env bash
set -euo pipefail

# Ghost AutoVacancy Poster — Database Backup Script
# Usage: ./scripts/backup.sh [backup-dir]

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_PATH="$(dirname "$0")/../ghost_vacancies.db"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_DIR/ghost_vacancies_$TIMESTAMP.db"
    gzip "$BACKUP_DIR/ghost_vacancies_$TIMESTAMP.db"
    echo "[OK] Backup created: $BACKUP_DIR/ghost_vacancies_$TIMESTAMP.db.gz"
else
    echo "[WARN] Database not found at $DB_PATH"
fi

# Clean old backups
find "$BACKUP_DIR" -name "ghost_vacancies_*.db.gz" -mtime +$RETENTION_DAYS -delete
echo "[OK] Removed backups older than $RETENTION_DAYS days"
