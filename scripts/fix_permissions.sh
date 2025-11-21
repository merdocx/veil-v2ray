#!/bin/bash
# Скрипт для исправления прав доступа VPN сервера
# Использование: sudo ./scripts/fix_permissions.sh

set -e

VPN_DIR="/root/vpn-server"

echo "=== Исправление прав доступа ==="

# 1. logs/ - должен быть root:root (Xray работает от root)
echo "1. Установка прав на logs/..."
chown -R root:root "$VPN_DIR/logs/"
chmod -R 755 "$VPN_DIR/logs/"
chmod 644 "$VPN_DIR/logs"/*.log 2>/dev/null || true

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
