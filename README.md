# VPN Server с VLESS+Reality

Этот проект представляет собой VPN сервер на базе Xray-core с протоколом VLESS+Reality и API для управления ключами доступа.

## Компоненты

- **Xray-core** - основной VPN сервер с поддержкой VLESS+Reality
- **FastAPI** - REST API для управления ключами
- **Nginx** - обратный прокси для API
- **Systemd** - управление сервисами

## Структура проекта

```
/root/vpn-server/
├── config/
│   ├── config.json          # Конфигурация Xray
│   ├── keys.env             # Ключи Reality
│   └── keys.json            # База данных ключей
├── logs/                    # Логи Xray
├── venv/                    # Python виртуальное окружение
├── api.py                   # Основной API файл
├── generate_keys.sh         # Скрипт генерации ключей
├── generate_client_config.py # Скрипт генерации конфигурации клиента
└── README.md               # Этот файл
```

## API Endpoints

### Управление ключами

#### Создание ключа
```bash
POST /api/keys
Content-Type: application/json
X-API-Key: YOUR_API_KEY

{
    "name": "Имя ключа"
}
```

#### Получение списка ключей
```bash
GET /api/keys
X-API-Key: YOUR_API_KEY
```

#### Получение информации о ключе
```bash
GET /api/keys/{key_id}
X-API-Key: YOUR_API_KEY
```

#### Получение конфигурации клиента
```bash
GET /api/keys/{key_id}/config
X-API-Key: YOUR_API_KEY
```

#### Удаление ключа
```bash
DELETE /api/keys/{key_id}
X-API-Key: YOUR_API_KEY
```

### Мониторинг трафика

#### Получение трафика для всех ключей
```bash
GET /api/traffic/simple
X-API-Key: YOUR_API_KEY
```

#### Получение трафика для конкретного ключа
```bash
GET /api/keys/{key_id}/traffic/simple
X-API-Key: YOUR_API_KEY
```

#### Сброс статистики трафика для ключа
```bash
POST /api/keys/{key_id}/traffic/simple/reset
X-API-Key: YOUR_API_KEY
```

### Системные endpoints

#### Статус системы
```bash
GET /api/system/ports
X-API-Key: YOUR_API_KEY
```

#### Синхронизация конфигурации Xray
```bash
POST /api/system/xray/sync-config
X-API-Key: YOUR_API_KEY
```

## Документация API

Документация доступна по адресу: `https://veil-bird.ru/docs`

## Управление сервисами

### Статус сервисов
```bash
systemctl status xray vpn-api nginx
```

### Перезапуск сервисов
```bash
systemctl restart xray
systemctl restart vpn-api
systemctl reload nginx
```

### Просмотр логов
```bash
journalctl -u xray -f
journalctl -u vpn-api -f
```

## Конфигурация клиента

Для подключения к VPN используйте следующие параметры:

- **Протокол**: VLESS
- **Сервер**: veil-bird.ru
- **Порт**: 443
- **Безопасность**: Reality
- **SNI**: www.microsoft.com
- **Fingerprint**: Chrome

Конфигурация генерируется автоматически через API endpoint `/api/keys/{key_id}/config`

## Безопасность

- **HTTPS обязателен** - все соединения шифруются через SSL
- **API ключ в переменных окружения** - не хардкодирован в коде
- **Reality протокол** обеспечивает обфускацию трафика
- **Автоматическая ротация ключей** через скрипт
- **Security headers** защищают от атак
- **Безопасные права доступа** на все файлы

### 🔑 Управление API ключом
```bash
# Генерация нового API ключа
python3 /root/vpn-server/generate_api_key.py

# Проверка безопасности
python3 /root/vpn-server/security_check.py
```

## Мониторинг

### Логи сервисов
Логи сервисов доступны в:
- Xray: `/root/vpn-server/logs/`
- API: `journalctl -u vpn-api`
- Nginx: `/var/log/nginx/`

### Мониторинг трафика
Система мониторинга трафика основана на активных соединениях и интерфейсном трафике:

#### Методы мониторинга
- **Простой мониторинг** (`/api/traffic/simple`) - основан на подсчете активных соединений и оценке трафика
- **Поддерживаемые состояния соединений**: ESTAB, LAST-ACK, CLOSE-WAIT
- **Кэширование**: 30 секунд для оптимизации производительности

#### Примеры использования
```bash
# Получение трафика для всех ключей
curl -k -X GET "https://veil-bird.ru/api/traffic/simple" \
  -H "X-API-Key: YOUR_API_KEY"

# Получение трафика для конкретного ключа
curl -k -X GET "https://veil-bird.ru/api/keys/{key_id}/traffic/simple" \
  -H "X-API-Key: YOUR_API_KEY"

# Сброс статистики трафика
curl -k -X POST "https://veil-bird.ru/api/keys/{key_id}/traffic/simple/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Формат ответа
```json
{
  "status": "success",
  "key": {...},
  "traffic": {
    "port": 10001,
    "connections": 111,
    "total_bytes": 33323549,
    "rx_bytes": 16661774,
    "tx_bytes": 16661774,
    "total_formatted": "31.78 MB",
    "rx_formatted": "15.89 MB",
    "tx_formatted": "15.89 MB",
    "traffic_rate": 134128.74,
    "connection_details": [...],
    "timestamp": 1754307423.1131258,
    "source": "simple_monitor",
    "method": "connection_based_estimation"
  }
}
```

## Обновление

Для обновления Xray:
```bash
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/latest/Xray-linux-64.zip
unzip -o xray.zip
chmod +x xray
systemctl restart xray
```

## Поддержка

При возникновении проблем проверьте:
1. Статус сервисов: `systemctl status xray vpn-api nginx`
2. Логи: `journalctl -u xray -f`
3. Конфигурацию: `/root/vpn-server/config/config.json`
4. Сетевые порты: `netstat -tlnp | grep :443` 