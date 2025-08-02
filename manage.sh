#!/bin/bash

# Скрипт управления VPN сервером

VPN_DIR="/root/vpn-server"
API_URL="http://localhost:8000"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Функция проверки статуса сервисов
check_services() {
    print_status "Проверка статуса сервисов..."
    
    echo "=== Xray ==="
    systemctl is-active --quiet xray && print_status "Xray: активен" || print_error "Xray: неактивен"
    
    echo "=== VPN API ==="
    systemctl is-active --quiet vpn-api && print_status "VPN API: активен" || print_error "VPN API: неактивен"
    
    echo "=== Nginx ==="
    systemctl is-active --quiet nginx && print_status "Nginx: активен" || print_error "Nginx: неактивен"
}

# Функция создания ключа
create_key() {
    if [ -z "$1" ]; then
        echo "Использование: $0 create-key <имя_ключа>"
        exit 1
    fi
    
    print_status "Создание ключа: $1"
    
    response=$(curl -s -X POST "$API_URL/api/keys" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$1\"}")
    
    if echo "$response" | grep -q "id"; then
        print_status "Ключ создан успешно"
        echo "$response" | python3 -m json.tool
        
        # Автоматически перезапускаем Xray
        print_status "Перезапуск Xray для применения конфигурации..."
        ./restart_xray.sh
    else
        print_error "Ошибка создания ключа"
        echo "$response"
    fi
}

# Функция удаления ключа
delete_key() {
    if [ -z "$1" ]; then
        echo "Использование: $0 delete-key <id_ключа>"
        exit 1
    fi
    
    print_status "Удаление ключа: $1"
    
    response=$(curl -s -X DELETE "$API_URL/api/keys/$1")
    
    if echo "$response" | grep -q "successfully"; then
        print_status "Ключ удален успешно"
        
        # Автоматически перезапускаем Xray
        print_status "Перезапуск Xray для применения конфигурации..."
        ./restart_xray.sh
    else
        print_error "Ошибка удаления ключа"
        echo "$response"
    fi
}

# Функция списка ключей
list_keys() {
    print_status "Список активных ключей:"
    
    response=$(curl -s -X GET "$API_URL/api/keys")
    
    if echo "$response" | grep -q "id"; then
        echo "$response" | python3 -m json.tool
    else
        print_warning "Нет активных ключей"
    fi
}

# Функция получения конфигурации клиента
get_config() {
    if [ -z "$1" ]; then
        echo "Использование: $0 get-config <id_ключа>"
        exit 1
    fi
    
    print_status "Получение конфигурации для ключа: $1"
    
    response=$(curl -s -X GET "$API_URL/api/keys/$1/config")
    
    if echo "$response" | grep -q "client_config"; then
        echo "$response" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('=== Информация о ключе ===')
print(f'ID: {data[\"key\"][\"id\"]}')
print(f'Имя: {data[\"key\"][\"name\"]}')
print(f'UUID: {data[\"key\"][\"uuid\"]}')
print(f'Создан: {data[\"key\"][\"created_at\"]}')
print('\n=== Конфигурация клиента ===')
print(data['client_config'])
"
    else
        print_error "Ошибка получения конфигурации"
        echo "$response"
    fi
}

# Функция перезапуска сервисов
restart_services() {
    print_status "Перезапуск сервисов..."
    
    systemctl restart xray
    systemctl restart vpn-api
    systemctl reload nginx
    
    print_status "Сервисы перезапущены"
}

# Функция просмотра логов
view_logs() {
    if [ -z "$1" ]; then
        echo "Использование: $0 logs <xray|api|nginx>"
        exit 1
    fi
    
    case $1 in
        xray)
            print_status "Логи Xray:"
            journalctl -u xray -f
            ;;
        api)
            print_status "Логи VPN API:"
            journalctl -u vpn-api -f
            ;;
        nginx)
            print_status "Логи Nginx:"
            tail -f /var/log/nginx/access.log
            ;;
        *)
            print_error "Неизвестный сервис: $1"
            ;;
    esac
}

# Функция показа статистики
show_stats() {
    print_status "Статистика VPN сервера:"
    
    echo "=== Активные ключи ==="
    key_count=$(curl -s -X GET "$API_URL/api/keys" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")
    echo "Количество ключей: $key_count"
    
    echo "=== Системные ресурсы ==="
    echo "Использование памяти:"
    free -h
    
    echo "Использование диска:"
    df -h /root
    
    echo "Активные соединения:"
    netstat -tlnp | grep :443
}

# Функция показа помощи
show_help() {
    echo "VPN Server Management Script"
    echo ""
    echo "Использование: $0 <команда> [параметры]"
    echo ""
    echo "Команды:"
    echo "  status                    - Проверить статус сервисов"
    echo "  create-key <имя>          - Создать новый ключ"
    echo "  delete-key <id>           - Удалить ключ"
    echo "  list-keys                 - Показать список ключей"
    echo "  get-config <id>           - Получить конфигурацию клиента"
    echo "  restart                   - Перезапустить сервисы"
    echo "  logs <сервис>             - Показать логи (xray|api|nginx)"
    echo "  stats                     - Показать статистику"
    echo "  help                      - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 create-key \"Мой ключ\""
    echo "  $0 get-config 12345678-1234-1234-1234-123456789012"
    echo "  $0 logs xray"
}

# Основная логика
case $1 in
    status)
        check_services
        ;;
    create-key)
        create_key "$2"
        ;;
    delete-key)
        delete_key "$2"
        ;;
    list-keys)
        list_keys
        ;;
    get-config)
        get_config "$2"
        ;;
    restart)
        restart_services
        ;;
    logs)
        view_logs "$2"
        ;;
    stats)
        show_stats
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 