#!/bin/bash
# Скрипт для автозапуска Xray при загрузке системы
# Используется как fallback если systemd unit не работает

XRAY_BIN="/usr/local/bin/xray"
CONFIG_FILE="/root/vpn-server/config/config.json"
PIDFILE="/var/run/xray.pid"

# Проверяем, не запущен ли уже Xray
if pgrep -f "xray.*config.json" > /dev/null; then
    echo "Xray already running"
    exit 0
fi

# Запускаем Xray в фоне
nohup "$XRAY_BIN" run -config "$CONFIG_FILE" > /dev/null 2>&1 &

# Сохраняем PID
echo $! > "$PIDFILE"

echo "Xray started with PID $(cat $PIDFILE)"



