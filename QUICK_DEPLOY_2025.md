# ⚡ Быстрое развертывание VPN сервера (2025)

**Версия:** 2.3.0 | **Xray:** v25.10.15 | **Время:** ~15 минут

---

## 🚀 **Автоматический скрипт развертывания**

### **1. Скачивание и запуск скрипта**
```bash
# Скачивание скрипта развертывания
curl -O https://raw.githubusercontent.com/your-repo/vpn-server/main/deploy.sh
chmod +x deploy.sh

# Запуск автоматического развертывания
sudo ./deploy.sh
```

### **2. Ручное развертывание (если скрипт недоступен)**

#### **Шаг 1: Подготовка системы**
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y curl wget git python3 python3-pip python3-venv nginx unzip openssl sqlite3
```
**Примечание:** `sqlite3` необходим для проверки целостности базы данных. Python модуль `sqlite3` входит в стандартную библиотеку Python 3.

#### **Шаг 2: Установка Xray v25.10.15**
```bash
# Скачивание и установка Xray
cd /tmp
ARCH=$(uname -m | sed 's/x86_64/64/; s/aarch64/arm64-v8a/; s/armv7l/arm32-v7a/')
wget "https://github.com/XTLS/Xray-core/releases/download/v25.10.15/Xray-linux-$ARCH.zip"
unzip "Xray-linux-$ARCH.zip"
sudo cp xray /usr/local/bin/ && sudo chmod +x /usr/local/bin/xray
```

#### **Шаг 3: Настройка проекта**
```bash
# Создание директории
sudo mkdir -p /root/vpn-server
cd /root/vpn-server

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install fastapi==0.116.1 uvicorn[standard]==0.35.0 pydantic==2.11.7 python-multipart==0.0.20 requests==2.32.4 psutil==5.9.6
```

#### **Шаг 4: Копирование файлов**
```bash
# Копирование всех файлов проекта в /root/vpn-server/
# (api.py, port_manager.py, xray_config_manager.py, и т.д.)
```

#### **Шаг 5: Настройка конфигурации**
```bash
# Создание .env файла
cat > .env << 'EOF'
VPN_API_KEY=your-secret-api-key-here
VPN_ENABLE_HTTPS=true
VPN_SSL_CERT_PATH=/etc/ssl/certs/vpn-api.crt
VPN_SSL_KEY_PATH=/etc/ssl/private/vpn-api.key
VPN_HOST=0.0.0.0
VPN_PORT=8000
EOF

# Генерация SSL сертификатов
sudo mkdir -p /etc/ssl/certs /etc/ssl/private
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/vpn-api.key \
    -out /etc/ssl/certs/vpn-api.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Генерация Reality ключей
/usr/local/bin/xray x25519 > reality_keys.txt
PRIVATE_KEY=$(cat reality_keys.txt | grep "Private key:" | cut -d' ' -f3)
SHORT_ID=$(openssl rand -hex 8)
```

#### **Шаг 6: Создание конфигурации Xray**
```bash
# Создание config.json
mkdir -p config
cat > config/config.json << EOF
{
  "log": {"loglevel": "info"},
  "inbounds": [{
    "listen": "0.0.0.0",
    "port": 443,
    "protocol": "vless",
    "settings": {"clients": [], "decryption": "none"},
    "streamSettings": {
      "network": "tcp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "dest": "www.microsoft.com:443",
        "serverNames": ["www.microsoft.com"],
        "privateKey": "$PRIVATE_KEY",
        "shortIds": ["$SHORT_ID"]
      }
    }
  }],
  "outbounds": [{"protocol": "freedom", "settings": {}}]
}
EOF

# Инициализация директорий (SQLite создаст базу автоматически)
mkdir -p logs data config/backups

# Важно: Файл data/vpn.db будет создан автоматически при первом запуске API
# SQLite является единственным хранилищем данных (ключи, порты, история трафика)
# Если есть старые JSON-файлы (keys.json, ports.json, traffic_history.json), 
# они будут автоматически импортированы в SQLite при первом запуске API
# Для проверки целостности базы используйте: scripts/check_db_integrity.sh

#### **Шаг 6.1: Настройка пользователя службы**
```bash
sudo ./scripts/setup_vpn_api_user.sh
```
```

#### **Шаг 7: Создание systemd сервисов**
```bash
# Xray сервис
sudo tee /etc/systemd/system/xray.service > /dev/null << 'EOF'
[Unit]
Description=Xray Service
After=network.target
[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/xray run -config /root/vpn-server/config/config.json
Restart=always
[Install]
WantedBy=multi-user.target
EOF

# VPN API сервис
sudo tee /etc/systemd/system/vpn-api.service > /dev/null << 'EOF'
[Unit]
Description=VPN Key Management API
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=vpnapi
Group=vpnapi
WorkingDirectory=/root/vpn-server
Environment=PATH=/root/vpn-server/venv/bin
EnvironmentFile=/root/vpn-server/.env
ExecStart=/root/vpn-server/venv/bin/python /root/vpn-server/api.py
Restart=always
RestartSec=5
LimitNOFILE=65535
MemoryMax=512M
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictNamespaces=yes
RestrictRealtime=yes
LockPersonality=yes
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
ReadWritePaths=/root/vpn-server /var/log /run

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable xray vpn-api
```

#### **Шаг 8: Запуск сервисов**
```bash
# Запуск сервисов
sudo systemctl start xray vpn-api

# Проверка статуса
sudo systemctl status xray vpn-api

# Проверка health check
curl -k https://localhost:8000/health
```

---

## 🔐 **Настройка прав доступа**

**Важно:** Скрипт `deploy_auto.sh` автоматически устанавливает правильные права. Если права были изменены, выполните:

```bash
sudo bash /root/vpn-server/scripts/fix_permissions.sh
```

**Требуемые права:**
- `logs/` → `root:root` (755) - Xray пишет от root
- `config/config.json` → `root:vpnapi` (664) - API изменяет конфигурацию
- `config/` → `root:vpnapi` (775) - API создает файлы
- `data/vpn.db` → `vpnapi:vpnapi` (660) - API читает/пишет БД

---

## ✅ **Проверка установки**

### **Тестирование API**
```bash
# Проверка health check
curl -k https://localhost:8000/health

# Создание тестового ключа
curl -k -X POST -H "Content-Type: application/json" \
     -H "X-API-Key: your-secret-api-key-here" \
     -d '{"name": "test@example.com"}' \
     https://localhost:8000/api/keys

# Получение списка ключей
curl -k -H "X-API-Key: your-secret-api-key-here" \
     https://localhost:8000/api/keys
```

### **Проверка портов**
```bash
# Проверка открытых портов
sudo netstat -tlnp | grep -E ":443|:8000"

# Проверка логов
sudo journalctl -u xray -f
sudo journalctl -u vpn-api -f
```

---

## 🔧 **Настройка файрвола**

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

---

## 📱 **Конфигурация клиентов**

### **Получение конфигурации клиента**
```bash
# Получение конфигурации для ключа
curl -k -H "X-API-Key: your-secret-api-key-here" \
     https://localhost:8000/api/keys/KEY_ID/config
```

### **Поддерживаемые клиенты:**
- **Android:** v2rayNG, SagerNet
- **iOS:** Shadowrocket, OneClick
- **Windows:** v2rayN, Clash
- **macOS:** ClashX, V2rayU
- **Linux:** v2ray-core, Clash

---

## 🚨 **Устранение неполадок**

### **Xray не запускается**
```bash
# Проверка конфигурации
/usr/local/bin/xray run -test -c /root/vpn-server/config/config.json

# Проверка логов
sudo journalctl -u xray -f
```

### **API не отвечает**
```bash
# Проверка статуса
sudo systemctl status vpn-api

# Проверка логов
sudo journalctl -u vpn-api -f

# Проверка переменных окружения
cat /root/vpn-server/.env
```

---

## 🎯 **Готово!**

После выполнения всех шагов у вас будет:
- ✅ VPN сервер с Xray v25.10.15
- ✅ RESTful API для управления
- ✅ HTTPS поддержка
- ✅ Health check мониторинг
- ✅ Автоматическое управление портами

**Время развертывания:** ~15 минут  
**Поддержка:** до 20 ключей

**Удачного использования! 🚀**
