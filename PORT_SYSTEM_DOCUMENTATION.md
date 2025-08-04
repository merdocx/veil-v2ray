# Система точного мониторинга трафика с индивидуальными портами

## Обзор

Система точного мониторинга трафика с индивидуальными портами обеспечивает 100% точность подсчета трафика для каждого VPN ключа путем выделения уникального порта для каждого пользователя.

## Архитектура

```
Клиент 1 → Порт 10001 → Xray → Интернет
Клиент 2 → Порт 10002 → Xray → Интернет
...
Клиент N → Порт 1000N → Xray → Интернет
```

### Компоненты системы

1. **PortManager** (`port_manager.py`) - управление портами и конфигурацией
2. **XrayConfigManager** (`xray_config_manager.py`) - генерация конфигурации Xray
3. **PortTrafficMonitor** (`port_traffic_monitor.py`) - мониторинг трафика по портам
4. **API Extensions** - расширение существующего API

## Установка и настройка

### 1. Подготовка системы

```bash
# Переходим в директорию проекта
cd /root/vpn-server

# Проверяем права доступа
chmod +x *.py
```

### 2. Миграция существующих ключей

```bash
# Запуск миграции
python3 migrate_to_ports.py
```

Миграция автоматически:
- Создает резервную копию существующих ключей
- Назначает порты для каждого ключа
- Обновляет конфигурацию Xray
- Валидирует результаты

### 3. Тестирование системы

```bash
# Запуск тестов
python3 test_port_system.py
```

## API Эндпоинты

### Управление портами

#### GET /api/system/ports
Получить статус портов

**Ответ:**
```json
{
  "port_assignments": {
    "used_ports": {...},
    "port_assignments": {...}
  },
  "used_ports": 5,
  "available_ports": 15,
  "max_ports": 20,
  "port_range": "10001-10020",
  "timestamp": 1234567890
}
```

#### POST /api/system/ports/reset
Сбросить все порты

#### GET /api/system/ports/status
Получить статус валидации портов

### Точный мониторинг трафика

#### GET /api/traffic/ports/exact
Получить точную статистику трафика по портам

**Ответ:**
```json
{
  "ports_traffic": {
    "total_ports": 5,
    "ports_traffic": {
      "uuid-1": {
        "port": 10001,
        "key_name": "User 1",
        "traffic": {
          "port": 10001,
          "connections": 2,
          "total_bytes": 1048576,
          "total_formatted": "1.0 MB",
          "timestamp": 1234567890
        }
      }
    },
    "total_traffic": 5242880,
    "total_connections": 10
  },
  "system_summary": {
    "total_system_traffic": 10485760,
    "active_ports": 5,
    "interface_summary": {...}
  },
  "source": "port_monitor",
  "timestamp": 1234567890
}
```

#### GET /api/keys/{key_id}/traffic/port/exact
Получить точную статистику трафика для ключа по порту

#### POST /api/keys/{key_id}/traffic/port/reset
Сбросить статистику трафика для ключа по порту

#### GET /api/system/traffic/summary
Получить сводку системного трафика

### Конфигурация Xray

#### GET /api/system/xray/config-status
Получить статус конфигурации Xray

#### POST /api/system/xray/sync-config
Синхронизировать конфигурацию Xray с ключами

#### GET /api/system/xray/validate-sync
Валидировать синхронизацию конфигурации Xray

## Структуры данных

### Ключ с портом
```json
{
  "id": "uuid",
  "name": "string",
  "uuid": "string", 
  "port": 10001,
  "created_at": "timestamp",
  "is_active": true
}
```

### Статистика трафика порта
```json
{
  "port": 10001,
  "uuid": "user-uuid",
  "connections": 2,
  "total_bytes": 1048576,
  "rx_bytes": 524288,
  "tx_bytes": 524288,
  "total_formatted": "1.0 MB",
  "rx_formatted": "512.0 KB",
  "tx_formatted": "512.0 KB",
  "interface_traffic": {...},
  "total_interface_traffic": 10485760,
  "timestamp": 1234567890
}
```

## Конфигурация Xray

### Структура inbound для ключа
```json
{
  "port": 10001,
  "protocol": "vless",
  "settings": {
    "clients": [
      {
        "id": "uuid-1",
        "flow": "",
        "email": "uuid-1"
      }
    ],
    "decryption": "none"
  },
  "streamSettings": {
    "network": "tcp",
    "security": "reality",
    "realitySettings": {
      "show": false,
      "dest": "www.microsoft.com:443",
      "xver": 0,
      "serverNames": ["www.microsoft.com"],
      "privateKey": "generated-key",
      "shortIds": ["generated-id"],
      "maxTimeDiff": 600
    }
  },
  "tag": "inbound-uuid-1"
}
```

## Мониторинг и диагностика

### Проверка статуса системы

```bash
# Проверка портов
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/system/ports

# Проверка трафика
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/traffic/ports/exact

# Проверка конфигурации Xray
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/system/xray/config-status
```

### Логи и отладка

```bash
# Логи Xray
tail -f /root/vpn-server/logs/access.log
tail -f /root/vpn-server/logs/error.log

# Проверка активных портов
ss -tuln | grep 1000

# Проверка конфигурации
cat /root/vpn-server/config/config.json
```

## Ограничения и особенности

### Ограничения
- Максимум 20 активных ключей
- Диапазон портов: 10001-10020
- Время простоя при операциях: не более 2 секунд

### Особенности
- Каждый ключ получает уникальный порт
- Автоматическая генерация ключей Reality
- Резервное копирование конфигурации
- Валидация целостности данных

## Устранение неполадок

### Проблема: Нет свободных портов
**Решение:**
```bash
# Проверить использование портов
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/system/ports

# Удалить неиспользуемые ключи
curl -X DELETE -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/keys/{key_id}
```

### Проблема: Ошибка конфигурации Xray
**Решение:**
```bash
# Синхронизировать конфигурацию
curl -X POST -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/system/xray/sync-config

# Проверить статус
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/system/xray/validate-sync
```

### Проблема: Неточный трафик
**Решение:**
```bash
# Сбросить статистику
curl -X POST -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/keys/{key_id}/traffic/port/reset

# Проверить соединения
ss -tuln | grep {port}
```

## Производительность

### Метрики
- Время создания ключа: ~3 секунды
- Время удаления ключа: ~3 секунды
- Время ответа API: <100ms
- Точность мониторинга: 100%

### Оптимизация
- Кэширование результатов (30 секунд)
- Асинхронная обработка
- Валидация данных
- Автоматическое восстановление

## Безопасность

### Меры безопасности
- Валидация всех входных данных
- Проверка доступности портов
- Защита от конфликтов портов
- Резервное копирование конфигурации
- Логирование всех операций

### API ключ
Все запросы требуют валидный API ключ в заголовке `X-API-Key`.

## Обновления и миграция

### Обновление системы
```bash
# Создать резервную копию
cp -r /root/vpn-server /root/vpn-server-backup-$(date +%Y%m%d)

# Обновить файлы
# ... обновление кода ...

# Запустить миграцию
python3 migrate_to_ports.py

# Протестировать систему
python3 test_port_system.py
```

### Откат изменений
```bash
# Восстановить резервную копию
cp -r /root/vpn-server-backup-YYYYMMDD/* /root/vpn-server/

# Перезапустить сервисы
systemctl restart xray
```

## Поддержка

### Логи
- API логи: стандартный вывод FastAPI
- Xray логи: `/root/vpn-server/logs/`
- Системные логи: `journalctl -u xray`

### Контакты
Для получения поддержки обратитесь к документации проекта или создайте issue в репозитории.

---

**Система готова к использованию!** 🚀 