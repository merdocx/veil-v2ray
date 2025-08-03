# Veil V2Ray - VPN Server с VLESS+Reality

Современный VPN сервер на базе Xray-core с протоколом VLESS+Reality и REST API для управления ключами доступа.

## 🌟 Особенности

- **VLESS+Reality** - современный протокол обфускации трафика
- **REST API** - полное управление ключами через HTTP
- **Автоматический перезапуск** - Xray перезапускается после изменений
- **Генерация конфигураций** - автоматическое создание VLESS ссылок
- **Systemd интеграция** - автозапуск и управление сервисами
- **Nginx прокси** - обратный прокси для API

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/merdocx/veil-v2ray.git
cd veil-v2ray
```

### 2. Установка зависимостей
```bash
# Обновление системы
apt update && apt install -y curl wget unzip python3 python3-pip python3-venv nginx

# Установка Xray
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/v1.8.7/Xray-linux-64.zip
unzip xray.zip && chmod +x xray && rm xray.zip
```

### 3. Настройка конфигурации
```bash
cd /root/vpn-server

# Генерация ключей Reality
./generate_keys.sh

# Настройка конфигурации
cp config/config.example.json config/config.json
cp config/keys.example.env config/keys.env

# Обновите config/config.json с вашими ключами
```

### 4. Установка Python зависимостей
```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-multipart
```

### 5. Настройка сервисов
```bash
# Копирование systemd сервисов
cp systemd/xray.service /etc/systemd/system/
cp systemd/vpn-api.service /etc/systemd/system/

# Настройка Nginx
cp nginx/vpn-api /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/vpn-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Запуск сервисов
systemctl daemon-reload
systemctl enable xray vpn-api nginx
systemctl start xray vpn-api nginx
```

## 📖 Использование

### API Endpoints

- `POST /api/keys` - Создание ключа
- `GET /api/keys` - Список ключей
- `GET /api/keys/{id}` - Информация о ключе
- `GET /api/keys/{id}/config` - Конфигурация клиента
- `DELETE /api/keys/{id}` - Удаление ключа

### Скрипт управления
```bash
./manage.sh status          # Статус сервисов
./manage.sh create-key "Имя" # Создание ключа
./manage.sh list-keys       # Список ключей
./manage.sh get-config <id> # Конфигурация клиента
./manage.sh delete-key <id> # Удаление ключа
./manage.sh stats           # Статистика
./manage.sh logs xray       # Логи Xray
```

### Примеры API запросов
```bash
# Создание ключа
curl -X POST http://your-domain.com/api/keys \
  -H "Content-Type: application/json" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  -d '{"name": "My VPN Key"}'

# Список ключей
curl -X GET http://your-domain.com/api/keys \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

# Получение конфигурации
curl -X GET http://your-domain.com/api/keys/{key_id}/config \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

## 🔐 Аутентификация

API защищен аутентификацией через API ключ. См. файл `SECURITY.md` для подробной информации о безопасности.

**API ключ:** `QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=`

## 🔧 Конфигурация

### Основные параметры
- **Порт**: 443 (HTTPS)
- **Протокол**: VLESS+Reality
- **SNI**: www.microsoft.com
- **Fingerprint**: Chrome

### Поддерживаемые клиенты
- **Android**: V2rayNG, SagerNet
- **iOS**: Shadowrocket, Quantumult X
- **Windows**: V2rayN, Clash
- **macOS**: V2rayX, ClashX
- **Linux**: V2ray, Clash

## 📁 Структура проекта

```
veil-v2ray/
├── config/                    # Конфигурационные файлы
│   ├── config.example.json    # Пример конфигурации Xray
│   └── keys.example.env       # Пример ключей
├── systemd/                   # Systemd сервисы
│   ├── xray.service          # Сервис Xray
│   └── vpn-api.service       # Сервис API
├── nginx/                     # Конфигурация Nginx
│   └── vpn-api               # Виртуальный хост
├── api.py                     # Основной API файл
├── manage.sh                  # Скрипт управления
├── generate_keys.sh           # Генерация ключей
├── generate_client_config.py  # Генерация конфигурации клиента
├── restart_xray.sh           # Перезапуск Xray
├── README.md                 # Документация
└── .gitignore               # Исключения Git
```

## 🔒 Безопасность

- Reality протокол обеспечивает обфускацию трафика
- Автоматическая генерация UUID ключей
- Изоляция API через Nginx
- Логирование всех операций
- Systemd сервисы с автозапуском

## 📊 Мониторинг

```bash
# Статус сервисов
systemctl status xray vpn-api nginx

# Логи в реальном времени
journalctl -u xray -f
journalctl -u vpn-api -f

# Статистика
./manage.sh stats
```

## 📊 Точный мониторинг трафика

Система предоставляет точную статистику использования VPN для каждого ключа через Xray API:

### API эндпоинты:

- `GET /api/traffic/exact` - точная статистика трафика всех ключей
- `GET /api/keys/{key_id}/traffic/exact` - точная статистика конкретного ключа
- `GET /api/traffic/status` - статус системы мониторинга
- `POST /api/keys/{key_id}/traffic/reset` - сброс статистики ключа

### Команды управления:

```bash
# Точная статистика трафика
./manage.sh traffic

# Точная статистика конкретного ключа
./manage.sh traffic-key <key_id>

# Статус системы мониторинга
./manage.sh traffic-status
```

### Преимущества:

- **Точность 95%+**: реальные байты вместо приближений
- **Реальное время**: мгновенное обновление данных
- **Детальная статистика**: разделение uplink/downlink
- **Управление**: возможность сброса статистики
- **Надежность**: прямое подключение к Xray API

## 🛠️ Обновление

### Обновление Xray
```bash
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/latest/Xray-linux-64.zip
unzip -o xray.zip && chmod +x xray && systemctl restart xray
```

### Обновление API
```bash
cd /root/vpn-server
source venv/bin/activate
pip install --upgrade fastapi uvicorn
systemctl restart vpn-api
```

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `./manage.sh logs xray`
2. Проверьте статус: `./manage.sh status`
3. Создайте Issue в GitHub

---

**Veil V2Ray** - современное решение для VPN серверов с полной автоматизацией управления ключами. 