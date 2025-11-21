#!/usr/bin/env bash
set -euo pipefail

# Скрипт создаёт системного пользователя vpnapi и настраивает права
# Запускать от root: sudo ./scripts/setup_vpn_api_user.sh

VPN_ROOT="/root/vpn-server"
SERVICE_USER="vpnapi"
SERVICE_GROUP="vpnapi"

if ! getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
    echo "Создаю группу $SERVICE_GROUP..."
    groupadd --system "$SERVICE_GROUP"
fi

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    echo "Создаю системного пользователя $SERVICE_USER..."
    useradd --system --shell /usr/sbin/nologin --home "$VPN_ROOT" --gid "$SERVICE_GROUP" "$SERVICE_USER"
else
    echo "Пользователь $SERVICE_USER уже существует"
fi

chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$VPN_ROOT"
chmod -R 750 "$VPN_ROOT"
chmod 640 "$VPN_ROOT"/config/*.json || true
chmod 640 "$VPN_ROOT"/config/*.env || true

echo "Готово. Не забудьте:"
echo "1. sudo systemctl daemon-reload"
echo "2. sudo systemctl enable --now vpn-api"

