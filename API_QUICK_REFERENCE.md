# API Quick Reference

## Основные эндпоинты

### Управление ключами
- `POST /api/keys` - создание ключа
- `GET /api/keys` - список всех ключей
- `GET /api/keys/{key_id}` - получение ключа
- `DELETE /api/keys/{key_id}` - удаление ключа
- `GET /api/keys/{key_id}/config` - конфигурация ключа

### Мониторинг трафика
- `GET /api/traffic/simple` - простой мониторинг всех ключей
- `GET /api/keys/{key_id}/traffic/simple` - простой мониторинг ключа
- `POST /api/keys/{key_id}/traffic/simple/reset` - сброс статистики ключа

### Системные эндпоинты
- `GET /api/system/ports` - статус портов
- `POST /api/system/ports/reset` - сброс портов
- `GET /api/system/traffic/summary` - сводка трафика
- `GET /api/system/xray/config-status` - статус конфигурации Xray
- `POST /api/system/xray/sync-config` - синхронизация конфигурации

## Примеры запросов

### Создание ключа
```bash
curl -X POST "https://veil-bird.ru/api/keys" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "user@example.com"}'
```

### Получение списка ключей
```bash
curl -X GET "https://veil-bird.ru/api/keys" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Получение конфигурации ключа
```bash
curl -X GET "https://veil-bird.ru/api/keys/{key_id}/config" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Удаление ключа
```bash
curl -X DELETE "https://veil-bird.ru/api/keys/{key_id}" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Мониторинг трафика

#### Простой мониторинг всех ключей
```bash
curl -X GET "https://veil-bird.ru/api/traffic/simple" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Простой мониторинг конкретного ключа
```bash
curl -X GET "https://veil-bird.ru/api/keys/{key_id}/traffic/simple" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Сброс статистики ключа
```bash
curl -X POST "https://veil-bird.ru/api/keys/{key_id}/traffic/simple/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Системные запросы

#### Статус портов
```bash
curl -X GET "https://veil-bird.ru/api/system/ports" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Сброс портов
```bash
curl -X POST "https://veil-bird.ru/api/system/ports/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Сводка трафика
```bash
curl -X GET "https://veil-bird.ru/api/system/traffic/summary" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Статус конфигурации Xray
```bash
curl -X GET "https://veil-bird.ru/api/system/xray/config-status" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Синхронизация конфигурации
```bash
curl -X POST "https://veil-bird.ru/api/system/xray/sync-config" \
  -H "X-API-Key: YOUR_API_KEY"
```

## Примеры ответов

### Создание ключа
```json
{
  "id": "e9d747b1-07f7-490e-a26e-c8ea6d67fd7d",
  "name": "user@example.com",
  "uuid": "0e5ff24b-c47b-4193-ae76-3ba8233a1930",
  "created_at": "2025-08-05T00:34:28.901054",
  "is_active": true,
  "port": 10001
}
```

### Простой мониторинг трафика
```json
{
  "status": "success",
  "data": {
    "ports": {
      "10001": {
        "port": 10001,
        "connections": 0,
        "total_bytes": 0,
        "total_formatted": "0 B",
        "traffic_rate": 0,
        "uuid": "0e5ff24b-c47b-4193-ae76-3ba8233a1930"
      }
    },
    "total_connections": 0,
    "total_bytes": 0
  }
}
```

## Переменные окружения

```bash
# API ключ для аутентификации
VPN_API_KEY=your-secret-api-key

# Настройки сервера
VPN_HOST=0.0.0.0
VPN_PORT=8000

# Настройки безопасности
VPN_ENABLE_HTTPS=true
VPN_SSL_CERT_PATH=/etc/ssl/certs/vpn-api.crt
VPN_SSL_KEY_PATH=/etc/ssl/private/vpn-api.key
```

## Коды ошибок

- `401 Unauthorized` - неверный API ключ
- `404 Not Found` - ключ не найден
- `500 Internal Server Error` - внутренняя ошибка сервера

## Примечания

- Все запросы требуют заголовок `X-API-Key`
- API поддерживает HTTPS
- Мониторинг трафика использует простую систему оценки на основе соединений
- Кэширование результатов мониторинга: 30 секунд 