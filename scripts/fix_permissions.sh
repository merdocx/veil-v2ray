#!/bin/bash
# Скрипт для исправления прав доступа VPN сервера
# Использование: sudo ./scripts/fix_permissions.sh

set -e

VPN_DIR="/root/vpn-server"

echo "=== Исправление прав доступа ==="

# 1. logs/ - должен быть root:vpnapi (Xray работает от root, API от vpnapi)
echo "1. Установка прав на logs/..."
chown root:vpnapi "$VPN_DIR/logs/"
chmod 775 "$VPN_DIR/logs/"
# Создаем api.log для API логов
touch "$VPN_DIR/logs/api.log" 2>/dev/null || true
# Xray логи (error.log) остаются root:root
chown root:root "$VPN_DIR/logs/error.log" 2>/dev/null || true
chmod 644 "$VPN_DIR/logs/error.log" 2>/dev/null || true
# Логи API должны быть доступны для записи vpnapi
chown vpnapi:vpnapi "$VPN_DIR/logs/api.log" 2>/dev/null || true
chmod 664 "$VPN_DIR/logs/api.log" 2>/dev/null || true
# Остальные логи - vpnapi:vpnapi (кроме error.log)
for logfile in "$VPN_DIR/logs"/*.log; do
    if [ -f "$logfile" ] && [ "$(basename "$logfile")" != "error.log" ]; then
        chown vpnapi:vpnapi "$logfile" 2>/dev/null || true
        chmod 664 "$logfile" 2>/dev/null || true
    fi
done

# 2. config/config.json - должен быть root:vpnapi с g+w
echo "2. Установка прав на config/config.json..."
chown root:vpnapi "$VPN_DIR/config/config.json"
chmod 664 "$VPN_DIR/config/config.json"

# 3. config/ - должна быть группа vpnapi с правами на запись
echo "3. Установка прав на config/..."
chown root:vpnapi "$VPN_DIR/config/"
chmod 775 "$VPN_DIR/config/"

# 4. config/backups/ - должна быть группа vpnapi с правами на запись
echo "4. Установка прав на config/backups/..."
mkdir -p "$VPN_DIR/config/backups/"
chown root:vpnapi "$VPN_DIR/config/backups/"
chmod 775 "$VPN_DIR/config/backups/"

# 4.1. config/keys.env - должен быть доступен для чтения vpnapi
echo "4.1. Установка прав на config/keys.env..."
if [ -f "$VPN_DIR/config/keys.env" ]; then
    chown root:vpnapi "$VPN_DIR/config/keys.env"
    chmod 640 "$VPN_DIR/config/keys.env"  # Чтение для группы, запись только для root
fi

# 5. data/vpn.db - должен быть доступен для записи vpnapi
echo "5. Установка прав на data/vpn.db..."
chown vpnapi:vpnapi "$VPN_DIR/data/vpn.db"
chmod 660 "$VPN_DIR/data/vpn.db"

# 6. data/ - должна быть доступна для записи vpnapi
echo "6. Установка прав на data/..."
chown vpnapi:vpnapi "$VPN_DIR/data/"
chmod 755 "$VPN_DIR/data/"

echo ""
echo "✅ Права доступа исправлены!"
echo ""
echo "Проверка:"
ls -lad "$VPN_DIR/logs/"
ls -lad "$VPN_DIR/config/"
ls -la "$VPN_DIR/config/config.json"
ls -lad "$VPN_DIR/config/backups/"
ls -lad "$VPN_DIR/data/"
ls -la "$VPN_DIR/data/vpn.db"
