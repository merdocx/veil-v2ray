#!/usr/bin/env python3
"""
Скрипт для генерации нового API ключа
"""

import secrets
import base64
import os

def generate_api_key():
    """Генерация нового API ключа"""
    # Генерируем 32 байта случайных данных
    random_bytes = secrets.token_bytes(32)
    # Кодируем в base64
    api_key = base64.b64encode(random_bytes).decode('utf-8')
    return api_key

def update_env_file(api_key):
    """Обновление .env файла с новым API ключом"""
    env_file = "/root/vpn-server/.env"
    
    if not os.path.exists(env_file):
        print(f"❌ Файл {env_file} не найден!")
        return False
    
    # Читаем текущий файл
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Обновляем API ключ
    updated_lines = []
    for line in lines:
        if line.startswith('VPN_API_KEY='):
            updated_lines.append(f'VPN_API_KEY={api_key}\n')
        else:
            updated_lines.append(line)
    
    # Записываем обновленный файл
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    return True

def main():
    print("🔑 Генерация нового API ключа...")
    
    # Генерируем новый ключ
    new_api_key = generate_api_key()
    print(f"✅ Новый API ключ: {new_api_key}")
    
    # Обновляем .env файл
    if update_env_file(new_api_key):
        print("✅ .env файл обновлен")
    else:
        print("❌ Ошибка обновления .env файла")
        return
    
    print("\n📋 Инструкции:")
    print("1. Перезапустите API сервис: systemctl restart vpn-api")
    print("2. Обновите все клиенты с новым API ключом")
    print("3. Удалите старый API ключ из всех мест")
    
    print(f"\n🔐 Новый API ключ для использования:")
    print(f"X-API-Key: {new_api_key}")

if __name__ == "__main__":
    main() 