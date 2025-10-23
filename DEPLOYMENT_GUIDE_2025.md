# 🚀 Руководство по разворачиванию VPN сервера (2025)

**Версия:** 2.1.4  
**Дата обновления:** 22 октября 2025  
**Xray версия:** v25.10.15 (последняя)

---

## 📋 **Требования к серверу**

### **Минимальные требования:**
- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM:** 1GB (рекомендуется 2GB)
- **CPU:** 1 ядро (рекомендуется 2 ядра)
- **Диск:** 20GB свободного места
- **Сеть:** Публичный IP с открытыми портами 443, 8000
- **Права:** root доступ

### **Рекомендуемые требования:**
- **OS:** Ubuntu 22.04 LTS
- **RAM:** 2GB+
- **CPU:** 2+ ядра
- **Диск:** 40GB+ SSD
- **Сеть:** Статический IP

---

## 🔧 **Шаг 1: Подготовка сервера**

### **1.1 Обновление системы**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### **1.2 Установка необходимых пакетов**
```bash
# Ubuntu/Debian
sudo apt install -y curl wget git python3 python3-pip python3-venv nginx unzip

# CentOS/RHEL
sudo yum install -y curl wget git python3 python3-pip nginx unzip
```

### **1.3 Создание пользователя (опционально)**
```bash
# Создание пользователя для VPN сервера
sudo useradd -m -s /bin/bash vpn
sudo usermod -aG sudo vpn
```

---

## 📦 **Шаг 2: Установка Xray v25.10.15**

### **2.1 Скачивание и установка Xray**
```bash
# Определение архитектуры
ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH="64";;
    aarch64) ARCH="arm64-v8a";;
    armv7l) ARCH="arm32-v7a";;
    *) echo "Неподдерживаемая архитектура: $ARCH"; exit 1;;
esac

# Скачивание Xray
cd /tmp
wget "https://github.com/XTLS/Xray-core/releases/download/v25.10.15/Xray-linux-$ARCH.zip"
unzip "Xray-linux-$ARCH.zip"

# Установка
sudo cp xray /usr/local/bin/
sudo chmod +x /usr/local/bin/xray

# Проверка установки
/usr/local/bin/xray version
```

### **2.2 Создание systemd сервиса**
```bash
sudo tee /etc/systemd/system/xray.service > /dev/null << 'EOF'
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

sudo systemctl daemon-reload
sudo systemctl enable xray
```

---

## 🐍 **Шаг 3: Настройка Python окружения**

### **3.1 Создание директории проекта**
```bash
sudo mkdir -p /root/vpn-server
cd /root/vpn-server
```

### **3.2 Создание виртуального окружения**
```bash
python3 -m venv venv
source venv/bin/activate
```

### **3.3 Установка зависимостей**
```bash
# Создание requirements.txt
cat > requirements.txt << 'EOF'
# VPN Server Dependencies
# Версия: 2.1.4
# Дата: 2025-10-22

# Основные зависимости
fastapi==0.116.1
uvicorn[standard]==0.35.0
pydantic==2.11.7
python-multipart==0.0.20
requests==2.32.4

# Логирование и мониторинг
structlog==23.2.0
psutil==5.9.6

# Безопасность
slowapi==0.1.9

# Тестирование
pytest==7.4.3
pytest-asyncio==0.21.1

# Дополнительные утилиты
click==8.2.2
certifi==2025.7.14
charset-normalizer==3.4.2
idna==3.10
urllib3==2.5.0
EOF

# Установка зависимостей
pip install -r requirements.txt
```

---

## 📁 **Шаг 4: Копирование файлов проекта**

### **4.1 Скачивание проекта**
```bash
# Если проект в Git репозитории
git clone <your-repository-url> /root/vpn-server

# Или копирование файлов вручную
# Скопируйте все файлы проекта в /root/vpn-server/
```

### **4.2 Структура проекта**
```
/root/vpn-server/
├── api.py                      # Основной API сервер
├── port_manager.py             # Управление портами
├── xray_config_manager.py      # Управление конфигурацией Xray
├── simple_traffic_monitor.py   # Мониторинг трафика
├── traffic_history_manager.py  # Исторические данные трафика
├── generate_client_config.py   # Генерация клиентских конфигураций
├── requirements.txt            # Python зависимости
├── .env                       # Переменные окружения
├── config/
│   ├── config.json            # Конфигурация Xray
│   ├── keys.json              # База ключей
│   ├── ports.json             # Назначения портов
│   └── traffic_history.json   # Исторические данные трафика
└── logs/                      # Логи приложения
```

---

## ⚙️ **Шаг 5: Настройка конфигурации**

### **5.1 Создание переменных окружения**
```bash
cat > /root/vpn-server/.env << 'EOF'
# VPN API Configuration
# ⚠️ ВНИМАНИЕ: Этот файл содержит секретные данные. Не коммитьте его в git!

# API ключ для аутентификации (замените на свой секретный ключ)
VPN_API_KEY=your-secret-api-key-here

# Настройки безопасности
VPN_ENABLE_HTTPS=true
VPN_SSL_CERT_PATH=/etc/ssl/certs/vpn-api.crt
VPN_SSL_KEY_PATH=/etc/ssl/private/vpn-api.key

# Настройки сервера
VPN_HOST=0.0.0.0
VPN_PORT=8000
VPN_WORKERS=1

# Настройки логирования
VPN_LOG_LEVEL=info
VPN_LOG_FILE=/root/vpn-server/logs/api.log
EOF

# Установка правильных прав доступа
chmod 600 /root/vpn-server/.env
```

### **5.2 Генерация SSL сертификатов**
```bash
# Создание директории для сертификатов
sudo mkdir -p /etc/ssl/certs /etc/ssl/private

# Генерация самоподписанного сертификата (для тестирования)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/vpn-api.key \
    -out /etc/ssl/certs/vpn-api.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Установка правильных прав доступа
sudo chmod 600 /etc/ssl/private/vpn-api.key
sudo chmod 644 /etc/ssl/certs/vpn-api.crt
```

### **5.3 Создание базовой конфигурации Xray**
```bash
mkdir -p /root/vpn-server/config

# Создание базовой конфигурации Xray
cat > /root/vpn-server/config/config.json << 'EOF'
{
  "log": {
    "loglevel": "info",
    "access": "/root/vpn-server/logs/xray-access.log",
    "error": "/root/vpn-server/logs/xray-error.log"
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
          "privateKey": "your-private-key-here",
          "shortIds": [
            "your-short-id-here"
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
```

### **5.4 Инициализация файлов данных**
```bash
# Создание пустых файлов данных
echo '[]' > /root/vpn-server/config/keys.json
echo '{"used_ports": {}, "port_assignments": {}, "created_at": "'$(date -Iseconds)'", "last_updated": "'$(date -Iseconds)'"}' > /root/vpn-server/config/ports.json
echo '{"keys": {}, "daily_stats": {}, "monthly_stats": {}}' > /root/vpn-server/config/traffic_history.json

# Создание директории для логов
mkdir -p /root/vpn-server/logs
```

---

## 🔑 **Шаг 6: Генерация Reality ключей**

### **6.1 Генерация ключей**
```bash
cd /root/vpn-server

# Генерация приватного ключа
/usr/local/bin/xray x25519 > reality_keys.txt

# Генерация публичного ключа
/usr/local/bin/xray x25519 -i $(cat reality_keys.txt | grep "Private key:" | cut -d' ' -f3) > reality_public.txt

# Генерация short ID
SHORT_ID=$(openssl rand -hex 8)
echo "Short ID: $SHORT_ID"

# Извлечение приватного ключа
PRIVATE_KEY=$(cat reality_keys.txt | grep "Private key:" | cut -d' ' -f3)
echo "Private key: $PRIVATE_KEY"
```

### **6.2 Обновление конфигурации Xray**
```bash
# Обновление конфигурации с реальными ключами
sed -i "s/your-private-key-here/$PRIVATE_KEY/g" /root/vpn-server/config/config.json
sed -i "s/your-short-id-here/$SHORT_ID/g" /root/vpn-server/config/config.json

# Удаление временных файлов
rm -f reality_keys.txt reality_public.txt
```

---

## 🚀 **Шаг 7: Запуск сервисов**

### **7.1 Создание systemd сервиса для VPN API**
```bash
sudo tee /etc/systemd/system/vpn-api.service > /dev/null << 'EOF'
[Unit]
Description=VPN Key Management API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/vpn-server
Environment=PATH=/root/vpn-server/venv/bin
ExecStart=/root/vpn-server/venv/bin/python /root/vpn-server/api.py
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vpn-api
```

### **7.2 Настройка Nginx (опционально)**
```bash
# Создание конфигурации Nginx
sudo tee /etc/nginx/sites-available/vpn-api > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass https://localhost:8000;
        proxy_ssl_verify off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Активация конфигурации
sudo ln -s /etc/nginx/sites-available/vpn-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### **7.3 Запуск всех сервисов**
```bash
# Запуск Xray
sudo systemctl start xray
sudo systemctl status xray

# Запуск VPN API
sudo systemctl start vpn-api
sudo systemctl status vpn-api

# Запуск Nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

---

## ✅ **Шаг 8: Проверка установки**

### **8.1 Проверка статуса сервисов**
```bash
# Проверка всех сервисов
sudo systemctl status xray vpn-api nginx

# Проверка портов
sudo netstat -tlnp | grep -E ":443|:8000"

# Проверка логов
sudo journalctl -u xray -f
sudo journalctl -u vpn-api -f
```

### **8.2 Тестирование API**
```bash
# Проверка health check
curl -k https://localhost:8000/health

# Проверка API (замените YOUR_API_KEY на реальный ключ)
curl -k -H "X-API-Key: YOUR_API_KEY" https://localhost:8000/api/keys

# Создание тестового ключа
curl -k -X POST -H "Content-Type: application/json" \
     -H "X-API-Key: YOUR_API_KEY" \
     -d '{"name": "test@example.com"}' \
     https://localhost:8000/api/keys
```

---

## 🔧 **Шаг 9: Настройка файрвола**

### **9.1 UFW (Ubuntu/Debian)**
```bash
# Установка UFW
sudo apt install ufw -y

# Настройка правил
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS/Xray
sudo ufw allow 8000/tcp  # VPN API (если нужен внешний доступ)

# Включение файрвола
sudo ufw --force enable
```

### **9.2 Firewalld (CentOS/RHEL)**
```bash
# Настройка правил
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp

# Перезагрузка правил
sudo firewall-cmd --reload
```

---

## 📊 **Шаг 10: Мониторинг и обслуживание**

### **10.1 Полезные команды**
```bash
# Проверка статуса
sudo systemctl status xray vpn-api nginx

# Просмотр логов
sudo journalctl -u xray -f
sudo journalctl -u vpn-api -f

# Перезапуск сервисов
sudo systemctl restart xray
sudo systemctl restart vpn-api

# Проверка health check
curl -k https://localhost:8000/health
```

### **10.2 Автоматическое обновление Xray**
```bash
# Создание скрипта обновления
sudo tee /usr/local/bin/update-xray.sh > /dev/null << 'EOF'
#!/bin/bash
# Скрипт обновления Xray (из проекта)
/root/vpn-server/update_xray.sh
EOF

sudo chmod +x /usr/local/bin/update-xray.sh

# Добавление в cron для автоматического обновления (опционально)
# echo "0 2 * * 0 /usr/local/bin/update-xray.sh" | sudo crontab -
```

---

## 🛠️ **Устранение неполадок**

### **Проблема: Xray не запускается**
```bash
# Проверка конфигурации
/usr/local/bin/xray run -test -c /root/vpn-server/config/config.json

# Проверка логов
sudo journalctl -u xray -f

# Проверка портов
sudo netstat -tlnp | grep :443
```

### **Проблема: VPN API не отвечает**
```bash
# Проверка статуса
sudo systemctl status vpn-api

# Проверка логов
sudo journalctl -u vpn-api -f

# Проверка портов
sudo netstat -tlnp | grep :8000

# Проверка переменных окружения
cat /root/vpn-server/.env
```

### **Проблема: SSL сертификаты**
```bash
# Проверка сертификатов
sudo openssl x509 -in /etc/ssl/certs/vpn-api.crt -text -noout

# Пересоздание сертификатов
sudo rm /etc/ssl/certs/vpn-api.crt /etc/ssl/private/vpn-api.key
# Повторите шаг 5.2
```

---

## 📚 **Дополнительные ресурсы**

### **Полезные ссылки:**
- [Xray Core GitHub](https://github.com/XTLS/Xray-core)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [VLESS Protocol](https://github.com/XTLS/Xray-core/discussions/173)

### **Конфигурация клиентов:**
- **Android:** v2rayNG, SagerNet
- **iOS:** Shadowrocket, OneClick
- **Windows:** v2rayN, Clash
- **macOS:** ClashX, V2rayU
- **Linux:** v2ray-core, Clash

---

## 🎯 **Заключение**

После выполнения всех шагов у вас будет:

✅ **Полнофункциональный VPN сервер** с Xray v25.10.15  
✅ **RESTful API** для управления ключами  
✅ **HTTPS поддержка** для безопасности  
✅ **Health check** для мониторинга  
✅ **Автоматическое управление портами**  
✅ **Мониторинг трафика** в реальном времени  
✅ **Исторические данные** трафика  

**Время развертывания:** ~30 минут  
**Сложность:** Средняя  
**Поддержка:** 5 активных ключей, до 20 максимум

---

**Удачного развертывания! 🚀**
