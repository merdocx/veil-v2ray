# Инструкции по использованию VPN сервера

## Быстрый старт

### 1. Проверка статуса сервисов
```bash
cd /root/vpn-server
./manage.sh status
```

### 2. Создание ключа
```bash
./manage.sh create-key "Имя ключа"
```

### 3. Получение списка ключей
```bash
./manage.sh list-keys
```

### 4. Получение конфигурации клиента
```bash
./manage.sh get-config <ID_ключа>
```

### 5. Удаление ключа
```bash
./manage.sh delete-key <ID_ключа>
```

## API Endpoints

### Создание ключа
```bash
curl -X POST http://veil-bird.ru/api/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "Имя ключа"}'
```

### Получение списка ключей
```bash
curl -X GET http://veil-bird.ru/api/keys
```

### Получение конфигурации клиента
```bash
curl -X GET http://veil-bird.ru/api/keys/{key_id}/config
```

### Удаление ключа
```bash
curl -X DELETE http://veil-bird.ru/api/keys/{key_id}
```

## Конфигурация клиента

### Параметры подключения
- **Протокол**: VLESS
- **Сервер**: veil-bird.ru
- **Порт**: 443
- **Безопасность**: Reality
- **SNI**: www.microsoft.com
- **Fingerprint**: Chrome

### Поддерживаемые клиенты
- **Android**: V2rayNG, SagerNet
- **iOS**: Shadowrocket, Quantumult X
- **Windows**: V2rayN, Clash
- **macOS**: V2rayX, ClashX
- **Linux**: V2ray, Clash

### Пример конфигурации
```
vless://[UUID]@veil-bird.ru:443?encryption=none&security=reality&sni=www.microsoft.com&fp=chrome&pbk=[PUBLIC_KEY]&sid=[SHORT_ID]&spx=/&type=tcp&flow=#[NAME]
```

## Управление сервисами

### Перезапуск всех сервисов
```bash
./manage.sh restart
```

### Просмотр логов
```bash
# Логи Xray
./manage.sh logs xray

# Логи API
./manage.sh logs api

# Логи Nginx
./manage.sh logs nginx
```

### Статистика сервера
```bash
./manage.sh stats
```

## Безопасность

### Рекомендации
1. Регулярно обновляйте ключи
2. Используйте уникальные имена для ключей
3. Удаляйте неиспользуемые ключи
4. Мониторьте логи на предмет подозрительной активности

### Мониторинг
```bash
# Проверка активных соединений
netstat -tlnp | grep :443

# Проверка использования ресурсов
./manage.sh stats

# Просмотр логов в реальном времени
./manage.sh logs xray
```

## Устранение неполадок

### Сервис не запускается
```bash
# Проверка статуса
systemctl status xray vpn-api nginx

# Перезапуск
./manage.sh restart

# Просмотр логов
./manage.sh logs xray
```

### API не отвечает
```bash
# Проверка API
curl -X GET http://localhost:8000/

# Проверка Nginx
curl -X GET http://veil-bird.ru/

# Просмотр логов
./manage.sh logs api
```

### Проблемы с подключением
1. Проверьте правильность конфигурации клиента
2. Убедитесь, что ключ активен
3. Проверьте статус сервера
4. Просмотрите логи Xray

## Обновление

### Обновление Xray
```bash
cd /usr/local/bin
wget -O xray.zip https://github.com/XTLS/Xray-core/releases/download/latest/Xray-linux-64.zip
unzip -o xray.zip
chmod +x xray
systemctl restart xray
```

### Обновление API
```bash
cd /root/vpn-server
source venv/bin/activate
pip install --upgrade fastapi uvicorn
systemctl restart vpn-api
```

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи: `./manage.sh logs xray`
2. Проверьте статус сервисов: `./manage.sh status`
3. Проверьте конфигурацию: `/root/vpn-server/config/config.json`
4. Обратитесь к документации: `http://veil-bird.ru/docs` 