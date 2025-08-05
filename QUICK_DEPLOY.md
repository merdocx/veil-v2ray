# ⚡ Быстрое развертывание VPN сервера

**Версия:** 2.1.1  
**Время развертывания:** ~10-15 минут

---

## 🚀 Автоматическое развертывание (рекомендуется)

### 1. Подготовка сервера
```bash
# Подключитесь к серверу с правами root
ssh root@your-server-ip

# Обновите систему
apt update && apt upgrade -y
```

### 2. Скачивание и запуск скрипта
```bash
# Скачивание скрипта развертывания
wget https://raw.githubusercontent.com/merdocx/veil-v2ray/main/deploy.sh
chmod +x deploy.sh

# Запуск автоматического развертывания
./deploy.sh
```

### 3. Проверка развертывания
```bash
# Проверка статуса сервисов
systemctl status vpn-api xray nginx

# Проверка API
curl -k https://localhost:8000/api/

# Получение API ключа
cat /root/vpn-server/.env | grep VPN_API_KEY
```

---

## 🔧 Ручное развертывание

### Минимальные команды
```bash
# 1. Клонирование проекта
cd /root
git clone https://github.com/merdocx/veil-v2ray.git vpn-server
cd vpn-server

# 2. Установка Xray
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-linux-64.zip
unzip -o xray.zip && chmod +x xray && rm xray.zip

# 3. Настройка Python
cd /root/vpn-server
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn[standard] pydantic python-multipart

# 4. Создание конфигурации
python3 generate_api_key.py
cp config/config.example.json config/config.json

# 5. Запуск сервисов
systemctl enable vpn-api xray
systemctl start vpn-api xray
```

---

## 📋 Требования

### Системные требования
- **ОС:** Ubuntu 20.04+ / Debian 11+
- **RAM:** 2GB+
- **CPU:** 2 ядра+
- **Диск:** 20GB+
- **Сеть:** Статический IP

### Открытые порты
- **22** - SSH
- **80** - HTTP (для SSL)
- **443** - HTTPS
- **8000** - API
- **10001-10020** - VPN ключи

---

## 🔒 Настройка безопасности

### 1. Изменение API ключа
```bash
# Редактирование .env файла
nano /root/vpn-server/.env

# Измените VPN_API_KEY на уникальный ключ
```

### 2. Настройка SSL для домена
```bash
# Если есть домен
certbot --nginx -d your-domain.com
```

### 3. Настройка файрвола
```bash
# UFW
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw allow 10001:10020/tcp
ufw enable
```

---

## 📊 Тестирование

### Проверка API
```bash
# Создание ключа
curl -X POST "https://your-server:8000/api/keys" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "test@example.com"}'

# Список ключей
curl -H "X-API-Key: your-api-key" \
  https://your-server:8000/api/keys

# Мониторинг трафика
curl -H "X-API-Key: your-api-key" \
  https://your-server:8000/api/traffic/simple
```

### Проверка VPN
```bash
# Получение конфигурации ключа
curl -H "X-API-Key: your-api-key" \
  https://your-server:8000/api/keys/key-id/config
```

---

## 🛠️ Управление

### Полезные команды
```bash
# Статус сервисов
systemctl status vpn-api xray nginx

# Логи в реальном времени
journalctl -f -u vpn-api
journalctl -f -u xray

# Перезапуск сервисов
systemctl restart vpn-api
systemctl restart xray

# Обновление проекта
cd /root/vpn-server
git pull origin main
systemctl restart vpn-api
```

### Мониторинг ресурсов
```bash
# Системные ресурсы
htop
df -h
free -h

# Сетевые соединения
netstat -tlnp | grep -E "(443|8000|10001)"
ss -tlnp | grep -E "(443|8000|10001)"
```

---

## 📞 Поддержка

### Документация
- **Полное руководство:** `DEPLOYMENT_GUIDE.md`
- **API документация:** `API_DOCUMENTATION.md`
- **README:** `README.md`

### Полезные ссылки
- **GitHub репозиторий:** https://github.com/merdocx/veil-v2ray
- **Последняя версия:** v2.1.1

### Устранение неполадок
```bash
# Проверка логов
journalctl -u vpn-api -n 50
journalctl -u xray -n 50

# Проверка конфигурации
xray test -c /root/vpn-server/config/config.json

# Проверка портов
netstat -tlnp | grep -E "(443|8000|10001)"
```

---

## ✅ Чек-лист развертывания

- [ ] Сервер подготовлен (Ubuntu/Debian)
- [ ] Скрипт развертывания запущен
- [ ] Все сервисы работают (vpn-api, xray, nginx)
- [ ] API доступен по HTTPS
- [ ] API ключ изменен на уникальный
- [ ] Файрвол настроен
- [ ] SSL сертификаты настроены (опционально)
- [ ] Тестовый ключ создан
- [ ] VPN подключение работает

**Статус:** ✅ Готово к использованию 