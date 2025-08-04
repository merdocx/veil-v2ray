# 📋 Краткая справка API VPN сервера

## 🔐 Аутентификация
**API ключ загружается из переменных окружения**  
**Заголовок:** `X-API-Key: YOUR_API_KEY`

## 🌐 Базовый URL
```
https://veil-bird.ru/api
```

### 🔑 Получение API ключа
API ключ хранится в файле `/root/vpn-server/.env` в переменной `VPN_API_KEY`.

Для генерации нового API ключа:
```bash
python3 /root/vpn-server/generate_api_key.py
```

---

## 🔑 Управление ключами

### Создание ключа (с назначением порта)
```bash
curl -X POST "https://veil-bird.ru/api/keys" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"name": "Мой ключ"}'
```

### Список ключей (с информацией о портах)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys"
```

### Информация о ключе (ID или UUID)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys/{key_id}"
```

### Удаление ключа (ID или UUID)
```bash
curl -X DELETE -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys/{key_id}"
```

### Конфигурация клиента (ID или UUID)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys/{key_id}/config"
```

---

## 📊 Точный мониторинг трафика (100% точность)

### Общая статистика по портам
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/traffic/ports/exact"
```

### Статистика ключа по порту (ID или UUID)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys/{key_id}/traffic/port/exact"
```

### Сброс статистики ключа (ID или UUID)
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys/{key_id}/traffic/port/reset"
```

### Системная сводка трафика
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/traffic/summary"
```

---

## 🔌 Управление портами

### Статус портов
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/ports"
```

### Сброс всех портов
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/ports/reset"
```

### Валидация портов
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/ports/status"
```

---

## ⚙️ Управление конфигурацией Xray

### Статус конфигурации Xray
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/xray/config-status"
```

### Синхронизация конфигурации
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/xray/sync-config"
```

### Валидация синхронизации
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/xray/validate-sync"
```

---

## 📊 Устаревшие эндпоинты (для совместимости)

### Приблизительная статистика
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/traffic/exact"
```

### Приблизительная статистика ключа
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/keys/{key_id}/traffic/exact"
```

---

## 🔧 Системные эндпоинты

### Проверка Reality настроек
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/verify-reality"
```

### Синхронизация конфигурации
```bash
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/sync-config"
```

### Статус синхронизации
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://veil-bird.ru/api/system/config-status"
```

---

## 📝 Быстрые примеры

### Создание ключа и получение конфигурации
```bash
# Создаем ключ
KEY_RESPONSE=$(curl -s -X POST "https://veil-bird.ru/api/keys" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"name": "Мой VPN ключ"}')

# Извлекаем ID и UUID
KEY_ID=$(echo $KEY_RESPONSE | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])")
KEY_UUID=$(echo $KEY_RESPONSE | python3 -c "import json, sys; print(json.load(sys.stdin)['uuid'])")

# Получаем конфигурацию клиента
curl -s -X GET "https://veil-bird.ru/api/keys/$KEY_ID/config" \
  -H "X-API-Key: YOUR_API_KEY" | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['client_config'])"
```

### Мониторинг трафика
```bash
# Получаем общую статистику трафика
curl -s -X GET "https://veil-bird.ru/api/traffic/ports/exact" \
  -H "X-API-Key: YOUR_API_KEY"

# Получаем трафик конкретного ключа
curl -s -X GET "https://veil-bird.ru/api/keys/$KEY_ID/traffic/port/exact" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Управление портами
```bash
# Проверяем статус портов
curl -s -X GET "https://veil-bird.ru/api/system/ports" \
  -H "X-API-Key: YOUR_API_KEY"

# Сбрасываем статистику трафика
curl -s -X POST "https://veil-bird.ru/api/keys/$KEY_ID/traffic/port/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## 🎯 Особенности новой системы

### Преимущества системы с индивидуальными портами:
- ✅ **100% точность** мониторинга трафика
- 🔌 **Индивидуальные порты** для каждого ключа (10001-10020)
- 🛡️ **Полная изоляция** трафика пользователей
- 📊 **Упрощенная диагностика** проблем
- ⚡ **Масштабируемость** до 20 ключей

### Новые возможности:
- 🔍 **Точный мониторинг** трафика по портам
- 📈 **Детальная статистика** для каждого ключа
- 🔄 **Автоматическое управление** портами
- 🛠️ **Простое управление** через API
- 📚 **Полная документация** системы

---

## 📞 Поддержка

При возникновении проблем с API обращайтесь к документации системы или создайте issue в репозитории проекта.

**Версия API:** 1.0.0  
**Дата обновления:** 4 августа 2025  
**Статус:** ✅ Актуально 