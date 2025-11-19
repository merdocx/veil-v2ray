#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/root/vpn-server"
BACKUP_DIR="$PROJECT_ROOT/config/backups"
LOG_FILE="/var/log/vpn-backup.log"

mkdir -p "$BACKUP_DIR"
touch "$LOG_FILE"

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log() {
    echo "$(timestamp) $1" | tee -a "$LOG_FILE"
}

ARCHIVE_NAME="vpn-backup-$(date +%Y%m%d_%H%M%S).tgz"
ARCHIVE_PATH="$BACKUP_DIR/$ARCHIVE_NAME"

cd "$PROJECT_ROOT"

log "Создание локального архива $ARCHIVE_PATH"

declare -a INCLUDE_PATHS=(
    "config/keys.json"
    "config/ports.json"
    "config/traffic_history.json"
    "config/keys.env"
    ".env"
    "systemd/xray.service"
    "systemd/vpn-api.service"
    "update_xray.sh"
    "sync_inbounds.py"
    "nginx"
)

declare -a EXISTING_PATHS=()
for path in "${INCLUDE_PATHS[@]}"; do
    if [[ -e "$path" ]]; then
        EXISTING_PATHS+=("$path")
    else
        log "WARN: файл/каталог $path не найден, пропускаю"
    fi
done

if [[ ${#EXISTING_PATHS[@]} -eq 0 ]]; then
    log "ERROR: Нет файлов для архивации."
    exit 1
fi

tar czf "$ARCHIVE_PATH" "${EXISTING_PATHS[@]}"

log "Архив создан: $ARCHIVE_PATH"

# Опциональная выгрузка в S3
if [[ -n "${S3_BUCKET:-}" ]] && command -v aws >/dev/null 2>&1; then
    S3_URI="s3://${S3_BUCKET%/}/$ARCHIVE_NAME"
    log "Выгрузка архива в S3: $S3_URI"
    aws s3 cp "$ARCHIVE_PATH" "$S3_URI" --sse AES256 && log "S3 выгрузка завершена"
fi

# Опциональная выгрузка через rsync/scp
if [[ -n "${REMOTE_BACKUP_TARGET:-}" ]]; then
    log "Передача архива на удалённый хост: $REMOTE_BACKUP_TARGET"
    rsync -av "$ARCHIVE_PATH" "$REMOTE_BACKUP_TARGET" && log "Удалённый backup завершён"
fi

log "Резервное копирование завершено"


