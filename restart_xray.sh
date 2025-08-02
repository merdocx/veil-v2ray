#!/bin/bash

# Скрипт для перезапуска Xray после изменения конфигурации

echo "Перезапуск Xray..."
systemctl restart xray

# Проверяем статус
if systemctl is-active --quiet xray; then
    echo "✅ Xray успешно перезапущен"
else
    echo "❌ Ошибка перезапуска Xray"
    exit 1
fi 