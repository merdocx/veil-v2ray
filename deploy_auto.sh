#!/bin/bash

# Автоматический скрипт развертывания VPN сервера
# Версия: 2.1.4
# Дата: 2025-10-22
# Xray версия: v25.10.15

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции для вывода
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    print_error "Запустите скрипт с правами root: sudo $0"
    exit 1
fi

print_info "=== Автоматическое развертывание VPN сервера v2.1.4 ==="

# Переменные
VPN_DIR="/root/vpn-server"
XRAY_VERSION="25.10.15"
API_KEY=$(openssl rand -base64 32)

print_info "Директория проекта: $VPN_DIR"
print_info "Версия Xray: $XRAY_VERSION"
print_info "API ключ: $API_KEY"

# Шаг 1: Обновление системы
print_info "Обновление системы..."
apt update && apt upgrade -y

# Шаг 2: Установка зависимостей
print_info "Установка зависимостей..."
apt install -y curl wget git python3 python3-pip python3-venv nginx unzip openssl sqlite3

# Шаг 3: Создание директории проекта
print_info "Создание директории проекта..."
mkdir -p $VPN_DIR
cd $VPN_DIR

# Шаг 4: Установка Xray
print_info "Установка Xray v$XRAY_VERSION..."
cd /tmp
ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH="64";;
    aarch64) ARCH="arm64-v8a";;
    armv7l) ARCH="arm32-v7a";;
    *) print_error "Неподдерживаемая архитектура: $ARCH"; exit 1;;
esac

wget -q "https://github.com/XTLS/Xray-core/releases/download/v$XRAY_VERSION/Xray-linux-$ARCH.zip"
unzip -q "Xray-linux-$ARCH.zip"
cp xray /usr/local/bin/
chmod +x /usr/local/bin/xray
rm -f "Xray-linux-$ARCH.zip" xray

print_success "Xray установлен: $(/usr/local/bin/xray version | head -1)"

# Шаг 5: Настройка Python окружения
print_info "Настройка Python окружения..."
cd $VPN_DIR
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -q fastapi==0.116.1 uvicorn[standard]==0.35.0 pydantic==2.11.7 python-multipart==0.0.20 requests==2.32.4 psutil==5.9.6

# Шаг 6: Создание файлов проекта
print_info "Создание файлов проекта..."

# Создание .env файла
cat > .env << EOF
# VPN API Configuration
VPN_API_KEY=$API_KEY
VPN_ENABLE_HTTPS=true
VPN_SSL_CERT_PATH=/etc/ssl/certs/vpn-api.crt
VPN_SSL_KEY_PATH=/etc/ssl/private/vpn-api.key
VPN_HOST=0.0.0.0
VPN_PORT=8000
VPN_WORKERS=2
VPN_WORKER_MAX_REQUESTS=0
VPN_LOG_LEVEL=info
VPN_LOG_FILE=$VPN_DIR/logs/api.log
EOF

# Создание директорий
mkdir -p config logs data

# Создание пользователя и прав для сервиса
if ! id -u vpnapi >/dev/null 2>&1; then
    print_info "Создание системного пользователя vpnapi..."
    useradd --system --shell /usr/sbin/nologin --home $VPN_DIR vpnapi
else
    print_info "Пользователь vpnapi уже существует"
fi
chown -R vpnapi:vpnapi $VPN_DIR
chmod -R 750 $VPN_DIR

# Генерация SSL сертификатов
print_info "Генерация SSL сертификатов..."
mkdir -p /etc/ssl/certs /etc/ssl/private
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/vpn-api.key \
    -out /etc/ssl/certs/vpn-api.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
    -quiet

# Генерация Reality ключей
print_info "Генерация Reality ключей..."
/usr/local/bin/xray x25519 > reality_keys.txt
PRIVATE_KEY=$(cat reality_keys.txt | grep "Private key:" | cut -d' ' -f3)
SHORT_ID=$(openssl rand -hex 8)
rm -f reality_keys.txt

# Создание конфигурации Xray
cat > config/config.json << EOF
{
  "log": {
    "loglevel": "info",
    "access": "$VPN_DIR/logs/xray-access.log",
    "error": "$VPN_DIR/logs/xray-error.log"
  },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "www.microsoft.com:443",
          "xver": 0,
          "serverNames": [
            "www.microsoft.com"
          ],
          "privateKey": "$PRIVATE_KEY",
          "shortIds": [
            "$SHORT_ID"
          ]
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "settings": {}
    }
  ]
}
EOF

# Инициализация директорий (SQLite создаст базу автоматически)
mkdir -p logs data config/backups
print_info "data/vpn.db будет создан автоматически при первом запуске API"

# Шаг 7: Создание systemd сервисов
print_info "Создание systemd сервисов..."

# Xray сервис
cat > /etc/systemd/system/xray.service << 'EOF'
[Unit]
Description=Xray Service
Documentation=https://github.com/xtls
After=network.target nss-lookup.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/xray run -config /root/vpn-server/config/config.json
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

# VPN API сервис
cat > /etc/systemd/system/vpn-api.service << EOF
[Unit]
Description=VPN Key Management API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$VPN_DIR
Environment=PATH=$VPN_DIR/venv/bin
ExecStart=$VPN_DIR/venv/bin/python $VPN_DIR/api.py
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable xray vpn-api

# Шаг 8: Настройка файрвола
print_info "Настройка файрвола..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 22/tcp
    ufw allow 443/tcp
    ufw allow 8000/tcp
    ufw --force enable
elif command -v firewall-cmd >/dev/null 2>&1; then
    firewall-cmd --permanent --add-port=22/tcp
    firewall-cmd --permanent --add-port=443/tcp
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --reload
fi

# Шаг 9: Запуск сервисов
print_info "Запуск сервисов..."
systemctl start xray vpn-api

# Ожидание запуска
sleep 5

# Проверка статуса
if systemctl is-active --quiet xray && systemctl is-active --quiet vpn-api; then
    print_success "Все сервисы запущены успешно"
else
    print_error "Ошибка запуска сервисов"
    systemctl status xray vpn-api
    exit 1
fi

# Шаг 10: Проверка установки
print_info "Проверка установки..."

# Проверка health check
if curl -k -s https://localhost:8000/health | grep -q "healthy"; then
    print_success "Health check работает"
else
    print_warning "Health check не отвечает"
fi

# Финальная информация
print_success "=== УСТАНОВКА ЗАВЕРШЕНА ==="
echo ""
print_info "Информация о сервере:"
print_info "  API URL: https://$(curl -s ifconfig.me):8000"
print_info "  API ключ: $API_KEY"
print_info "  Reality Private Key: $PRIVATE_KEY"
print_info "  Reality Short ID: $SHORT_ID"
echo ""
print_info "Полезные команды:"
print_info "  Статус сервисов: systemctl status xray vpn-api"
print_info "  Логи Xray: journalctl -u xray -f"
print_info "  Логи API: journalctl -u vpn-api -f"
print_info "  Health check: curl -k https://localhost:8000/health"
echo ""
print_info "Создание первого ключа:"
print_info "  curl -k -X POST -H 'Content-Type: application/json' \\"
print_info "       -H 'X-API-Key: $API_KEY' \\"
print_info "       -d '{\"name\": \"test@example.com\"}' \\"
print_info "       https://localhost:8000/api/keys"
echo ""
print_success "VPN сервер готов к использованию! 🚀"
