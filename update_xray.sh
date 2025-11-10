#!/bin/bash

# Скрипт обновления Xray до последней версии
# Автор: VPN Server Management
# Дата: $(date +%Y-%m-%d)
# Использование:
#   sudo ./update_xray.sh        # обновление до последней версии
#   ./update_xray.sh --check     # только проверка (возвращает 1, если доступно обновление)

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Режим выполнения: обновление по умолчанию
MODE="update"
if [[ "$1" == "--check" ]]; then
    MODE="check"
fi

# Проверка прав root только для режима обновления
if [[ "$MODE" == "update" ]] && [ "$EUID" -ne 0 ]; then
    print_error "Запустите скрипт с правами root: sudo $0"
    exit 1
fi

print_info "=== $( [[ \"$MODE\" == \"check\" ]] && echo \"Проверка\" || echo \"Обновление\" ) Xray до последней версии ==="

# Получение текущей версии
CURRENT_VERSION=$(/usr/local/bin/xray version | head -n1 | grep -o 'Xray [0-9.]*' | cut -d' ' -f2)
print_info "Текущая версия: $CURRENT_VERSION"

# Получение последней версии
print_info "Получение информации о последней версии..."
LATEST_VERSION=$(curl -s https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep '"tag_name"' | cut -d'"' -f4 | sed 's/v//')
print_info "Последняя версия: $LATEST_VERSION"

# Проверка необходимости обновления
if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    if [[ "$MODE" == "check" ]]; then
        print_success "Xray обновлен до последней версии ($CURRENT_VERSION)."
    else
        print_success "Xray уже обновлен до последней версии!"
    fi
    exit 0
fi

if [[ "$MODE" == "check" ]]; then
    print_warning "Доступно обновление Xray: текущая $CURRENT_VERSION, последняя $LATEST_VERSION"
    exit 1
fi

print_warning "Обновление с $CURRENT_VERSION до $LATEST_VERSION"

# Создание резервной копии
print_info "Создание резервной копии текущей конфигурации..."
BACKUP_DIR="/root/vpn-server/config/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp /root/vpn-server/config/config.json "$BACKUP_DIR/"
cp /root/vpn-server/config/keys.json "$BACKUP_DIR/"
cp /root/vpn-server/config/ports.json "$BACKUP_DIR/"
print_success "Резервная копия создана: $BACKUP_DIR"

# Остановка Xray
print_info "Остановка Xray сервиса..."
systemctl stop xray

# Скачивание новой версии
print_info "Скачивание Xray v$LATEST_VERSION..."
cd /tmp
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        ARCH="64"
        ;;
    aarch64)
        ARCH="arm64-v8a"
        ;;
    armv7l)
        ARCH="arm32-v7a"
        ;;
    *)
        print_error "Неподдерживаемая архитектура: $ARCH"
        exit 1
        ;;
esac

DOWNLOAD_URL="https://github.com/XTLS/Xray-core/releases/download/v$LATEST_VERSION/Xray-linux-$ARCH.zip"
print_info "URL: $DOWNLOAD_URL"

wget -q "$DOWNLOAD_URL" -O "xray-linux-$ARCH.zip"
if [ $? -ne 0 ]; then
    print_error "Ошибка скачивания Xray"
    exit 1
fi

# Распаковка
print_info "Распаковка архива..."
unzip -q "xray-linux-$ARCH.zip"
if [ $? -ne 0 ]; then
    print_error "Ошибка распаковки архива"
    exit 1
fi

# Резервная копия старого бинарника
print_info "Создание резервной копии старого бинарника..."
BACKUP_BIN="/usr/local/bin/xray.backup.$(date +%Y%m%d_%H%M%S)"
cp /usr/local/bin/xray "$BACKUP_BIN"

# Установка новой версии
print_info "Установка новой версии Xray..."
cp xray /usr/local/bin/
chmod +x /usr/local/bin/xray

# Проверка установки
print_info "Проверка установки..."
NEW_VERSION=$(/usr/local/bin/xray version | head -n1 | grep -o 'Xray [0-9.]*' | cut -d' ' -f2)
if [ "$NEW_VERSION" = "$LATEST_VERSION" ]; then
    print_success "Xray успешно обновлен до версии $NEW_VERSION"
else
    print_error "Ошибка обновления. Текущая версия: $NEW_VERSION"
    exit 1
fi

# Проверка конфигурации
print_info "Проверка конфигурации..."
/usr/local/bin/xray test -c /root/vpn-server/config/config.json
if [ $? -ne 0 ]; then
    print_error "Ошибка в конфигурации после обновления!"
    print_warning "Восстановление из резервной копии..."
    cp "$BACKUP_BIN" /usr/local/bin/xray
    systemctl start xray
    exit 1
fi

# Запуск Xray
print_info "Запуск Xray сервиса..."
systemctl start xray

# Проверка статуса
sleep 3
if systemctl is-active --quiet xray; then
    print_success "Xray успешно запущен и работает"
else
    print_error "Ошибка запуска Xray"
    print_warning "Проверьте логи: journalctl -u xray -f"
    exit 1
fi

# Очистка временных файлов
print_info "Очистка временных файлов..."
rm -f /tmp/xray-linux-$ARCH.zip /tmp/xray

# Финальная проверка
print_info "=== Финальная проверка ==="
print_info "Версия Xray: $(/usr/local/bin/xray version | head -n1)"
print_info "Статус сервиса: $(systemctl is-active xray)"
ACTIVE_443=$(ss -tlnp | awk '/:443[[:space:]]/ {count++} END {print count+0}')
print_info "Порт 443: $ACTIVE_443 активных соединений"

print_success "=== Обновление завершено успешно! ==="
print_info "Резервная копия сохранена в: $BACKUP_DIR"
print_warning "Рекомендуется перезапустить VPN API для полной совместимости:"
print_warning "systemctl restart vpn-api"
