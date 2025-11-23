#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/root/vpn-server"
DB_PATH="$PROJECT_ROOT/data/vpn.db"

if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "ERROR: sqlite3 не установлен"
    exit 1
fi

if [[ ! -f "$DB_PATH" ]]; then
    echo "ERROR: База $DB_PATH не найдена"
    exit 1
fi

echo "Проверка целостности $DB_PATH..."
RESULT=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" || true)

if [[ "$RESULT" != "ok" ]]; then
    echo "ERROR: integrity_check вернул '$RESULT'"
    exit 2
fi

echo "OK: integrity_check прошёл успешно"




