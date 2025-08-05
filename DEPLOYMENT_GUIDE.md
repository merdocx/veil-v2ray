# 🚀 Руководство по развертыванию VPN сервера

**Версия:** 2.1.1  
**Дата:** 5 августа 2025  
**Статус:** ✅ Готово к развертыванию

---

## 📋 Предварительные требования

### 🖥️ Системные требования
- **ОС:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM:** Минимум 2GB (рекомендуется 4GB+)
- **CPU:** 2 ядра (рекомендуется 4+)
- **Диск:** 20GB свободного места
- **Сеть:** Статический IP адрес
- **Права:** Root доступ или sudo права

### 🌐 Сетевые требования
- **Порты:** 443 (HTTPS), 8000 (API), 10001-10020 (VPN)
- **Домен:** Рекомендуется настроить домен
- **SSL:** Сертификат для HTTPS (Let's Encrypt)

---

## 🔧 Пошаговое развертывание

### 1️⃣ Подготовка сервера

#### Обновление системы
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

#### Установка необходимых пакетов
```bash
# Ubuntu/Debian
sudo apt install -y git curl wget python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y git curl wget python3 python3-pip nginx certbot python3-certbot-nginx
```

### 2️⃣ Клонирование проекта

```bash
# Клонирование репозитория
cd /root
git clone https://github.com/merdocx/veil-v2ray.git vpn-server
cd vpn-server

# Проверка версии
git tag -l | tail -1
# Должно показать: v2.1.1
```

### 3️⃣ Установка Xray-core

```bash
# Скачивание и установка Xray
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-linux-64.zip
unzip -o xray.zip
chmod +x xray
rm xray.zip

# Проверка установки
xray version
```

### 4️⃣ Настройка Python окружения

```bash
cd /root/vpn-server

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install fastapi uvicorn[standard] pydantic python-multipart
```

### 5️⃣ Настройка конфигурации

#### Создание файла .env
```bash
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
```

#### Настройка Xray конфигурации
```bash
# Копирование примера конфигурации
cp config/config.example.json config/config.json

# Редактирование конфигурации
nano config/config.json
```

**Важные параметры для изменения:**
```json
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": []
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "www.microsoft.com:443",
          "xver": 0,
          "serverNames": ["www.microsoft.com"],
          "privateKey": "your-private-key",
          "shortIds": [""]
        }
      }
    }
  ]
}
```

### 6️⃣ Настройка SSL сертификатов

#### Автоматический SSL (рекомендуется)
```bash
# Если есть домен
sudo certbot --nginx -d your-domain.com

# Настройка автообновления
sudo crontab -e
# Добавить строку:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

#### Ручной SSL (для тестирования)
```bash
# Создание самоподписанного сертификата
sudo mkdir -p /etc/ssl/certs /etc/ssl/private
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/vpn-api.key \
  -out /etc/ssl/certs/vpn-api.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### 7️⃣ Настройка Nginx

```bash
# Создание конфигурации Nginx
sudo tee /etc/nginx/sites-available/vpn-api << 'EOF'
server {
    listen 443 ssl http2;
    server_name your-domain.com;

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
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
EOF

# Активация конфигурации
sudo ln -s /etc/nginx/sites-available/vpn-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8️⃣ Создание systemd сервисов

#### VPN API сервис
```bash
sudo tee /etc/systemd/system/vpn-api.service << 'EOF'
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
```

#### Xray сервис
```bash
sudo tee /etc/systemd/system/xray.service << 'EOF'
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
```

### 9️⃣ Запуск сервисов

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable vpn-api
sudo systemctl enable xray
sudo systemctl enable nginx

# Запуск сервисов
sudo systemctl start vpn-api
sudo systemctl start xray
sudo systemctl start nginx

# Проверка статуса
sudo systemctl status vpn-api xray nginx
```

### 🔟 Проверка развертывания

#### Проверка API
```bash
# Проверка доступности API
curl -k https://your-domain.com/api/ || curl -k https://localhost:8000/api/

# Проверка с API ключом
curl -k -H "X-API-Key: your-api-key" https://your-domain.com/api/keys
```

#### Проверка Xray
```bash
# Проверка конфигурации
xray test -c /root/vpn-server/config/config.json

# Проверка портов
netstat -tlnp | grep -E "(443|8000|10001)"
```

#### Проверка логов
```bash
# Логи API
sudo journalctl -u vpn-api -f

# Логи Xray
sudo journalctl -u xray -f

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
```

---

## 🔧 Настройка файрвола

### UFW (Ubuntu)
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 10001:10020/tcp
sudo ufw enable
```

### iptables
```bash
# Разрешение портов
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
iptables -A INPUT -p tcp --dport 10001:10020 -j ACCEPT

# Сохранение правил
iptables-save > /etc/iptables/rules.v4
```

---

## 📊 Тестирование системы

### 1. Создание тестового ключа
```bash
curl -X POST "https://your-domain.com/api/keys" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "test@example.com"}'
```

### 2. Проверка списка ключей
```bash
curl -H "X-API-Key: your-api-key" \
  https://your-domain.com/api/keys
```

### 3. Проверка мониторинга трафика
```bash
curl -H "X-API-Key: your-api-key" \
  https://your-domain.com/api/traffic/simple
```

### 4. Проверка исторических данных
```bash
curl -H "X-API-Key: your-api-key" \
  https://your-domain.com/api/traffic/history
```

---

## 🔒 Безопасность

### Рекомендации по безопасности
1. **Измените API ключ** на уникальный
2. **Настройте файрвол** для ограничения доступа
3. **Используйте SSL сертификаты** от Let's Encrypt
4. **Регулярно обновляйте** систему и зависимости
5. **Мониторьте логи** на подозрительную активность

### Настройка fail2ban
```bash
# Установка fail2ban
sudo apt install fail2ban

# Создание конфигурации
sudo tee /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 📝 Устранение неполадок

### Частые проблемы

#### 1. API недоступен
```bash
# Проверка статуса сервиса
sudo systemctl status vpn-api

# Проверка портов
netstat -tlnp | grep 8000

# Проверка логов
sudo journalctl -u vpn-api -f
```

#### 2. Xray не запускается
```bash
# Проверка конфигурации
xray test -c /root/vpn-server/config/config.json

# Проверка прав доступа
ls -la /root/vpn-server/config/config.json

# Проверка логов
sudo journalctl -u xray -f
```

#### 3. SSL ошибки
```bash
# Проверка сертификатов
openssl x509 -in /etc/ssl/certs/vpn-api.crt -text -noout

# Проверка Nginx конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl reload nginx
```

#### 4. Проблемы с портами
```bash
# Проверка занятых портов
netstat -tlnp | grep -E "(443|8000|10001)"

# Освобождение портов
sudo fuser -k 443/tcp
sudo fuser -k 8000/tcp
```

---

## 🔄 Обновление системы

### Обновление кода
```bash
cd /root/vpn-server
git pull origin main
sudo systemctl restart vpn-api
```

### Обновление Xray
```bash
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/latest/Xray-linux-64.zip
unzip -o xray.zip
chmod +x xray
sudo systemctl restart xray
```

### Обновление зависимостей
```bash
cd /root/vpn-server
source venv/bin/activate
pip install --upgrade fastapi uvicorn pydantic
sudo systemctl restart vpn-api
```

---

## 📞 Поддержка

### Полезные команды
```bash
# Статус всех сервисов
sudo systemctl status vpn-api xray nginx

# Просмотр логов в реальном времени
sudo journalctl -f -u vpn-api

# Проверка конфигурации
xray test -c /root/vpn-server/config/config.json

# Мониторинг ресурсов
htop
df -h
free -h
```

### Контакты
- **Документация:** README.md в репозитории
- **Issues:** GitHub Issues в репозитории
- **Версия:** v2.1.1

---

## ✅ Чек-лист развертывания

- [ ] Система обновлена
- [ ] Xray установлен
- [ ] Python окружение настроено
- [ ] Конфигурация создана
- [ ] SSL сертификаты настроены
- [ ] Nginx настроен
- [ ] Systemd сервисы созданы
- [ ] Сервисы запущены
- [ ] Файрвол настроен
- [ ] API протестирован
- [ ] Безопасность настроена

**Статус развертывания:** ✅ Готово к использованию 