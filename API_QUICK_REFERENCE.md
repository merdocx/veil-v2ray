# API Quick Reference

## Версия API: 2.3.3

## Основные эндпоинты

### Информационные (без аутентификации)
- `GET /` - Информация о версии и статусе API
- `GET /api/` - Информация об API
- `GET /health` - Health check для мониторинга состояния системы

### Управление ключами
- `POST /api/keys` - создание ключа (лимит: 5/мин)
- `GET /api/keys` - список всех ключей (лимит: 30/мин)
- `GET /api/keys/{key_id}` - получение ключа (лимит: 60/мин)
- `DELETE /api/keys/{key_id}` - удаление ключа (лимит: 10/мин)
- `GET /api/keys/{key_id}/config` - конфигурация ключа (VLESS URL)

### Мониторинг трафика
- `GET /api/keys/{key_id}/traffic` - получить накопительный трафик ключа
- `POST /api/keys/{key_id}/traffic/reset` - обнулить накопительный трафик ключа

> Трафик считается накопительно с момента создания или последнего сброса. Данные обновляются автоматически каждые 5 минут и при каждом запросе.

### Системные эндпоинты - Конфигурация
- `POST /api/system/sync-config` - синхронизация конфигурации Xray с SQLite (лимит: 3/мин)
- `GET /api/system/config-status` - статус синхронизации конфигурации
- `POST /api/system/verify-reality` - проверка Reality настроек

### Системные эндпоинты - Порты
- `GET /api/system/ports` - статус портов
- `POST /api/system/ports/reset` - сброс всех портов
- `GET /api/system/ports/status` - валидация портов

### Системные эндпоинты - Xray
- `GET /api/system/xray/config-status` - статус конфигурации Xray
- `GET /api/system/xray/inbounds` - список активных inbound'ов
- `POST /api/system/xray/sync-config` - синхронизация конфигурации Xray
- `GET /api/system/xray/validate-sync` - валидация синхронизации Xray
- `POST /api/system/fix-reality-keys` - исправление Reality ключей

> **Важно:** новые ключи получают уникальный `short_id` (16-значный hex) и случайный SNI домен. Поля присутствуют в ответах `POST /api/keys`, `GET /api/keys`, `GET /api/keys/{key_id}` и `GET /api/keys/{key_id}/config`.

## Примеры запросов

> Базовый адрес API: `https://<IP_ИЛИ_ДОМЕН>:8000`. Домен необязателен — можно использовать публичный IP сервера. При self-signed сертификате добавляйте `-k` в `curl`.

### Информационные

#### Health check
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/health"
```

### Управление ключами

#### Создание ключа
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/keys" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "user@example.com"}'
```

#### Получение списка ключей
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/keys" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Получение конкретного ключа
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/keys/{key_id}" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Получение конфигурации ключа
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/keys/{key_id}/config" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Удаление ключа
```bash
curl -k -X DELETE "https://SERVER_ADDRESS:8000/api/keys/{key_id}" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Мониторинг трафика

#### Получение накопительного трафика ключа
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/keys/{key_id}/traffic" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Обнуление трафика ключа
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/keys/{key_id}/traffic/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Системные запросы

#### Синхронизация конфигурации
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/system/sync-config" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Статус конфигурации
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/system/config-status" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Проверка Reality настроек
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/system/verify-reality" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Статус портов
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/system/ports" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Сброс портов
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/system/ports/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Валидация портов
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/system/ports/status" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Статус конфигурации Xray
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/system/xray/config-status" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Список inbound'ов Xray
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/system/xray/inbounds" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Синхронизация конфигурации Xray
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/system/xray/sync-config" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Валидация синхронизации Xray
```bash
curl -k -X GET "https://SERVER_ADDRESS:8000/api/system/xray/validate-sync" \
  -H "X-API-Key: YOUR_API_KEY"
```

#### Исправление Reality ключей
```bash
curl -k -X POST "https://SERVER_ADDRESS:8000/api/system/fix-reality-keys" \
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
  "port": 10001,
  "short_id": "5f9c2b7adfe7d8ab",
  "sni": "www.microsoft.com"
}
```

### Получение трафика ключа
```json
{
  "status": "success",
  "key_id": "e9d747b1-07f7-490e-a26e-c8ea6d67fd7d",
  "key_uuid": "0e5ff24b-c47b-4193-ae76-3ba8233a1930",
  "total_bytes": 1234567,
  "timestamp": "2025-11-21T16:00:00"
}
```

### Обнуление трафика
```json
{
  "status": "success",
  "message": "Traffic reset successfully",
  "key_id": "e9d747b1-07f7-490e-a26e-c8ea6d67fd7d",
  "key_uuid": "0e5ff24b-c47b-4193-ae76-3ba8233a1930",
  "timestamp": "2025-11-21T16:00:00"
}
```

### Health check
```json
{
  "status": "healthy",
  "timestamp": "2025-11-21T16:00:00",
  "version": "2.3.2",
  "services": {
    "xray": "running",
    "api": "running",
    "nginx": "running"
  },
  "resources": {
    "memory_usage_percent": 45.2,
    "memory_available_mb": 2048.5,
    "disk_usage_percent": 32.1,
    "disk_free_gb": 50.3,
    "cpu_usage_percent": 12.5
  },
  "uptime_seconds": 86400
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

- `200 OK` - Успешный запрос
- `400 Bad Request` - Неверный запрос
- `401 Unauthorized` - Неверный API ключ
- `404 Not Found` - Ресурс не найден
- `500 Internal Server Error` - Внутренняя ошибка сервера
- `503 Service Unavailable` - Сервис недоступен (например, Xray Stats API)

## Примечания

- Все запросы (кроме `/`, `/api/` и `/health`) требуют заголовок `X-API-Key`
- API поддерживает HTTPS
- Трафик считается через Xray Stats API и обновляется автоматически каждые 5 минут
- Каждый ключ получает уникальный порт из диапазона 10001-10100
- Максимум 100 активных ключей
- При использовании self-signed сертификата добавляйте флаг `-k` в curl команды
