#!/bin/bash
# Скрипт для очистки старых бэкапов конфигурации

BACKUP_DIR="/root/vpn-server/config/backups"
DAYS_TO_KEEP=30

echo "[$(date)] Starting backup cleanup..."
echo "Backup directory: $BACKUP_DIR"
echo "Keeping backups older than $DAYS_TO_KEEP days"

# Считаем количество файлов до очистки
BEFORE_COUNT=$(find "$BACKUP_DIR" -type f -name "config_backup_*.json" | wc -l)

# Удаляем файлы старше указанного количества дней
find "$BACKUP_DIR" -type f -name "config_backup_*.json" -mtime +$DAYS_TO_KEEP -delete

# Считаем количество файлов после очистки
AFTER_COUNT=$(find "$BACKUP_DIR" -type f -name "config_backup_*.json" | wc -l)

DELETED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

echo "[$(date)] Cleanup completed. Deleted $DELETED_COUNT files."
echo "Remaining backups: $AFTER_COUNT"

# Показываем размер директории после очистки
DU_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo "Backup directory size: $DU_SIZE"

exit 0




