#!/usr/bin/env python3
"""
Скрипт проверки безопасности VPN API
"""

import os
import subprocess
import requests
import json
from datetime import datetime

def check_env_file():
    """Проверка файла .env"""
    print("🔍 Проверка файла .env...")
    
    env_file = "/root/vpn-server/.env"
    if not os.path.exists(env_file):
        print("❌ Файл .env не найден!")
        return False
    
    # Проверяем права доступа
    stat = os.stat(env_file)
    if stat.st_mode & 0o777 != 0o600:
        print(f"⚠️  Небезопасные права доступа к .env: {oct(stat.st_mode & 0o777)}")
        print("   Рекомендуется: chmod 600 .env")
    else:
        print("✅ Безопасные права доступа к .env")
    
    # Проверяем наличие API ключа
    with open(env_file, 'r') as f:
        content = f.read()
        if 'VPN_API_KEY=' in content:
            print("✅ API ключ найден в .env")
            return True
        else:
            print("❌ API ключ не найден в .env")
            return False

def check_ssl_certificates():
    """Проверка SSL сертификатов"""
    print("\n🔍 Проверка SSL сертификатов...")
    
    cert_file = "/etc/ssl/certs/vpn-api.crt"
    key_file = "/etc/ssl/private/vpn-api.key"
    
    if not os.path.exists(cert_file):
        print("❌ SSL сертификат не найден")
        return False
    
    if not os.path.exists(key_file):
        print("❌ SSL ключ не найден")
        return False
    
    # Проверяем права доступа
    cert_stat = os.stat(cert_file)
    key_stat = os.stat(key_file)
    
    if cert_stat.st_mode & 0o777 != 0o644:
        print(f"⚠️  Небезопасные права доступа к сертификату: {oct(cert_stat.st_mode & 0o777)}")
    else:
        print("✅ Безопасные права доступа к сертификату")
    
    if key_stat.st_mode & 0o777 != 0o600:
        print(f"⚠️  Небезопасные права доступа к ключу: {oct(key_stat.st_mode & 0o777)}")
    else:
        print("✅ Безопасные права доступа к ключу")
    
    print("✅ SSL сертификаты найдены")
    return True

def check_api_https():
    """Проверка HTTPS API"""
    print("\n🔍 Проверка HTTPS API...")
    
    try:
        # Проверяем локальный HTTPS
        response = requests.get(
            "https://localhost:8000/api/keys",
            headers={"X-API-Key": os.getenv("VPN_API_KEY")},
            verify=False,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ HTTPS API работает локально")
        else:
            print(f"⚠️  HTTPS API вернул статус: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки HTTPS API: {e}")
        return False
    
    return True

def check_nginx_https():
    """Проверка Nginx HTTPS"""
    print("\n🔍 Проверка Nginx HTTPS...")
    
    try:
        # Проверяем внешний HTTPS через Nginx
        response = requests.get(
            "https://veil-bird.ru/api/keys",
            headers={"X-API-Key": os.getenv("VPN_API_KEY")},
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Nginx HTTPS работает")
        else:
            print(f"⚠️  Nginx HTTPS вернул статус: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки Nginx HTTPS: {e}")
        return False
    
    return True

def check_services():
    """Проверка сервисов"""
    print("\n🔍 Проверка сервисов...")
    
    services = ['vpn-api', 'nginx', 'xray']
    all_active = True
    
    for service in services:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip() == 'active':
                print(f"✅ Сервис {service} активен")
            else:
                print(f"❌ Сервис {service} неактивен")
                all_active = False
                
        except Exception as e:
            print(f"❌ Ошибка проверки сервиса {service}: {e}")
            all_active = False
    
    return all_active

def check_ports():
    """Проверка открытых портов"""
    print("\n🔍 Проверка открытых портов...")
    
    try:
        result = subprocess.run(
            ['netstat', '-tlnp'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            
            # Проверяем порты API
            api_ports = ['8000', '443', '80']
            all_ports_open = True
            
            for port in api_ports:
                found = False
                for line in lines:
                    if f':{port}' in line:
                        found = True
                        print(f"✅ Порт {port} открыт: {line.split()[-1]}")
                        break
                
                if not found:
                    print(f"⚠️  Порт {port} не найден")
                    all_ports_open = False
            
            return all_ports_open
        else:
            print("❌ Ошибка выполнения netstat")
            return False
                    
    except Exception as e:
        print(f"❌ Ошибка проверки портов: {e}")
        return False

def main():
    print("🔒 ПРОВЕРКА БЕЗОПАСНОСТИ VPN API")
    print("=" * 50)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Загружаем переменные окружения
    env_file = "/root/vpn-server/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Выполняем проверки
    checks = [
        check_env_file,
        check_ssl_certificates,
        check_api_https,
        check_nginx_https,
        check_services,
        check_ports
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result if result is not None else False)
        except Exception as e:
            print(f"❌ Ошибка выполнения проверки: {e}")
            results.append(False)
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Пройдено проверок: {passed}/{total}")
    print(f"📈 Процент успеха: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 Все проверки безопасности пройдены успешно!")
    else:
        print("⚠️  Обнаружены проблемы безопасности. Рекомендуется исправить.")

if __name__ == "__main__":
    main() 