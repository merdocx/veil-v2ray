#!/usr/bin/env python3
"""
Тестирование системы портов и мониторинга трафика
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from port_manager import PortManager
from xray_config_manager import XrayConfigManager
# Удаляем импорт несуществующего модуля
# from port_traffic_monitor import port_traffic_monitor

# Конфигурация API
API_BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("VPN_API_KEY")
if not API_KEY:
    raise ValueError("VPN_API_KEY environment variable is required")

def make_api_request(endpoint, method="GET", data=None):
    """Выполнение запроса к API"""
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

def test_port_system():
    """Тестирование системы портов"""
    print("🔌 Тестирование системы портов...")
    
    try:
        # Создаем экземпляр менеджера портов
        port_manager = PortManager()
        
        # Получаем статистику портов
        used_count = port_manager.get_used_ports_count()
        available_count = port_manager.get_available_ports_count()
        
        print(f"✅ Использовано портов: {used_count}")
        print(f"✅ Доступно портов: {available_count}")
        
        # Получаем все назначения
        assignments = port_manager.get_all_assignments()
        print(f"✅ Назначений портов: {len(assignments.get('port_assignments', {}))}")
        
        # Валидация назначений
        validation = port_manager.validate_port_assignments()
        if validation["valid"]:
            print("✅ Назначения портов корректны")
        else:
            print(f"❌ Ошибки в назначениях: {validation['errors']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования системы портов: {e}")
        return False

def test_xray_config_manager():
    """Тестирование менеджера конфигурации Xray"""
    print("⚙️  Тестирование менеджера конфигурации Xray...")
    
    # Тест получения статуса конфигурации
    config_status = xray_config_manager.get_config_status()
    if "error" not in config_status:
        print(f"✅ Статус конфигурации получен: {config_status.get('vless_inbounds', 0)} inbounds")
    else:
        print(f"❌ Ошибка получения статуса: {config_status['error']}")
        return False
    
    # Тест создания inbound конфигурации
    test_uuid = "test-config-uuid"
    test_name = "Test Config Key"
    
    # Назначаем порт для теста
    port_manager.assign_port(test_uuid, "test-config-key-id", test_name)
    
    inbound = xray_config_manager.create_inbound_for_key(test_uuid, test_name)
    if inbound:
        print(f"✅ Inbound конфигурация создана для порта {inbound['port']}")
        
        # Проверяем структуру конфигурации
        required_fields = ["port", "protocol", "settings", "streamSettings"]
        for field in required_fields:
            if field in inbound:
                print(f"   ✅ Поле {field} присутствует")
            else:
                print(f"   ❌ Поле {field} отсутствует")
                return False
    else:
        print("❌ Не удалось создать inbound конфигурацию")
        return False
    
    # Очищаем тестовые данные
    port_manager.release_port(test_uuid)
    
    print("✅ Менеджер конфигурации Xray работает корректно")
    return True

def test_api_endpoints():
    """Тестирование API эндпоинтов"""
    print("🌐 Тестирование API эндпоинтов...")
    
    try:
        # Тест получения списка ключей
        keys_response = make_api_request("/api/keys")
        if keys_response:
            print(f"✅ Список ключей получен: {len(keys_response)} ключей")
        else:
            print("❌ Не удалось получить список ключей")
            return False
        
        # Тест получения статуса портов
        ports_response = make_api_request("/api/system/ports")
        if ports_response:
            print(f"✅ Статус портов получен: {ports_response.get('used_count', 0)} использовано")
        else:
            print("❌ Не удалось получить статус портов")
            return False
        
        # Тест получения простого трафика
        traffic_response = make_api_request("/api/traffic/simple")
        if traffic_response:
            print(f"✅ Простой трафик получен: {traffic_response.get('data', {}).get('total_connections', 0)} соединений")
        else:
            print("❌ Не удалось получить простой трафик")
            return False
        
        # Тест получения трафика конкретного ключа (если есть ключи)
        if keys_response:
            key_id = keys_response[0]["id"]
            key_traffic_response = make_api_request(f"/api/keys/{key_id}/traffic/simple")
            if key_traffic_response:
                print(f"✅ Трафик ключа {key_id} получен")
            else:
                print(f"❌ Не удалось получить трафик ключа {key_id}")
                return False
        
        print("✅ API эндпоинты работают корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")
        return False

def test_key_creation_and_deletion():
    """Тестирование создания и удаления ключей"""
    print("🔑 Тестирование создания и удаления ключей...")
    
    # Создаем тестовый ключ
    test_key_data = {"name": f"Test Key {int(time.time())}"}
    new_key = make_api_request("/api/keys", method="POST", data=test_key_data)
    
    if new_key and "id" in new_key:
        print(f"✅ Ключ создан: {new_key['name']} (порт: {new_key.get('port', 'N/A')})")
        key_id = new_key["id"]
        
        # Получаем список ключей
        keys_list = make_api_request("/api/keys")
        if keys_list:
            print(f"✅ Список ключей получен: {len(keys_list)} ключей")
        
        # Получаем трафик ключа по порту
        port_traffic = make_api_request(f"/api/keys/{key_id}/traffic/port/exact")
        if port_traffic:
            print("✅ Трафик ключа по порту получен")
        
        # Удаляем тестовый ключ
        delete_result = make_api_request(f"/api/keys/{key_id}", method="DELETE")
        if delete_result:
            print("✅ Ключ успешно удален")
        else:
            print("❌ Не удалось удалить ключ")
            return False
    else:
        print("❌ Не удалось создать тестовый ключ")
        return False
    
    print("✅ Создание и удаление ключей работает корректно")
    return True

def run_all_tests():
    """Запуск всех тестов"""
    print("🧪 ЗАПУСК ТЕСТИРОВАНИЯ СИСТЕМЫ С ПОРТАМИ")
    print("=" * 50)
    
    tests = [
        ("Менеджер портов", test_port_system),
        ("Менеджер конфигурации Xray", test_xray_config_manager),
        ("API эндпоинты", test_api_endpoints),
        ("Создание и удаление ключей", test_key_creation_and_deletion)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 Тест: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                print(f"✅ {test_name}: ПРОЙДЕН")
                passed += 1
            else:
                print(f"❌ {test_name}: ПРОВАЛЕН")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ОШИБКА - {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📈 Успешность: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print(f"\n⚠️  {failed} ТЕСТОВ ПРОВАЛЕНО")
        return False

def main():
    """Основная функция"""
    print("🚀 Запуск тестирования системы мониторинга с индивидуальными портами")
    print("=" * 60)
    
    # Проверяем доступность API
    print("🔍 Проверка доступности API...")
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ API доступен")
        else:
            print(f"❌ API недоступен (статус: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API недоступен: {e}")
        return False
    
    # Запускаем тесты
    success = run_all_tests()
    
    if success:
        print("\n🎯 СИСТЕМА ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
        print("📝 Рекомендации:")
        print("   - Проверьте работу Xray сервиса")
        print("   - Протестируйте подключение клиентов")
        print("   - Мониторьте точность трафика")
    else:
        print("\n🔧 ТРЕБУЕТСЯ ДОРАБОТКА!")
        print("📝 Проверьте:")
        print("   - Логи системы")
        print("   - Конфигурацию Xray")
        print("   - Настройки портов")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1) 