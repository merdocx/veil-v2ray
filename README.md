# VPN Key Management Server

Сервер для управления VPN ключами с поддержкой VLESS+Reality протокола, индивидуальных портов и мониторинга трафика.

## 🚀 Возможности

- ✅ **Управление ключами** - создание, удаление, просмотр VPN ключей
- 🔐 **VLESS+Reality** - современный протокол для обхода блокировок
- 🔌 **Индивидуальные порты** - каждый ключ получает уникальный порт (10001-10020)
- 📊 **Мониторинг трафика** - отслеживание трафика в реальном времени
- 📈 **Исторические данные** - накопление и анализ трафика с момента создания ключей
- 🔧 **API управление** - RESTful API для всех операций
- 🛡️ **Безопасность** - API ключ аутентификация, HTTPS

## 📦 Установка

### Требования
- Python 3.8+
- Xray-core v25.10.15+
- Nginx (для HTTPS)
- systemd

### ⚡ Быстрая установка (рекомендуется)
```bash
# Автоматическое развертывание
curl -O https://raw.githubusercontent.com/your-repo/vpn-server/main/deploy_auto.sh
chmod +x deploy_auto.sh
sudo ./deploy_auto.sh
```

### 📖 Ручная установка
```bash
# Клонирование репозитория
git clone <repository-url>
cd vpn-server

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл

# Запуск сервисов
sudo systemctl enable vpn-api
sudo systemctl start vpn-api
sudo systemctl enable xray
sudo systemctl start xray
```

**📚 Подробные инструкции:** [DEPLOYMENT_GUIDE_2025.md](DEPLOYMENT_GUIDE_2025.md)

## 🔧 Конфигурация

### Переменные окружения (.env)
```bash
VPN_API_KEY=your-secret-api-key
VPN_HOST=0.0.0.0
VPN_PORT=8000
VPN_ENABLE_HTTPS=true
VPN_SSL_CERT_PATH=/etc/ssl/certs/vpn-api.crt
VPN_SSL_KEY_PATH=/etc/ssl/private/vpn-api.key
```

### Xray конфигурация
Основная конфигурация находится в `config/config.json` и автоматически обновляется при создании/удалении ключей.

## 📊 API Endpoints

### Управление ключами
- `POST /api/keys` - Создание ключа
- `GET /api/keys` - Список ключей
- `GET /api/keys/{id}` - Информация о ключе
- `GET /api/keys/{id}/config` - Конфигурация клиента
- `DELETE /api/keys/{id}` - Удаление ключа

### Мониторинг трафика
- `GET /api/traffic/simple` - Текущий трафик всех портов
- `GET /api/keys/{id}/traffic/simple` - Трафик конкретного ключа
- `POST /api/keys/{id}/traffic/simple/reset` - Сброс статистики

### Исторические данные
- `GET /api/traffic/history` - Общий объем трафика с момента создания
- `GET /api/keys/{id}/traffic/history` - История трафика ключа
- `GET /api/traffic/daily/{date}` - Ежедневная статистика
- `POST /api/keys/{id}/traffic/history/reset` - Сброс истории
- `POST /api/traffic/history/cleanup` - Очистка старых данных

### Месячная статистика
- `GET /api/traffic/monthly` - Месячная статистика всех ключей
- `GET /api/keys/{id}/traffic/monthly` - Месячная статистика ключа

### Системные
- `GET /health` - Health check (мониторинг состояния)
- `GET /api/system/ports` - Статус портов
- `POST /api/system/sync-config` - Синхронизация конфигурации
- `GET /api/system/config-status` - Статус конфигурации

## 📈 Мониторинг трафика

### Текущий трафик
Система отслеживает трафик в реальном времени на основе активных соединений:
- Количество соединений
- Общий объем трафика
- Входящий/исходящий трафик
- Скорость передачи данных

### Исторические данные
Новая система накопления данных позволяет:
- Отслеживать общий объем трафика с момента создания ключа
- Анализировать ежедневную статистику
- Просматривать активность по дням
- Получать детальную информацию о сессиях

**Пример получения исторических данных:**
```bash
# Общий объем трафика всех ключей
curl -H "X-API-Key: your-key" https://server:8000/api/traffic/history

# История конкретного ключа
curl -H "X-API-Key: your-key" https://server:8000/api/keys/key-id/traffic/history

# Ежедневная статистика
curl -H "X-API-Key: your-key" https://server:8000/api/traffic/daily/2025-08-05
```

## 🔌 Управление портами

Система автоматически назначает порты из диапазона 10001-10020:
- Каждый ключ получает уникальный порт
- Максимум 20 активных ключей
- Автоматическое освобождение при удалении ключа

## 🛠️ Управление сервисами

```bash
# VPN API сервис
sudo systemctl status vpn-api
sudo systemctl restart vpn-api
sudo systemctl stop vpn-api

# Xray сервис
sudo systemctl status xray
sudo systemctl restart xray
sudo systemctl stop xray

# Просмотр логов
sudo journalctl -u vpn-api -f
sudo journalctl -u xray -f
```

## 📁 Структура проекта

```
vpn-server/
├── api.py                      # Основной API сервер
├── port_manager.py             # Управление портами
├── xray_config_manager.py      # Управление конфигурацией Xray
├── simple_traffic_monitor.py   # Мониторинг трафика
├── traffic_history_manager.py  # Исторические данные трафика
├── generate_client_config.py   # Генерация клиентских конфигураций
├── config/
│   ├── config.json            # Конфигурация Xray
│   ├── keys.json              # База ключей
│   ├── ports.json             # Назначения портов
│   └── traffic_history.json   # Исторические данные трафика
├── requirements.txt           # Python зависимости
├── .env                      # Переменные окружения
└── README.md                 # Документация
```

## 🔒 Безопасность

- **API ключ аутентификация** - все запросы требуют валидный API ключ
- **HTTPS поддержка** - шифрование всех соединений
- **Изоляция портов** - каждый ключ на отдельном порту
- **Валидация данных** - проверка всех входных данных

## 📊 Мониторинг и логирование

### Логи сервисов
```bash
# VPN API логи
sudo journalctl -u vpn-api -f

# Xray логи
sudo journalctl -u xray -f

# Системные логи
sudo journalctl -f
```

### Файлы данных
- `config/keys.json` - база VPN ключей
- `config/ports.json` - назначения портов
- `config/traffic_history.json` - исторические данные трафика
- `config/config.json` - конфигурация Xray

## 🚨 Устранение неполадок

### Проблемы с API
1. Проверьте статус сервиса: `systemctl status vpn-api`
2. Проверьте логи: `journalctl -u vpn-api -f`
3. Убедитесь в правильности API ключа
4. Проверьте доступность порта 8000

### Проблемы с Xray
1. Проверьте статус: `systemctl status xray`
2. Проверьте конфигурацию: `xray test -c config/config.json`
3. Проверьте логи: `journalctl -u xray -f`

### Проблемы с портами
1. Проверьте назначения: `curl -H "X-API-Key: key" https://server:8000/api/system/ports`
2. Синхронизируйте конфигурацию: `curl -X POST -H "X-API-Key: key" https://server:8000/api/system/sync-config`

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сервисов
2. Убедитесь в корректности конфигурации
3. Проверьте доступность всех зависимостей
4. Обратитесь к документации API

## 📝 Лицензия

Проект распространяется под лицензией MIT.

---

**Версия:** 2.1.4  
**Дата обновления:** 22 октября 2025  
**Статус:** ✅ Актуально (обновлен Xray до v25.10.15, добавлен health check, оптимизирована структура) 