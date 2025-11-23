#!/usr/bin/env python3
import json
import sys
import os

def generate_client_config(key_uuid, key_name, port=None):
    """Генерация конфигурации клиента для VLESS+Reality"""
    
    # Загрузка конфигурации сервера
    with open('/root/vpn-server/config/config.json', 'r') as f:
        server_config = json.load(f)
    
    # Поиск правильного inbound для данного ключа
    vless_inbound = None
    for inbound in server_config['inbounds']:
        if (inbound.get('protocol') == 'vless' and 
            'streamSettings' in inbound and
            'settings' in inbound and
            'clients' in inbound['settings']):
            
            # Проверяем, есть ли наш ключ в этом inbound
            for client in inbound['settings']['clients']:
                if client.get('id') == key_uuid:
                    vless_inbound = inbound
                    break
            if vless_inbound:
                break
    
    if not vless_inbound:
        print("Ошибка: не найден VLESS inbound для данного ключа")
        sys.exit(1)
    
    # Извлечение параметров Reality из найденного inbound
    reality_settings = vless_inbound['streamSettings']['realitySettings']
    private_key = reality_settings['privateKey']
    
    # Используем shortId из конфигурации Xray (индивидуальный для каждого ключа)
    # Это гарантирует, что short_id в ссылке совпадает с конфигурацией Xray
    short_ids = reality_settings.get('shortIds', [])
    if not short_ids:
        print("Ошибка: shortIds не найдены в конфигурации Reality")
        sys.exit(1)
    short_id = short_ids[0]  # Используем первый shortId из конфигурации (индивидуальный для ключа)
    
    server_names = reality_settings['serverNames']
    
    # Используем SNI из БД, если он сохранен (выбирался случайно при создании ключа)
    # Если SNI нет в БД (старые ключи), используем первый из списка как fallback
    from storage.sqlite_storage import storage
    key_from_db = None
    keys = storage.get_all_keys()
    for k in keys:
        if k.get('uuid') == key_uuid:
            key_from_db = k
            break
    
    # Используем фиксированный SNI для всех ключей (iOS и Android совместимость)
    sni = "www.microsoft.com"  # Фиксированный для всех
    
    # Загрузка публичного ключа из keys.env
    public_key = None
    try:
        with open('/root/vpn-server/config/keys.env', 'r') as f:
            for line in f:
                if line.startswith('PUBLIC_KEY='):
                    public_key = line.split('=', 1)[1].strip()
                    break
    except FileNotFoundError:
        pass
    
    if not public_key:
        print("Ошибка: не удалось найти публичный ключ")
        sys.exit(1)
    
    # Получение домена сервера
    server_ip = "veil-bird.ru"  # Домен сервера
    
    # Использование порта из inbound, если не указан
    if not port:
        port = vless_inbound['port']
    
    # Генерация VLESS URL с фиксированными параметрами для iOS и Android совместимости
    # Используем fp=chrome для лучшей совместимости с v2raytun на Android
    vless_url = f"vless://{key_uuid}@{server_ip}:{port}?type=tcp&security=reality&encryption=none&fp=chrome&pbk={public_key}&sid={short_id}&sni={sni}#{key_name}"
    
    return vless_url

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 generate_client_config.py <uuid> <name> [port]")
        sys.exit(1)
    
    key_uuid = sys.argv[1]
    key_name = sys.argv[2]
    port = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        config = generate_client_config(key_uuid, key_name, port)
        print(config)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)