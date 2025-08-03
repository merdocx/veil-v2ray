# 📋 Краткая справка API VPN сервера

## 🔐 Аутентификация
**API ключ:** `QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=`  
**Заголовок:** `X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=`

## 🌐 Базовый URL
```
http://veil-bird.ru/api
```

---

## 🔑 Управление ключами

### Создание ключа
```bash
curl -X POST "http://veil-bird.ru/api/keys" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  -d '{"name": "Мой ключ"}'
```

### Список ключей
```bash
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys"
```

### Информация о ключе (ID или UUID)
```bash
# По ID
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_id}"

# По UUID
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_uuid}"
```

### Удаление ключа (ID или UUID)
```bash
# По ID
curl -X DELETE -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_id}"

# По UUID
curl -X DELETE -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_uuid}"
```

### Конфигурация клиента (ID или UUID)
```bash
# По ID
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_id}/config"

# По UUID
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_uuid}/config"
```

---

## 📊 Мониторинг трафика

### Общая статистика
```bash
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/traffic/exact"
```

### Статистика ключа (ID или UUID)
```bash
# По ID
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_id}/traffic/exact"

# По UUID
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_uuid}/traffic/exact"
```

### Статус системы
```bash
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/traffic/status"
```

### Сброс статистики (ID или UUID)
```bash
# По ID
curl -X POST -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_id}/traffic/reset"

# По UUID
curl -X POST -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/keys/{key_uuid}/traffic/reset"
```

---

## 🏠 Системные эндпоинты

### Информация об API
```bash
curl "http://veil-bird.ru/api/"
```

### Статус синхронизации
```bash
curl -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/system/config-status"
```

### Принудительная синхронизация
```bash
curl -X POST -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/system/sync-config"
```

### Проверка Reality настроек
```bash
curl -X POST -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  "http://veil-bird.ru/api/system/verify-reality"
```

---

## 📊 Коды ответов
- `200` - Успешно
- `400` - Неверный запрос
- `401` - Неавторизован
- `404` - Не найдено
- `500` - Ошибка сервера

---

## 🎯 Быстрый старт

### 1. Создать ключ
```bash
KEY_RESPONSE=$(curl -s -X POST "http://veil-bird.ru/api/keys" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=" \
  -d '{"name": "Мой ключ"}')
```

### 2. Получить ID и UUID
```bash
KEY_ID=$(echo $KEY_RESPONSE | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])")
KEY_UUID=$(echo $KEY_RESPONSE | python3 -c "import json, sys; print(json.load(sys.stdin)['uuid'])")
```

### 3. Получить конфигурацию
```bash
curl -s "http://veil-bird.ru/api/keys/$KEY_ID/config" | python3 -m json.tool
```

### 4. Проверить трафик
```bash
curl -s "http://veil-bird.ru/api/keys/$KEY_ID/traffic/exact" | python3 -m json.tool
```

---

## 📈 Точность мониторинга
- **Общий трафик**: 100%
- **Подключения**: ~95%
- **По пользователям**: ~80-85%
- **Метод**: network_distribution

## 🆕 Новые возможности
- **Автоматическая проверка Reality настроек**
- **Предотвращение проблем с подключением**
- **Улучшенная синхронизация**
- **Диагностические эндпоинты**

**Версия**: 1.0.0  
**Обновлено**: 2025-08-03 