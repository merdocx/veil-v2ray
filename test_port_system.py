#!/usr/bin/env python3
"""
Скрипт тестирования системы мониторинга с индивидуальными портами
"""

import json
import os
import sys
import time
import requests
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from port_manager import port_manager
from xray_config_manager import xray_config_manager
from port_traffic_monitor import port_traffic_monitor

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

def test_port_manager():
    """Тестирование менеджера портов"""
    print("🔌 Тестирование менеджера портов...")
    
    # Тест получения доступного порта
    port = port_manager.get_available_port()
    if port:
        print(f"✅ Доступный порт: {port}")
    else:
        print("❌ Не удалось получить доступный порт")
        return False
    
    # Тест назначения порта
    test_uuid = "test-uuid-123"
    test_key_id = "test-key-123"
    test_name = "Test Key"
    
    assigned_port = port_manager.assign_port(test_uuid, test_key_id, test_name)
    if assigned_port:
        print(f"✅ Порт {assigned_port} назначен для {test_name}")
    else:
        print("❌ Не удалось назначить порт")
        return False
    
    # Тест получения порта для UUID
    retrieved_port = port_manager.get_port_for_uuid(test_uuid)
    if retrieved_port == assigned_port:
        print(f"✅ Порт {retrieved_port} корректно получен для UUID")
    else:
        print(f"❌ Несоответствие портов: {retrieved_port} != {assigned_port}")
        return False
    
    # Тест освобождения порта
    if port_manager.release_port(test_uuid):
        print("✅ Порт успешно освобожден")
    else:
        print("❌ Не удалось освободить порт")
        return False
    
    print("✅ Менеджер портов работает корректно")
    return True

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

def test_port_traffic_monitor():
    """Тестирование монитора трафика портов"""
    print("📊 Тестирование монитора трафика портов...")
    
    # Тест получения системной сводки
    system_summary = port_traffic_monitor.get_system_traffic_summary()
    if "error" not in system_summary:
        print(f"✅ Системная сводка получена: {system_summary.get('active_ports', 0)} активных портов")
    else:
        print(f"❌ Ошибка получения системной сводки: {system_summary['error']}")
        return False
    
    # Тест получения трафика всех портов
    all_traffic = port_traffic_monitor.get_all_ports_traffic()
    if "error" not in all_traffic:
        print(f"✅ Трафик всех портов получен: {all_traffic.get('total_ports', 0)} портов")
    else:
        print(f"❌ Ошибка получения трафика портов: {all_traffic['error']}")
        return False
    
    # Тест получения трафика конкретного порта
    test_port = 10001
    port_traffic = port_traffic_monitor.get_port_traffic(test_port)
    if "error" not in port_traffic:
        print(f"✅ Трафик порта {test_port} получен: {port_traffic.get('total_bytes', 0)} байт")
    else:
        print(f"❌ Ошибка получения трафика порта: {port_traffic['error']}")
        return False
    
    print("✅ Монитор трафика портов работает корректно")
    return True

def test_api_endpoints():
    """Тестирование API эндпоинтов"""
    print("🌐 Тестирование API эндпоинтов...")
    
    # Тест получения статуса портов
    ports_status = make_api_request("/api/system/ports")
    if ports_status:
        print(f"✅ Статус портов получен: {ports_status.get('used_ports', 0)} использовано")
    else:
        print("❌ Не удалось получить статус портов")
        return False
    
    # Тест получения системной сводки трафика
    traffic_summary = make_api_request("/api/system/traffic/summary")
    if traffic_summary:
        print("✅ Системная сводка трафика получена")
    else:
        print("❌ Не удалось получить системную сводку трафика")
        return False
    
    # Тест получения статуса конфигурации Xray
    xray_status = make_api_request("/api/system/xray/config-status")
    if xray_status:
        print("✅ Статус конфигурации Xray получен")
    else:
        print("❌ Не удалось получить статус конфигурации Xray")
        return False
    
    print("✅ API эндпоинты работают корректно")
    return True

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
        ("Менеджер портов", test_port_manager),
        ("Менеджер конфигурации Xray", test_xray_config_manager),
        ("Монитор трафика портов", test_port_traffic_monitor),
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