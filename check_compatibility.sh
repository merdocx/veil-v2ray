#!/bin/bash

# Скрипт проверки совместимости после обновления Xray
# Автор: VPN Server Management

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_info "=== Проверка совместимости после обновления Xray ==="

# Проверка версии Xray
print_info "Проверка версии Xray..."
XRAY_VERSION=$(/usr/local/bin/xray version | head -n1 | grep -o 'Xray [0-9.]*' | cut -d' ' -f2)
print_info "Версия Xray: $XRAY_VERSION"

# Проверка статуса сервисов
print_info "Проверка статуса сервисов..."
services=("xray" "vpn-api" "nginx")
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        print_success "$service: активен"
    else
        print_error "$service: неактивен"
    fi
done

# Проверка конфигурации
print_info "Проверка конфигурации Xray..."
if /usr/local/bin/xray test -c /root/vpn-server/config/config.json; then
    print_success "Конфигурация Xray корректна"
else
    print_error "Ошибка в конфигурации Xray"
fi

# Проверка портов
print_info "Проверка активных портов..."
for port in 10001 10002 10003 10004 10005; do
    if netstat -tlnp | grep -q ":$port "; then
        print_success "Порт $port: активен"
    else
        print_warning "Порт $port: неактивен"
    fi
done

# Проверка API
print_info "Проверка VPN API..."
API_URL="https://localhost:8000"
API_KEY="QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

if curl -k -s -H "X-API-Key: $API_KEY" "$API_URL/api/keys" | grep -q "id"; then
    print_success "VPN API отвечает корректно"
else
    print_error "VPN API не отвечает"
fi

# Проверка трафика
print_info "Проверка мониторинга трафика..."
if curl -k -s -H "X-API-Key: $API_KEY" "$API_URL/api/traffic/simple" | grep -q "ports"; then
    print_success "Мониторинг трафика работает"
else
    print_warning "Проблемы с мониторингом трафика"
fi

# Проверка логов на ошибки
print_info "Проверка логов Xray на ошибки..."
ERROR_COUNT=$(journalctl -u xray --since "5 minutes ago" | grep -i error | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "Ошибок в логах Xray не найдено"
else
    print_warning "Найдено $ERROR_COUNT ошибок в логах Xray"
    print_info "Последние ошибки:"
    journalctl -u xray --since "5 minutes ago" | grep -i error | tail -3
fi

# Проверка производительности
print_info "Проверка производительности..."
XRAY_MEMORY=$(ps aux | grep xray | grep -v grep | awk '{print $6}' | head -1)
if [ -n "$XRAY_MEMORY" ]; then
    XRAY_MEMORY_MB=$((XRAY_MEMORY / 1024))
    print_info "Использование памяти Xray: ${XRAY_MEMORY_MB}MB"
    if [ "$XRAY_MEMORY_MB" -lt 100 ]; then
        print_success "Использование памяти в норме"
    else
        print_warning "Высокое использование памяти"
    fi
fi

# Проверка активных соединений
print_info "Проверка активных соединений..."
TOTAL_CONNECTIONS=$(netstat -tlnp | grep xray | wc -l)
print_info "Всего соединений: $TOTAL_CONNECTIONS"

if [ "$TOTAL_CONNECTIONS" -gt 0 ]; then
    print_success "Активные соединения обнаружены"
else
    print_warning "Нет активных соединений"
fi

print_info "=== Проверка завершена ==="
print_info "Если все проверки прошли успешно, обновление можно считать успешным"
print_warning "В случае проблем проверьте логи: journalctl -u xray -f"
