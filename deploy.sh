#!/bin/bash

# 🚀 Автоматический скрипт развертывания VPN сервера
# Версия: 2.1.1
# Дата: 5 августа 2025

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка root прав
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен быть запущен с правами root"
        exit 1
    fi
}

# Проверка ОС
check_os() {
    log_info "Проверка операционной системы..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Не удалось определить операционную систему"
        exit 1
    fi
    
    log_success "Обнаружена ОС: $OS $VER"
}

# Обновление системы
update_system() {
    log_info "Обновление системы..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt update && apt upgrade -y
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum update -y
    else
        log_warning "Неизвестная ОС, пропускаем обновление"
    fi
    
    log_success "Система обновлена"
}

# Установка зависимостей
install_dependencies() {
    log_info "Установка зависимостей..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt install -y git curl wget python3 python3-pip python3-venv nginx certbot python3-certbot-nginx unzip
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum install -y git curl wget python3 python3-pip nginx certbot python3-certbot-nginx unzip
    fi
    
    log_success "Зависимости установлены"
}

# Установка Xray
install_xray() {
    log_info "Установка Xray-core..."
    
    cd /usr/local/bin
    wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-linux-64.zip
    unzip -o xray.zip
    chmod +x xray
    rm xray.zip
    
    log_success "Xray установлен"
}

# Клонирование проекта
clone_project() {
    log_info "Клонирование проекта..."
    
    cd /root
    if [[ -d "vpn-server" ]]; then
        log_warning "Директория vpn-server уже существует, удаляем..."
        rm -rf vpn-server
    fi
    
    git clone https://github.com/merdocx/veil-v2ray.git vpn-server
    cd vpn-server
    
    # Проверка версии
    LATEST_TAG=$(git tag -l | tail -1)
    log_success "Проект клонирован, версия: $LATEST_TAG"
}

# Настройка Python окружения
setup_python() {
    log_info "Настройка Python окружения..."
    
    cd /root/vpn-server
    python3 -m venv venv
    source venv/bin/activate
    pip install fastapi uvicorn[standard] pydantic python-multipart
    
    log_success "Python окружение настроено"
}

# Создание конфигурации
create_config() {
    log_info "Создание конфигурации..."
    
    cd /root/vpn-server
    
    # Создание .env файла
    cat > .env << 'EOF'
VPN_API_KEY=your-secret-api-key-here
VPN_HOST=0.0.0.0
VPN_PORT=8000
VPN_ENABLE_HTTPS=true
VPN_SSL_CERT_PATH=/etc/ssl/certs/vpn-api.crt
VPN_SSL_KEY_PATH=/etc/ssl/private/vpn-api.key
EOF
    
    # Генерация API ключа
    python3 generate_api_key.py
    
    # Копирование конфигурации Xray
    cp config/config.example.json config/config.json
    
    log_success "Конфигурация создана"
}

# Создание SSL сертификатов
create_ssl() {
    log_info "Создание SSL сертификатов..."
    
    mkdir -p /etc/ssl/certs /etc/ssl/private
    
    # Создание самоподписанного сертификата
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/vpn-api.key \
        -out /etc/ssl/certs/vpn-api.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    log_success "SSL сертификаты созданы"
}

# Настройка Nginx
setup_nginx() {
    log_info "Настройка Nginx..."
    
    # Создание конфигурации
    cat > /etc/nginx/sites-available/vpn-api << 'EOF'
server {
    listen 443 ssl http2;
    server_name _;

    ssl_certificate /etc/ssl/certs/vpn-api.crt;
    ssl_certificate_key /etc/ssl/private/vpn-api.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}
EOF
    
    # Активация конфигурации
    ln -sf /etc/nginx/sites-available/vpn-api /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Проверка конфигурации
    nginx -t
    
    log_success "Nginx настроен"
}

# Создание systemd сервисов
create_services() {
    log_info "Создание systemd сервисов..."
    
    # VPN API сервис
    cat > /etc/systemd/system/vpn-api.service << 'EOF'
[Unit]
Description=VPN Key Management API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/vpn-server
Environment=PATH=/root/vpn-server/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/root/vpn-server/venv/bin/python /root/vpn-server/api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Xray сервис
    cat > /etc/systemd/system/xray.service << 'EOF'
[Unit]
Description=Xray Service
Documentation=https://github.com/xtls
After=network.target nss-lookup.target

[Service]
User=root
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
ExecStart=/usr/local/bin/xray run -config /root/vpn-server/config/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "Systemd сервисы созданы"
}

# Настройка файрвола
setup_firewall() {
    log_info "Настройка файрвола..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 8000/tcp
        ufw allow 10001:10020/tcp
        ufw --force enable
        log_success "UFW настроен"
    else
        # iptables
        iptables -A INPUT -p tcp --dport 22 -j ACCEPT
        iptables -A INPUT -p tcp --dport 80 -j ACCEPT
        iptables -A INPUT -p tcp --dport 443 -j ACCEPT
        iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
        iptables -A INPUT -p tcp --dport 10001:10020 -j ACCEPT
        log_success "iptables настроен"
    fi
}

# Запуск сервисов
start_services() {
    log_info "Запуск сервисов..."
    
    systemctl daemon-reload
    
    systemctl enable vpn-api
    systemctl enable xray
    systemctl enable nginx
    
    systemctl start vpn-api
    systemctl start xray
    systemctl start nginx
    
    log_success "Сервисы запущены"
}

# Проверка развертывания
check_deployment() {
    log_info "Проверка развертывания..."
    
    # Проверка статуса сервисов
    if systemctl is-active --quiet vpn-api; then
        log_success "VPN API сервис работает"
    else
        log_error "VPN API сервис не работает"
        return 1
    fi
    
    if systemctl is-active --quiet xray; then
        log_success "Xray сервис работает"
    else
        log_error "Xray сервис не работает"
        return 1
    fi
    
    if systemctl is-active --quiet nginx; then
        log_success "Nginx сервис работает"
    else
        log_error "Nginx сервис не работает"
        return 1
    fi
    
    # Проверка портов
    if netstat -tlnp | grep -q ":8000"; then
        log_success "Порт 8000 (API) открыт"
    else
        log_error "Порт 8000 (API) не открыт"
        return 1
    fi
    
    if netstat -tlnp | grep -q ":443"; then
        log_success "Порт 443 (HTTPS) открыт"
    else
        log_error "Порт 443 (HTTPS) не открыт"
        return 1
    fi
    
    log_success "Развертывание успешно завершено!"
}

# Вывод информации
show_info() {
    echo ""
    echo "=========================================="
    echo "🚀 VPN сервер успешно развернут!"
    echo "=========================================="
    echo ""
    echo "📋 Информация о развертывании:"
    echo "   • API URL: https://$(hostname -I | awk '{print $1}'):8000"
    echo "   • Nginx URL: https://$(hostname -I | awk '{print $1}')"
    echo "   • Версия проекта: $(cd /root/vpn-server && git tag -l | tail -1)"
    echo ""
    echo "🔧 Полезные команды:"
    echo "   • Статус сервисов: systemctl status vpn-api xray nginx"
    echo "   • Логи API: journalctl -u vpn-api -f"
    echo "   • Логи Xray: journalctl -u xray -f"
    echo "   • Проверка API: curl -k https://localhost:8000/api/"
    echo ""
    echo "🔒 Безопасность:"
    echo "   • Измените API ключ в файле /root/vpn-server/.env"
    echo "   • Настройте SSL сертификаты для домена"
    echo "   • Настройте fail2ban для защиты"
    echo ""
    echo "📚 Документация:"
    echo "   • /root/vpn-server/README.md"
    echo "   • /root/vpn-server/DEPLOYMENT_GUIDE.md"
    echo ""
    echo "=========================================="
}

# Основная функция
main() {
    echo "🚀 Начинаем развертывание VPN сервера..."
    echo ""
    
    check_root
    check_os
    update_system
    install_dependencies
    install_xray
    clone_project
    setup_python
    create_config
    create_ssl
    setup_nginx
    create_services
    setup_firewall
    start_services
    check_deployment
    show_info
}

# Запуск скрипта
main "$@" 