#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/root/vpn-server/config/backups"
DAYS_TO_KEEP="${DAYS_TO_KEEP:-7}"
BACKUP_PATTERN="${BACKUP_PATTERN:-vpn-backup-*.tgz}"
LOG_FILE="/root/vpn-server/logs/backup_cleanup.log"

mkdir -p "$BACKUP_DIR"
touch "$LOG_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Начинаю очистку: папка=$BACKUP_DIR, сохраняем $DAYS_TO_KEEP дней"

BEFORE_COUNT=$(find "$BACKUP_DIR" -type f -name "$BACKUP_PATTERN" | wc -l | tr -d ' ')

find "$BACKUP_DIR" -type f -name "$BACKUP_PATTERN" -mtime +"$DAYS_TO_KEEP" -delete

AFTER_COUNT=$(find "$BACKUP_DIR" -type f -name "$BACKUP_PATTERN" | wc -l | tr -d ' ')
DELETED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

log "Удалено $DELETED_COUNT архивов, осталось $AFTER_COUNT"
DU_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "Текущий размер каталога: ${DU_SIZE:-0}"

exit 0



