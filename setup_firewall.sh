#!/bin/bash
# Скрипт для настройки безопасных firewall правил
# ВАЖНО: SSH доступ гарантирован!

set -e

echo "========================================="
echo "Настройка Firewall для VPN"
echo "========================================="

# Проверяем SSH доступ ДО применения правил
SSH_PORT=22
echo "Проверка SSH на порту $SSH_PORT..."
if ss -tlnp | grep -q ":${SSH_PORT}"; then
    echo "✅ SSH работает на порту $SSH_PORT"
else
    echo "❌ ОШИБКА: SSH не найден на порту $SSH_PORT"
    exit 1
fi

# Сохраняем текущие правила (на всякий случай)
echo "Сохранение текущих правил..."
iptables-save > /root/iptables_backup_$(date +%Y%m%d_%H%M%S).rules
echo "✅ Бэкап создан"

# Создаем цепочку для VPN правил (если не существует)
if ! iptables -L VPN_INPUT >/dev/null 2>&1; then
    iptables -N VPN_INPUT
    echo "✅ Создана цепочка VPN_INPUT"
fi

# Очищаем цепочку VPN_INPUT (если есть старые правила)
iptables -F VPN_INPUT 2>/dev/null || true

# ВАЖНО: Сначала разрешаем SSH в основной цепочке INPUT
echo "Настройка правил..."
iptables -I INPUT 1 -p tcp --dport $SSH_PORT -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
echo "✅ SSH порт $SSH_PORT разрешен (правило #1 в INPUT)"

# Разрешаем все установленные и связанные соединения
iptables -I INPUT 2 -m state --state ESTABLISHED,RELATED -j ACCEPT
echo "✅ Установленные соединения разрешены (правило #2 в INPUT)"

# ВАЖНО: Правильный порядок правил для VPN портов
# 1. Сначала разрешаем установленные соединения (критично!)
iptables -A VPN_INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 2. Разрешаем loopback
iptables -A VPN_INPUT -i lo -j ACCEPT

# 3. Разрешаем localhost
iptables -A VPN_INPUT -s 127.0.0.1 -j ACCEPT

# 4. Защита от SYN flood
iptables -A VPN_INPUT -p tcp --dport 10001:10100 --syn -m limit --limit 5/second --limit-burst 10 -j ACCEPT

# 5. Разрешаем новые соединения с rate limiting
iptables -A VPN_INPUT -p tcp --dport 10001:10100 -m state --state NEW -m limit --limit 10/minute --limit-burst 20 -j ACCEPT

# 6. Ограничение соединений с одного IP (в конце, чтобы не блокировать установленные)
# Увеличено до 100 для активных пользователей (множество вкладок/приложений)
iptables -A VPN_INPUT -p tcp --dport 10001:10100 -m connlimit --connlimit-above 100 --connlimit-mask 32 -j REJECT --reject-with tcp-reset

# Применяем цепочку VPN_INPUT к VPN портам
iptables -I INPUT 3 -p tcp --dport 10001:10100 -j VPN_INPUT
echo "✅ VPN правила применены (правило #3 в INPUT)"

# Проверяем SSH ДОПОЛНИТЕЛЬНО
echo ""
echo "Проверка SSH после применения правил..."
if iptables -C INPUT -p tcp --dport $SSH_PORT -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT 2>/dev/null; then
    echo "✅ SSH правило подтверждено"
else
    echo "⚠️  SSH правило требует проверки"
fi

# Показываем правила для проверки
echo ""
echo "Проверка правил INPUT (первые 10):"
iptables -L INPUT -n -v --line-numbers | head -15

echo ""
echo "========================================="
echo "✅ Firewall правила применены"
echo "========================================="
echo ""
echo "ВАЖНО: SSH доступ сохранен!"
echo "Правила применены в порядке:"
echo "  1. SSH (порт $SSH_PORT) - разрешен"
echo "  2. Установленные соединения - разрешены"
echo "  3. VPN порты (10001-10100) - с ограничениями"

