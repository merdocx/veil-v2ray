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

### Создание ключа
```bash
POST /api/keys
Content-Type: application/json

{
    "name": "Имя ключа"
}
```

### Получение списка ключей
```bash
GET /api/keys
```

### Получение информации о ключе
```bash
GET /api/keys/{key_id}
```

### Получение конфигурации клиента
```bash
GET /api/keys/{key_id}/config
```

### Удаление ключа
```bash
DELETE /api/keys/{key_id}
```

## Документация API

Документация доступна по адресу: `http://veil-bird.ru/docs`

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

- Все ключи хранятся в зашифрованном виде
- API доступен только через HTTPS (при настройке SSL)
- Reality протокол обеспечивает обфускацию трафика
- Автоматическая ротация ключей

## Мониторинг

Логи сервисов доступны в:
- Xray: `/root/vpn-server/logs/`
- API: `journalctl -u vpn-api`
- Nginx: `/var/log/nginx/`

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