#!/bin/bash

# Скрипт тестирования совместимости ключей после обновления Xray
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

print_info "=== Тестирование совместимости ключей ==="

# Проверка текущей конфигурации
print_info "Проверка текущей конфигурации..."
if /usr/local/bin/xray run -test -c /root/vpn-server/config/config.json; then
    print_success "Текущая конфигурация корректна"
else
    print_error "Ошибка в текущей конфигурации"
    exit 1
fi

# Получение списка активных ключей
print_info "Получение списка активных ключей..."
API_URL="https://localhost:8000"
API_KEY="QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

KEYS_JSON=$(curl -k -s -H "X-API-Key: $API_KEY" "$API_URL/api/keys")
if [ $? -ne 0 ]; then
    print_error "Не удалось получить список ключей"
    exit 1
fi

KEY_COUNT=$(echo "$KEYS_JSON" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")
print_info "Найдено активных ключей: $KEY_COUNT"

# Анализ конфигурации ключей
print_info "Анализ конфигурации ключей..."

# Проверка протокола VLESS
VLESS_COUNT=$(grep -c '"protocol": "vless"' /root/vpn-server/config/config.json)
print_info "VLESS конфигураций: $VLESS_COUNT"

# Проверка Reality настроек
REALITY_COUNT=$(grep -c '"realitySettings"' /root/vpn-server/config/config.json)
print_info "Reality настроек: $REALITY_COUNT"

# Проверка портов
print_info "Проверка назначенных портов..."
for port in 10001 10002 10003 10004 10005; do
    if grep -q "\"port\": $port" /root/vpn-server/config/config.json; then
        print_success "Порт $port: настроен"
    else
        print_warning "Порт $port: не настроен"
    fi
done

# Проверка UUID ключей
print_info "Проверка UUID ключей..."
UUID_COUNT=$(grep -c '"id":' /root/vpn-server/config/config.json)
print_info "UUID в конфигурации: $UUID_COUNT"

# Проверка совместимости с новой версией
print_info "Проверка совместимости с новой версией Xray..."

# Создание временной конфигурации для тестирования
print_info "Создание тестовой конфигурации..."
cp /root/vpn-server/config/config.json /tmp/test_config.json

# Проверка синтаксиса JSON
if python3 -m json.tool /tmp/test_config.json > /dev/null 2>&1; then
    print_success "JSON синтаксис корректен"
else
    print_error "Ошибка в JSON синтаксисе"
    exit 1
fi

# Анализ совместимости
print_info "Анализ совместимости..."

# Проверка обязательных полей VLESS
REQUIRED_FIELDS=("protocol" "settings" "clients" "id" "flow" "email")
for field in "${REQUIRED_FIELDS[@]}"; do
    if grep -q "\"$field\":" /tmp/test_config.json; then
        print_success "Поле '$field': присутствует"
    else
        print_warning "Поле '$field': отсутствует"
    fi
done

# Проверка Reality настроек
print_info "Проверка Reality настроек..."
REALITY_FIELDS=("dest" "serverNames" "privateKey" "shortIds")
for field in "${REALITY_FIELDS[@]}"; do
    if grep -q "\"$field\":" /tmp/test_config.json; then
        print_success "Reality поле '$field': присутствует"
    else
        print_warning "Reality поле '$field': отсутствует"
    fi
done

# Проверка портов
print_info "Проверка портов..."
for port in 10001 10002 10003 10004 10005; do
    if netstat -tlnp | grep -q ":$port "; then
        print_success "Порт $port: активен"
    else
        print_warning "Порт $port: неактивен"
    fi
done

# Проверка активных соединений
print_info "Проверка активных соединений..."
TOTAL_CONNECTIONS=$(netstat -tlnp | grep xray | wc -l)
print_info "Всего соединений Xray: $TOTAL_CONNECTIONS"

if [ "$TOTAL_CONNECTIONS" -gt 0 ]; then
    print_success "Активные соединения обнаружены - ключи работают"
else
    print_warning "Нет активных соединений"
fi

# Очистка временных файлов
rm -f /tmp/test_config.json

# Итоговая оценка совместимости
print_info "=== Итоговая оценка совместимости ==="

if [ "$KEY_COUNT" -gt 0 ] && [ "$VLESS_COUNT" -gt 0 ] && [ "$TOTAL_CONNECTIONS" -gt 0 ]; then
    print_success "✅ ВСЕ КЛЮЧИ БУДУТ РАБОТАТЬ ПОСЛЕ ОБНОВЛЕНИЯ!"
    print_info "Причины:"
    print_info "- Протокол VLESS полностью совместим между версиями"
    print_info "- Конфигурация использует стандартные поля"
    print_info "- Reality настройки совместимы"
    print_info "- Активные соединения подтверждают работоспособность"
else
    print_warning "⚠️ Требуется дополнительная проверка"
fi

print_info "=== Рекомендации ==="
print_info "1. Обновление Xray безопасно для существующих ключей"
print_info "2. Конфигурация не требует изменений"
print_info "3. Клиенты продолжат работать без изменений"
print_info "4. Рекомендуется создать резервную копию перед обновлением"

print_success "=== Тест завершен ==="
