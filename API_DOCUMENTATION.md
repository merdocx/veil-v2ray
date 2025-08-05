# VPN Key Management API - Документация

## Версия API: 2.1.3

### Обзор
API для управления VPN ключами с поддержкой VLESS+Reality протокола, индивидуальных портов и мониторинга трафика.

### Базовый URL
```
https://your-server:8000
```

### Аутентификация
Все запросы требуют API ключ в заголовке `X-API-Key`.

---

## 🔑 Управление ключами

### Создание ключа
**POST** `/api/keys`

Создает новый VPN ключ с индивидуальным портом.

**Тело запроса:**
```json
{
    "name": "user@example.com"
}
```

**Ответ:**
```json
{
    "id": "uuid-key-id",
    "name": "user@example.com",
    "uuid": "vless-uuid",
    "created_at": "2025-08-05T12:00:00.000000",
    "is_active": true,
    "port": 10001
}
```

**Пример:**
```bash
curl -X POST "https://localhost:8000/api/keys" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"name": "user@example.com"}'
```

### Получение списка ключей
**GET** `/api/keys`

Возвращает список всех VPN ключей.

**Ответ:**
```json
[
    {
        "id": "uuid-key-id",
        "name": "user@example.com",
        "uuid": "vless-uuid",
        "created_at": "2025-08-05T12:00:00.000000",
        "is_active": true,
        "port": 10001
    }
]
```

### Получение конкретного ключа
**GET** `/api/keys/{key_id}`

Возвращает информацию о конкретном ключе.

### Получение конфигурации ключа
**GET** `/api/keys/{key_id}/config`

Возвращает VLESS URL и QR код для клиентской конфигурации.

**Ответ:**
```json
{
    "key": {
        "id": "uuid-key-id",
        "name": "user@example.com",
        "uuid": "vless-uuid",
        "created_at": "2025-08-05T12:00:00.000000",
        "is_active": true,
        "port": 10001
    },
    "vless_url": "vless://uuid@server:port?security=reality&sni=example.com&fp=chrome&pbk=public-key&sid=session-id&type=tcp&flow=xtls-rprx-vision#user@example.com",
    "qr_code_data": "vless://uuid@server:port?security=reality&sni=example.com&fp=chrome&pbk=public-key&sid=session-id&type=tcp&flow=xtls-rprx-vision#user@example.com"
}
```

### Удаление ключа
**DELETE** `/api/keys/{key_id}`

Удаляет VPN ключ и освобождает порт.

**Ответ:**
```json
{
    "message": "Key deleted successfully"
}
```

---

## 📊 Мониторинг трафика

### Простой мониторинг трафика
**GET** `/api/traffic/simple`

Возвращает текущий трафик для всех портов.

**Ответ:**
```json
{
    "status": "success",
    "data": {
        "ports": {
            "10001": {
                "port": 10001,
                "connections": 5,
                "total_bytes": 1024,
                "rx_bytes": 512,
                "tx_bytes": 512,
                "total_formatted": "1.00 KB",
                "rx_formatted": "512 B",
                "tx_formatted": "512 B",
                "traffic_rate": 1024.5,
                "uuid": "key-uuid"
            }
        },
        "total_connections": 5,
        "total_bytes": 1024,
        "timestamp": 1754395154.0027776
    },
    "timestamp": "2025-08-05T14:59:14.026283"
}
```

### Трафик конкретного ключа
**GET** `/api/keys/{key_id}/traffic/simple`

Возвращает текущий трафик для конкретного ключа.

### Сброс статистики трафика
**POST** `/api/keys/{key_id}/traffic/simple/reset`

Сбрасывает статистику трафика для ключа.

---

## 📈 Исторические данные о трафике

### Общая история трафика
**GET** `/api/traffic/history`

Возвращает общий объем трафика для всех ключей с момента их создания.

**Ответ:**
```json
{
    "status": "success",
    "data": {
        "total_keys": 2,
        "active_keys": 1,
        "total_traffic_bytes": 198,
        "total_rx_bytes": 99,
        "total_tx_bytes": 99,
        "keys": [
            {
                "key_uuid": "dc41f2d0-7741-43d2-b0c4-193cd8dd16ce",
                "key_name": "zhdanov@gmail.com",
                "port": 10002,
                "created_at": "2025-08-05T16:06:36.865147",
                "last_activity": "2025-08-05T16:06:47.590883",
                "is_active": true,
                "total_traffic": {
                    "total_bytes": 198,
                    "rx_bytes": 99,
                    "tx_bytes": 99,
                    "total_connections": 35,
                    "total_formatted": "198 B",
                    "rx_formatted": "99 B",
                    "tx_formatted": "99 B"
                }
            }
        ],
        "total_traffic_formatted": "198 B",
        "total_rx_formatted": "99 B",
        "total_tx_formatted": "99 B"
    },
    "timestamp": "2025-08-05T16:06:36.865907"
}
```

### История трафика ключа
**GET** `/api/keys/{key_id}/traffic/history`

Возвращает общий объем трафика для конкретного ключа с момента создания.

**Ответ:**
```json
{
    "status": "success",
    "data": {
        "key_uuid": "dc41f2d0-7741-43d2-b0c4-193cd8dd16ce",
        "key_name": "zhdanov@gmail.com",
        "port": 10002,
        "created_at": "2025-08-05T16:06:36.865147",
        "last_activity": "2025-08-05T16:06:47.590883",
        "is_active": true,
        "total_traffic": {
            "total_bytes": 198,
            "rx_bytes": 99,
            "tx_bytes": 99,
            "total_connections": 35,
            "total_formatted": "198 B",
            "rx_formatted": "99 B",
            "tx_formatted": "99 B"
        },
        "daily_stats": {
            "2025-08-05": {
                "total_bytes": 198,
                "rx_bytes": 99,
                "tx_bytes": 99,
                "max_connections": 35,
                "sessions": 2
            }
        }
    },
    "timestamp": "2025-08-05T16:06:47.593730"
}
```

### Ежедневная статистика
**GET** `/api/traffic/daily/{date}`

Возвращает ежедневную статистику трафика (формат даты: YYYY-MM-DD).

**Ответ:**
```json
{
    "status": "success",
    "data": {
        "date": "2025-08-05",
        "total_bytes": 396,
        "total_connections": 35,
        "active_keys": 0,
        "total_sessions": 2,
        "total_formatted": "396 B"
    },
    "timestamp": "2025-08-05T16:06:51.354243"
}
```

### Сброс истории трафика ключа
**POST** `/api/keys/{key_id}/traffic/history/reset`

Сбрасывает историю трафика для конкретного ключа.

**Ответ:**
```json
{
    "status": "success",
    "message": "Traffic history reset successfully",
    "key_id": "key-id",
    "timestamp": "2025-08-05T16:06:51.354243"
}
```

### Очистка старых данных
**POST** `/api/traffic/history/cleanup?days_to_keep=30`

Очищает старые данные истории трафика (по умолчанию 30 дней).

**Ответ:**
```json
{
    "status": "success",
    "message": "Cleaned up traffic history older than 30 days",
    "days_kept": 30,
    "timestamp": "2025-08-05T16:06:51.354243"
}
```

---

## 📅 Месячная статистика трафика

### Общая месячная статистика
**GET** `/api/traffic/monthly?year_month=2025-08`

Возвращает месячную статистику трафика для всех ключей. Параметр `year_month` необязателен (по умолчанию текущий месяц).

**Параметры:**
- `year_month` (опционально) - месяц в формате YYYY-MM (например, "2025-08")

**Ответ:**
```json
{
    "status": "success",
    "data": {
        "year_month": "2025-08",
        "total_keys": 2,
        "active_keys": 2,
        "total_traffic_bytes": 38468204.02026367,
        "total_rx_bytes": 19234101.0,
        "total_tx_bytes": 19234101.0,
        "total_connections": 271,
        "total_sessions": 28,
        "keys": [
            {
                "key_uuid": "0e5ff24b-c47b-4193-ae76-3ba8233a1930",
                "key_name": "nvipetrenko@gmail.com",
                "port": 10001,
                "created_at": "2025-08-05T16:06:36.864003",
                "last_activity": "2025-08-05T17:49:51.981637",
                "is_active": true,
                "monthly_traffic": {
                    "total_bytes": 38467682.02026367,
                    "rx_bytes": 19233840.0,
                    "tx_bytes": 19233840.0,
                    "max_connections": 271,
                    "sessions": 5,
                    "total_formatted": "36.69 MB",
                    "rx_formatted": "18.34 MB",
                    "tx_formatted": "18.34 MB"
                }
            },
            {
                "key_uuid": "dc41f2d0-7741-43d2-b0c4-193cd8dd16ce",
                "key_name": "zhdanov@gmail.com",
                "port": 10002,
                "created_at": "2025-08-05T16:06:36.865147",
                "last_activity": "2025-08-05T17:49:51.983284",
                "is_active": true,
                "monthly_traffic": {
                    "total_bytes": 522,
                    "rx_bytes": 261,
                    "tx_bytes": 261,
                    "max_connections": 252,
                    "sessions": 23,
                    "total_formatted": "522 B",
                    "rx_formatted": "261 B",
                    "tx_formatted": "261 B"
                }
            }
        ],
        "total_traffic_formatted": "36.69 MB",
        "total_rx_formatted": "18.34 MB",
        "total_tx_formatted": "18.34 MB"
    },
    "timestamp": "2025-08-05T17:49:51.983284"
}
```

**Примеры использования:**
```bash
# Текущий месяц
curl -H "X-API-Key: your-api-key" https://localhost:8000/api/traffic/monthly

# Указанный месяц
curl -H "X-API-Key: your-api-key" https://localhost:8000/api/traffic/monthly?year_month=2025-08
```

### Месячная статистика ключа
**GET** `/api/keys/{key_id}/traffic/monthly?year_month=2025-08`

Возвращает месячную статистику трафика для конкретного ключа. Параметр `year_month` необязателен (по умолчанию текущий месяц).

**Параметры:**
- `year_month` (опционально) - месяц в формате YYYY-MM (например, "2025-08")

**Ответ:**
```json
{
    "status": "success",
    "data": {
        "key_uuid": "0e5ff24b-c47b-4193-ae76-3ba8233a1930",
        "key_name": "nvipetrenko@gmail.com",
        "port": 10001,
        "created_at": "2025-08-05T16:06:36.864003",
        "last_activity": "2025-08-05T17:49:46.365707",
        "is_active": true,
        "year_month": "2025-08",
        "monthly_traffic": {
            "total_bytes": 38467682.02026367,
            "rx_bytes": 19233840.0,
            "tx_bytes": 19233840.0,
            "max_connections": 271,
            "sessions": 4,
            "total_formatted": "36.69 MB",
            "rx_formatted": "18.34 MB",
            "tx_formatted": "18.34 MB"
        },
        "daily_breakdown": {
            "2025-08-05": {
                "total_bytes": 38467682.02026367,
                "rx_bytes": 19233840.0,
                "tx_bytes": 19233840.0,
                "max_connections": 271,
                "sessions": 4
            }
        }
    },
    "timestamp": "2025-08-05T17:49:46.365707"
}
```

**Примеры использования:**
```bash
# Текущий месяц для ключа
curl -H "X-API-Key: your-api-key" https://localhost:8000/api/keys/key-id/traffic/monthly

# Указанный месяц для ключа
curl -H "X-API-Key: your-api-key" https://localhost:8000/api/keys/key-id/traffic/monthly?year_month=2025-08
```

---

## 🔧 Системные эндпоинты

### Статус трафика
**GET** `/api/traffic/status`

Возвращает статус трафика всех ключей.

### Синхронизация конфигурации
**POST** `/api/system/sync-config`

Принудительно синхронизирует конфигурацию Xray с базой ключей.

### Статус конфигурации
**GET** `/api/system/config-status`

Возвращает статус синхронизации конфигурации.

### Проверка Reality настроек
**POST** `/api/system/verify-reality`

Проверяет корректность Reality настроек.

### Статус портов
**GET** `/api/system/ports`

Возвращает статус назначения портов.

### Сброс портов
**POST** `/api/system/ports/reset`

Сбрасывает все назначения портов.

### Валидация портов
**GET** `/api/system/ports/status`

Возвращает статус валидации портов.

### Сводка системного трафика
**GET** `/api/system/traffic/summary`

Возвращает сводку системного трафика.

### Статус конфигурации Xray
**GET** `/api/system/xray/config-status`

Возвращает статус конфигурации Xray.

### Синхронизация конфигурации Xray
**POST** `/api/system/xray/sync-config`

Синхронизирует конфигурацию Xray.

### Валидация синхронизации Xray
**GET** `/api/system/xray/validate-sync`

Валидирует синхронизацию конфигурации Xray.

---

## 📝 Коды ошибок

- **200** - Успешный запрос
- **400** - Неверный запрос
- **401** - Неверный API ключ
- **404** - Ресурс не найден
- **500** - Внутренняя ошибка сервера

---

## 🔄 Примеры использования

### Получение общего объема трафика с момента создания ключей
```bash
curl -H "X-API-Key: your-api-key" \
     https://localhost:8000/api/traffic/history
```

### Получение истории трафика конкретного ключа
```bash
curl -H "X-API-Key: your-api-key" \
     https://localhost:8000/api/keys/key-id/traffic/history
```

### Получение ежедневной статистики
```bash
curl -H "X-API-Key: your-api-key" \
     https://localhost:8000/api/traffic/daily/2025-08-05
```

---

## 📊 Структура данных

### Ключ VPN
```json
{
    "id": "string",           // Уникальный ID ключа
    "name": "string",         // Имя/email пользователя
    "uuid": "string",         // UUID для VLESS протокола
    "created_at": "string",   // Дата создания (ISO 8601)
    "is_active": "boolean",   // Активен ли ключ
    "port": "integer"         // Назначенный порт
}
```

### Трафик
```json
{
    "total_bytes": "integer",      // Общий объем в байтах
    "rx_bytes": "integer",         // Входящий трафик
    "tx_bytes": "integer",         // Исходящий трафик
    "connections": "integer",      // Количество соединений
    "total_formatted": "string",   // Форматированный объем
    "traffic_rate": "float"        // Скорость трафика
}
```

### Исторические данные
```json
{
    "total_traffic": {
        "total_bytes": "integer",
        "rx_bytes": "integer", 
        "tx_bytes": "integer",
        "total_connections": "integer",
        "total_formatted": "string",
        "rx_formatted": "string",
        "tx_formatted": "string"
    },
    "daily_stats": {
        "YYYY-MM-DD": {
            "total_bytes": "integer",
            "rx_bytes": "integer",
            "tx_bytes": "integer", 
            "max_connections": "integer",
            "sessions": "integer"
        }
    }
}
``` 