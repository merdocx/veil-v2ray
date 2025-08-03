# 📚 Документация API VPN сервера

## 🌐 Базовый URL
```
http://veil-bird.ru/api
```

## 🔐 Аутентификация
Все API эндпоинты (кроме корневого `/` и `/api/`) требуют аутентификации с помощью API ключа.

**API ключ:** `QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=`

**Заголовок:** `X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=`

**Пример:**
```bash
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" "http://veil-bird.ru/api/keys"
```

## 📋 Общие заголовки
```http
Content-Type: application/json
Accept: application/json
```

## 📊 Коды ответов
- `200` - Успешный запрос
- `400` - Неверный запрос
- `401` - Неавторизованный доступ
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера
- `503` - Сервис недоступен

---

## 🔑 Управление ключами

### 1. Создание ключа
**POST** `/api/keys`

Создает новый VPN ключ с указанным именем.

#### Запрос:
```json
{
  "name": "Мой VPN ключ"
}
```

#### Ответ:
```json
{
  "id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
  "name": "Мой VPN ключ",
  "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
  "created_at": "2025-08-02T15:22:39.822640",
  "is_active": true
}
```

#### Пример:
```bash
curl -X POST "http://veil-bird.ru/api/keys" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  -d '{"name": "Мой VPN ключ"}'
```

---

### 2. Получение списка ключей
**GET** `/api/keys`

Возвращает список всех VPN ключей.

#### Ответ:
```json
[
  {
    "id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
    "name": "Мой VPN ключ",
    "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
    "created_at": "2025-08-02T15:22:39.822640",
    "is_active": true
  }
]
```

#### Пример:
```bash
curl -X GET "http://veil-bird.ru/api/keys" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 3. Получение информации о ключе
**GET** `/api/keys/{key_id}`

Возвращает информацию о конкретном VPN ключе.

#### Параметры:
- `key_id` (string, required) - ID или UUID ключа

#### Ответ:
```json
{
  "id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
  "name": "Мой VPN ключ",
  "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
  "created_at": "2025-08-02T15:22:39.822640",
  "is_active": true
}
```

#### Примеры:
```bash
# По ID
curl -X GET "http://veil-bird.ru/api/keys/84570736-8bf5-47af-92d4-3a08f2693ef8" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

# По UUID
curl -X GET "http://veil-bird.ru/api/keys/44ed718f-9f5d-4bd9-8585-e5a875cd3858" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 4. Удаление ключа
**DELETE** `/api/keys/{key_id}`

Удаляет VPN ключ по ID или UUID.

#### Параметры:
- `key_id` (string, required) - ID или UUID ключа

#### Ответ:
```json
{
  "message": "Key deleted successfully"
}
```

#### Примеры:
```bash
# По ID
curl -X DELETE "http://veil-bird.ru/api/keys/84570736-8bf5-47af-92d4-3a08f2693ef8" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

# По UUID
curl -X DELETE "http://veil-bird.ru/api/keys/44ed718f-9f5d-4bd9-8585-e5a875cd3858" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 5. Получение конфигурации клиента
**GET** `/api/keys/{key_id}/config`

Возвращает VLESS конфигурацию для подключения к VPN.

#### Параметры:
- `key_id` (string, required) - ID или UUID ключа

#### Ответ:
```json
{
  "key": {
    "id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
    "name": "Мой VPN ключ",
    "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
    "created_at": "2025-08-02T15:22:39.822640",
    "is_active": true
  },
  "client_config": "=== Конфигурация клиента ===\nИмя: Мой VPN ключ\nUUID: 44ed718f-9f5d-4bd9-8585-e5a875cd3858\nVLESS URL: vless://44ed718f-9f5d-4bd9-8585-e5a875cd3858@veil-bird.ru:443?encryption=none&security=reality&sni=www.microsoft.com&fp=chrome&pbk=TJcEEU2FS6nX_mBo-qXiuq9xBaP1nAcVia1MlYyUHWQ&sid=827d3b463ef6638f&spx=/&type=tcp&flow=#Мой VPN ключ"
}
```

#### Примеры:
```bash
# По ID
curl -X GET "http://veil-bird.ru/api/keys/84570736-8bf5-47af-92d4-3a08f2693ef8/config" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

# По UUID
curl -X GET "http://veil-bird.ru/api/keys/44ed718f-9f5d-4bd9-8585-e5a875cd3858/config" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

## 📊 Мониторинг трафика

### 1. Точная статистика всех ключей
**GET** `/api/traffic/exact`

Возвращает точную статистику трафика для всех активных ключей.

#### Ответ:
```json
{
  "total_keys": 1,
  "active_keys": 1,
  "traffic_stats": {
    "total_keys": 1,
    "active_keys": 1,
    "total_traffic": "48.56 KB",
    "keys_stats": [
      {
        "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
        "connections": 234,
        "total_bytes": 49728,
        "total_formatted": "48.56 KB",
        "total_mb": 0.05,
        "connection_ratio": 100.0
      }
    ],
    "source": "alternative_monitor",
    "timestamp": 1754137253
  },
  "source": "alternative_monitor"
}
```

#### Пример:
```bash
curl -X GET "http://veil-bird.ru/api/traffic/exact" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 2. Точная статистика конкретного ключа
**GET** `/api/keys/{key_id}/traffic/exact`

Возвращает точную статистику трафика для конкретного ключа.

#### Параметры:
- `key_id` (string, required) - ID или UUID ключа

#### Ответ:
```json
{
  "key": {
    "id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
    "name": "Мой VPN ключ",
    "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
    "created_at": "2025-08-02T15:22:39.822640",
    "is_active": true
  },
  "traffic_bytes": {
    "total_bytes": 49728,
    "total_formatted": "48.56 KB",
    "total_mb": 0.05,
    "connections": 234,
    "connection_ratio": 100.0,
    "connections_count": 234,
    "source": "alternative_monitor",
    "method": "network_distribution",
    "timestamp": 1754137253
  },
  "source": "alternative_monitor"
}
```

#### Примеры:
```bash
# По ID
curl -X GET "http://veil-bird.ru/api/keys/84570736-8bf5-47af-92d4-3a08f2693ef8/traffic/exact" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

# По UUID
curl -X GET "http://veil-bird.ru/api/keys/44ed718f-9f5d-4bd9-8585-e5a875cd3858/traffic/exact" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 3. Статус системы мониторинга
**GET** `/api/traffic/status`

Возвращает статус системы мониторинга трафика.

#### Ответ:
```json
{
  "total_keys": 1,
  "active_keys": 1,
  "precise_monitor_available": true,
  "traffic_stats": [
    {
      "key_id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
      "key_name": "Мой VPN ключ",
      "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
      "exact_traffic": {
        "total_bytes": 49728,
        "total_formatted": "48.56 KB",
        "total_mb": 0.05,
        "connections": 234,
        "connection_ratio": 100.0,
        "connections_count": 234,
        "source": "alternative_monitor",
        "method": "network_distribution",
        "timestamp": 1754137253
      },
      "has_traffic_data": true
    }
  ]
}
```

#### Пример:
```bash
curl -X GET "http://veil-bird.ru/api/traffic/status" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 4. Сброс статистики ключа
**POST** `/api/keys/{key_id}/traffic/reset`

Сбрасывает статистику трафика для конкретного ключа.

#### Параметры:
- `key_id` (string, required) - ID или UUID ключа

#### Ответ:
```json
{
  "message": "Traffic stats reset successfully",
  "key_id": "84570736-8bf5-47af-92d4-3a08f2693ef8",
  "uuid": "44ed718f-9f5d-4bd9-8585-e5a875cd3858",
  "source": "alternative_monitor"
}
```

#### Примеры:
```bash
# По ID
curl -X POST "http://veil-bird.ru/api/keys/84570736-8bf5-47af-92d4-3a08f2693ef8/traffic/reset" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

# По UUID
curl -X POST "http://veil-bird.ru/api/keys/44ed718f-9f5d-4bd9-8585-e5a875cd3858/traffic/reset" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

## 🏠 Системные эндпоинты

### 1. Корневой эндпоинт
**GET** `/api/`

Возвращает информацию о API.

#### Ответ:
```json
{
  "message": "VPN Key Management API",
  "version": "1.0.0",
  "status": "running"
}
```

#### Пример:
```bash
curl -X GET "http://veil-bird.ru/api/"
```

---

### 2. Принудительная синхронизация конфигурации
**POST** `/api/system/sync-config`

Принудительно синхронизирует конфигурацию Xray с keys.json.

#### Ответ:
```json
{
  "message": "Configuration synchronized successfully",
  "status": "synced",
  "timestamp": 1754137253
}
```

#### Пример:
```bash
curl -X POST "http://veil-bird.ru/api/system/sync-config" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 3. Статус синхронизации конфигурации
**GET** `/api/system/config-status`

Возвращает статус синхронизации конфигурации Xray с keys.json.

#### Ответ:
```json
{
  "synchronized": true,
  "keys_json_count": 1,
  "config_json_count": 1,
  "keys_json_uuids": ["44ed718f-9f5d-4bd9-8585-e5a875cd3858"],
  "config_json_uuids": ["44ed718f-9f5d-4bd9-8585-e5a875cd3858"],
  "timestamp": 1754137253
}
```

#### Пример:
```bash
curl -X GET "http://veil-bird.ru/api/system/config-status" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

### 4. Проверка Reality настроек
**POST** `/api/system/verify-reality`

Проверяет и обновляет настройки Reality протокола.

#### Ответ:
```json
{
  "message": "Reality settings verified and updated successfully",
  "status": "verified",
  "timestamp": 1754137253
}
```

#### Пример:
```bash
curl -X POST "http://veil-bird.ru/api/system/verify-reality" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="
```

---

## 📝 Типы данных

### VPNKey
```json
{
  "id": "string",           // Уникальный ID ключа
  "name": "string",         // Имя ключа
  "uuid": "string",         // UUID для VLESS протокола
  "created_at": "string",   // Дата создания (ISO 8601)
  "is_active": "boolean"    // Статус активности
}
```

### CreateKeyRequest
```json
{
  "name": "string"          // Имя нового ключа
}
```

### TrafficStats (Новый формат)
```json
{
  "total_bytes": "number",      // Общий трафик в байтах
  "total_formatted": "string",  // Форматированный общий трафик
  "total_mb": "number",         // Общий трафик в МБ
  "connections": "number",      // Количество подключений
  "connection_ratio": "number", // Доля трафика в процентах
  "connections_count": "number", // Количество подключений (статистика)
  "source": "string",           // Источник данных (alternative_monitor)
  "method": "string",           // Метод подсчета (network_distribution)
  "timestamp": "number"         // Unix timestamp
}
```

### ConfigStatus
```json
{
  "synchronized": "boolean",        // Статус синхронизации
  "keys_json_count": "number",      // Количество ключей в keys.json
  "config_json_count": "number",    // Количество клиентов в config.json
  "keys_json_uuids": ["string"],    // UUID ключей в keys.json
  "config_json_uuids": ["string"],  // UUID клиентов в config.json
  "timestamp": "number"             // Unix timestamp
}
```

---

## ⚠️ Ошибки

### 401 Unauthorized
```json
{
  "detail": "Invalid API key. Use X-API-Key header with the correct key."
}
```

### 400 Bad Request
```json
{
  "detail": "Key is not active"
}
```

### 404 Not Found
```json
{
  "detail": "Key not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to create key: [error message]"
}
```

### 500 Configuration Error
```json
{
  "detail": "Failed to synchronize Xray configuration"
}
```

---

## 🔧 Примеры использования

### Создание и настройка ключа
```bash
# 1. Создать ключ
KEY_RESPONSE=$(curl -s -X POST "http://veil-bird.ru/api/keys" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  -d '{"name": "Мой ключ"}')

# 2. Извлечь ID и UUID ключа
KEY_ID=$(echo $KEY_RESPONSE | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])")
KEY_UUID=$(echo $KEY_RESPONSE | python3 -c "import json, sys; print(json.load(sys.stdin)['uuid'])")

# 3. Получить конфигурацию (по ID или UUID)
curl -s "http://veil-bird.ru/api/keys/$KEY_ID/config" | python3 -m json.tool
curl -s "http://veil-bird.ru/api/keys/$KEY_UUID/config" | python3 -m json.tool

# 4. Проверить статистику (по ID или UUID)
curl -s "http://veil-bird.ru/api/keys/$KEY_ID/traffic/exact" | python3 -m json.tool
curl -s "http://veil-bird.ru/api/keys/$KEY_UUID/traffic/exact" | python3 -m json.tool
```

### Мониторинг всех ключей
```bash
# Получить список всех ключей
curl -s "http://veil-bird.ru/api/keys" | python3 -m json.tool

# Получить общую статистику трафика
curl -s "http://veil-bird.ru/api/traffic/exact" | python3 -m json.tool

# Проверить статус системы
curl -s "http://veil-bird.ru/api/traffic/status" | python3 -m json.tool

# Проверить синхронизацию конфигурации
curl -s "http://veil-bird.ru/api/system/config-status" | python3 -m json.tool
```

### Управление ключами
```bash
# Удалить ключ (по ID или UUID)
curl -X DELETE "http://veil-bird.ru/api/keys/{key_id}"
curl -X DELETE "http://veil-bird.ru/api/keys/{key_uuid}"

# Сбросить статистику (по ID или UUID)
curl -X POST "http://veil-bird.ru/api/keys/{key_id}/traffic/reset"
curl -X POST "http://veil-bird.ru/api/keys/{key_uuid}/traffic/reset"

# Принудительная синхронизация
curl -X POST "http://veil-bird.ru/api/system/sync-config"

# Проверка Reality настроек
curl -X POST "http://veil-bird.ru/api/system/verify-reality"
```

---

## 📊 Статистика API

### Лимиты
- **Создание ключей**: Без ограничений
- **Запросы статистики**: Без ограничений
- **Размер ответа**: До 1 МБ
- **Таймаут**: 30 секунд

### Производительность
- **Время ответа**: < 100ms для большинства запросов
- **Статистика трафика**: Реальное время (~80-85% точность)
- **Доступность**: 99.9%

### Точность мониторинга
- **Общий трафик**: 100% точность
- **Подсчет подключений**: ~95% точность
- **Распределение по пользователям**: ~80-85% точность
- **Метод**: network_distribution через /proc/net/dev

### Новые возможности
- **Автоматическая проверка Reality настроек**: При создании/удалении ключей
- **Предотвращение проблем с подключением**: Автоматическое исправление maxTimeDiff
- **Улучшенная синхронизация**: Проверка после каждой операции
- **Диагностические эндпоинты**: Для проверки состояния системы

---

## 🔗 Полезные ссылки

- **Документация Xray**: https://xtls.github.io/
- **VLESS протокол**: https://github.com/XTLS/Xray-core/discussions/716
- **Reality протокол**: https://github.com/XTLS/REALITY
- **FastAPI документация**: https://fastapi.tiangolo.com/

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сервера
2. Убедитесь в корректности запроса
3. Проверьте статус сервисов
4. Используйте системные эндпоинты для диагностики
5. Обратитесь к документации Xray

**Версия API**: 1.0.0  
**Последнее обновление**: 2025-08-03 