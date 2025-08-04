#!/usr/bin/env python3
import json
import sys
import os
import subprocess

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
    short_id = reality_settings['shortIds'][0]
    server_names = reality_settings['serverNames']
    
    # Генерация публичного ключа из приватного
    try:
        result = subprocess.run([
            '/usr/local/bin/xray', 'x25519', '-i', private_key
        ], capture_output=True, text=True, check=True)
        
        # Извлекаем публичный ключ из вывода
        public_key = None
        for line in result.stdout.split('\n'):
            if 'Public key:' in line:
                public_key = line.split(':')[1].strip()
                break
        
        if not public_key:
            print("Ошибка: не удалось извлечь публичный ключ")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"Ошибка генерации публичного ключа: {e}")
        sys.exit(1)
    

    
    # Определение порта
    if port is None:
        # Если порт не передан, используем 443 (для обратной совместимости)
        port = 443
    
    # Создание конфигурации клиента
    client_config = {
        "v": "2",
        "ps": f"VLESS+Reality - {key_name}",
        "add": "veil-bird.ru",
        "port": str(port),
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
    vless_url = f"vless://{key_uuid}@veil-bird.ru:{port}?encryption=none&security=reality&sni={server_names[0]}&fp=chrome&pbk={public_key}&sid={short_id}&spx=/&type=tcp&flow=#{key_name}"
    
    return {
        "config": client_config,
        "vless_url": vless_url,
        "qr_code_data": vless_url
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 generate_client_config.py <key_uuid> <key_name> [port]")
        sys.exit(1)
    
    key_uuid = sys.argv[1]
    key_name = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    result = generate_client_config(key_uuid, key_name, port)
    
    print("=== Конфигурация клиента ===")
    print(f"Имя: {key_name}")
    print(f"UUID: {key_uuid}")
    print(f"Порт: {result['config']['port']}")
    print(f"VLESS URL: {result['vless_url']}")
    print("\n=== QR код данные ===")
    print(result['qr_code_data']) 