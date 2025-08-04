#!/usr/bin/env python3
"""
Скрипт миграции существующих ключей на систему с индивидуальными портами
"""

import json
import os
import sys
import time
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from port_manager import port_manager
from xray_config_manager import xray_config_manager
from port_traffic_monitor import port_traffic_monitor

def load_keys():
    """Загрузка ключей из файла"""
    keys_file = "/root/vpn-server/config/keys.json"
    if not os.path.exists(keys_file):
        return []
    
    with open(keys_file, 'r') as f:
        return json.load(f)

def save_keys(keys):
    """Сохранение ключей в файл"""
    keys_file = "/root/vpn-server/config/keys.json"
    with open(keys_file, 'w') as f:
        json.dump(keys, f, indent=2)

def backup_keys():
    """Создание резервной копии ключей"""
    keys_file = "/root/vpn-server/config/keys.json"
    if not os.path.exists(keys_file):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"/root/vpn-server/config/keys_backup_{timestamp}.json"
    
    with open(keys_file, 'r') as src:
        with open(backup_file, 'w') as dst:
            dst.write(src.read())
    
    return backup_file

def migrate_keys_to_ports():
    """Миграция ключей на систему с портами"""
    print("=== МИГРАЦИЯ КЛЮЧЕЙ НА СИСТЕМУ С ПОРТАМИ ===")
    print()
    
    # Создаем резервную копию
    backup_file = backup_keys()
    if backup_file:
        print(f"✅ Создана резервная копия: {backup_file}")
    else:
        print("⚠️  Не удалось создать резервную копию")
    
    # Загружаем существующие ключи
    keys = load_keys()
    if not keys:
        print("ℹ️  Нет ключей для миграции")
        return True
    
    print(f"📋 Найдено {len(keys)} ключей для миграции")
    print()
    
    # Проверяем лимит портов
    if len(keys) > 20:
        print("❌ Ошибка: Количество ключей превышает лимит портов (20)")
        return False
    
    migrated_count = 0
    failed_count = 0
    
    for i, key in enumerate(keys, 1):
        print(f"🔄 Миграция ключа {i}/{len(keys)}: {key['name']} ({key['uuid'][:8]}...)")
        
        try:
            # Назначаем порт для ключа
            assigned_port = port_manager.assign_port(
                key["uuid"], 
                key["id"], 
                key["name"]
            )
            
            if not assigned_port:
                print(f"❌ Не удалось назначить порт для ключа {key['name']}")
                failed_count += 1
                continue
            
            # Добавляем порт в данные ключа
            key["port"] = assigned_port
            
            # Добавляем ключ в конфигурацию Xray
            if not xray_config_manager.add_key_to_config(key["uuid"], key["name"]):
                print(f"❌ Не удалось добавить ключ {key['name']} в конфигурацию Xray")
                # Откатываем назначение порта
                port_manager.release_port(key["uuid"])
                failed_count += 1
                continue
            
            print(f"✅ Ключ {key['name']} успешно мигрирован на порт {assigned_port}")
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Ошибка при миграции ключа {key['name']}: {e}")
            failed_count += 1
    
    print()
    print("=== РЕЗУЛЬТАТЫ МИГРАЦИИ ===")
    print(f"✅ Успешно мигрировано: {migrated_count}")
    print(f"❌ Ошибок: {failed_count}")
    print(f"📊 Всего ключей: {len(keys)}")
    
    if migrated_count > 0:
        # Сохраняем обновленные ключи
        save_keys(keys)
        print("💾 Обновленные ключи сохранены")
        
        # Показываем статус портов
        print()
        print("=== СТАТУС ПОРТОВ ===")
        port_assignments = port_manager.get_all_assignments()
        used_count = port_manager.get_used_ports_count()
        available_count = port_manager.get_available_ports_count()
        
        print(f"🔌 Использовано портов: {used_count}")
        print(f"🔓 Свободных портов: {available_count}")
        print(f"📋 Назначения портов:")
        
        for uuid, assignment in port_assignments["port_assignments"].items():
            print(f"   Порт {assignment['port']} → {assignment['key_name']} ({uuid[:8]}...)")
    
    return failed_count == 0

def validate_migration():
    """Валидация результатов миграции"""
    print()
    print("=== ВАЛИДАЦИЯ МИГРАЦИИ ===")
    
    # Проверяем ключи
    keys = load_keys()
    print(f"📋 Загружено ключей: {len(keys)}")
    
    # Проверяем порты
    port_assignments = port_manager.get_all_assignments()
    print(f"🔌 Назначено портов: {len(port_assignments['port_assignments'])}")
    
    # Проверяем соответствие
    keys_with_ports = [k for k in keys if k.get("port")]
    print(f"🔗 Ключей с портами: {len(keys_with_ports)}")
    
    # Проверяем конфигурацию Xray
    config_status = xray_config_manager.get_config_status()
    print(f"⚙️  Inbounds в конфигурации: {config_status.get('vless_inbounds', 0)}")
    
    # Валидация назначений портов
    validation = port_manager.validate_port_assignments()
    if validation["valid"]:
        print("✅ Назначения портов корректны")
    else:
        print("❌ Обнаружены проблемы с назначениями портов:")
        for issue in validation["issues"]:
            print(f"   - {issue}")
    
    return validation["valid"]

def main():
    """Основная функция"""
    print("🚀 Запуск миграции ключей на систему с индивидуальными портами")
    print("=" * 60)
    
    # Проверяем текущее состояние
    print("📊 Текущее состояние:")
    keys = load_keys()
    print(f"   Ключей: {len(keys)}")
    
    port_assignments = port_manager.get_all_assignments()
    print(f"   Назначено портов: {len(port_assignments['port_assignments'])}")
    
    if len(port_assignments["port_assignments"]) > 0:
        print("⚠️  Обнаружены существующие назначения портов")
        response = input("Продолжить миграцию? (y/N): ")
        if response.lower() != 'y':
            print("❌ Миграция отменена")
            return False
    
    print()
    
    # Выполняем миграцию
    success = migrate_keys_to_ports()
    
    if success:
        # Валидируем результаты
        validation_success = validate_migration()
        
        if validation_success:
            print()
            print("🎉 МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
            print("📝 Следующие шаги:")
            print("   1. Перезапустите Xray сервис")
            print("   2. Проверьте работу новых эндпоинтов API")
            print("   3. Протестируйте точный мониторинг трафика")
        else:
            print()
            print("⚠️  МИГРАЦИЯ ЗАВЕРШЕНА С ПРЕДУПРЕЖДЕНИЯМИ")
            print("📝 Рекомендуется проверить конфигурацию вручную")
    else:
        print()
        print("❌ МИГРАЦИЯ ЗАВЕРШЕНА С ОШИБКАМИ")
        print("📝 Проверьте логи и исправьте ошибки")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Миграция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1) 