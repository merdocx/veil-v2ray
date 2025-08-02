#!/usr/bin/env python3
import json
import sys
import os

def generate_client_config(key_uuid, key_name):
    """Генерация конфигурации клиента для VLESS+Reality"""
    
    # Загрузка ключей сервера
    with open('/root/vpn-server/config/keys.env', 'r') as f:
        keys_content = f.read()
    
    # Извлечение публичного ключа
    public_key = None
    for line in keys_content.split('\n'):
        if line.startswith('PUBLIC_KEY='):
            public_key = line.split('=')[1]
            break
    
    if not public_key:
        print("Ошибка: не удалось найти публичный ключ")
        sys.exit(1)
    
    # Загрузка конфигурации сервера
    with open('/root/vpn-server/config/config.json', 'r') as f:
        server_config = json.load(f)
    
    # Извлечение параметров Reality
    reality_settings = server_config['inbounds'][0]['streamSettings']['realitySettings']
    short_id = reality_settings['shortIds'][0]
    server_names = reality_settings['serverNames']
    
    # Создание конфигурации клиента
    client_config = {
        "v": "2",
        "ps": f"VLESS+Reality - {key_name}",
        "add": "veil-bird.ru",
        "port": "443",
        "id": key_uuid,
        "aid": "0",
        "net": "tcp",
        "type": "http",
        "host": server_names[0],
        "path": "",
        "tls": "reality",
        "sni": server_names[0],
        "fp": "chrome",
        "pbk": public_key,
        "sid": short_id,
        "spx": "/"
    }
    
    # Генерация VLESS URL
    vless_url = f"vless://{key_uuid}@veil-bird.ru:443?encryption=none&security=reality&sni={server_names[0]}&fp=chrome&pbk={public_key}&sid={short_id}&spx=/&type=tcp&flow=#{key_name}"
    
    return {
        "config": client_config,
        "vless_url": vless_url,
        "qr_code_data": vless_url
    }

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python3 generate_client_config.py <key_uuid> <key_name>")
        sys.exit(1)
    
    key_uuid = sys.argv[1]
    key_name = sys.argv[2]
    
    result = generate_client_config(key_uuid, key_name)
    
    print("=== Конфигурация клиента ===")
    print(f"Имя: {key_name}")
    print(f"UUID: {key_uuid}")
    print(f"VLESS URL: {result['vless_url']}")
    print("\n=== QR код данные ===")
    print(result['qr_code_data']) 