#!/bin/bash

# Генерация ключей для Reality
echo "Генерация ключей Reality..."

# Генерация приватного ключа
PRIVATE_KEY=$(xray x25519)
echo "Приватный ключ: $PRIVATE_KEY"

# Генерация публичного ключа
PUBLIC_KEY=$(echo "$PRIVATE_KEY" | grep "Private key:" | awk '{print $3}')
echo "Публичный ключ: $(echo "$PRIVATE_KEY" | grep "Public key:" | awk '{print $3}')"

# Генерация короткого ID
SHORT_ID=$(openssl rand -hex 8)
echo "Короткий ID: $SHORT_ID"

# Сохранение ключей в файл
echo "PRIVATE_KEY=$PRIVATE_KEY" > /root/vpn-server/config/keys.env
echo "PUBLIC_KEY=$(echo "$PRIVATE_KEY" | grep "Public key:" | awk '{print $3}')" >> /root/vpn-server/config/keys.env
echo "SHORT_ID=$SHORT_ID" >> /root/vpn-server/config/keys.env

echo "Ключи сохранены в /root/vpn-server/config/keys.env" 