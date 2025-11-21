#!/usr/bin/env python3
"""
Тестовый скрипт для проверки синхронизации short_id между БД и конфигурацией Xray
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.sqlite_storage import storage
from xray_config_manager import validate_xray_config_sync, sync_short_ids_from_db, xray_config_manager

def test_short_id_sync():
    """Тестирование синхронизации short_id"""
    print("=" * 80)
    print("ТЕСТ СИНХРОНИЗАЦИИ SHORT_ID")
    print("=" * 80)
    
    # 1. Загружаем ключи из БД
    print("\n1. Загрузка ключей из БД...")
    keys = storage.get_all_keys()
    print(f"   Найдено ключей: {len(keys)}")
    
    # Проверяем, сколько ключей имеют short_id
    keys_with_short_id = [k for k in keys if k.get("short_id")]
    print(f"   Ключей с short_id в БД: {len(keys_with_short_id)}")
    
    # 2. Валидация синхронизации
    print("\n2. Валидация синхронизации...")
    validation = validate_xray_config_sync(keys)
    
    print(f"   UUID синхронизированы: {validation.get('uuid_synced', False)}")
    print(f"   Short ID синхронизированы: {validation.get('short_id_synced', False)}")
    print(f"   Всего синхронизировано: {validation.get('synced', False)}")
    
    if validation.get('short_id_mismatches'):
        print(f"\n   ❌ Найдено несоответствий short_id: {len(validation['short_id_mismatches'])}")
        for mismatch in validation['short_id_mismatches'][:5]:  # Показываем первые 5
            print(f"      - UUID: {mismatch['uuid'][:8]}...")
            print(f"        Имя: {mismatch['name']}")
            print(f"        БД: {mismatch['db_short_id']}")
            print(f"        Конфиг: {mismatch['config_short_id']}")
    else:
        print("   ✅ Все short_id синхронизированы!")
    
    # 3. Синхронизация short_id
    if not validation.get('short_id_synced'):
        print("\n3. Синхронизация short_id из БД...")
        sync_result = sync_short_ids_from_db()
        
        if sync_result.get("success"):
            fixed_count = sync_result.get("fixed_count", 0)
            if fixed_count > 0:
                print(f"   ✅ Исправлено {fixed_count} несоответствий")
                for fixed_key in sync_result.get("fixed_keys", [])[:5]:
                    print(f"      - {fixed_key['name']}: {fixed_key['old_short_id']} -> {fixed_key['new_short_id']}")
            else:
                print("   ✅ Все short_id уже синхронизированы")
        else:
            print(f"   ❌ Ошибка синхронизации: {sync_result.get('error')}")
            return False
        
        # Повторная валидация
        print("\n4. Повторная валидация после синхронизации...")
        validation = validate_xray_config_sync(keys)
        print(f"   Short ID синхронизированы: {validation.get('short_id_synced', False)}")
    
    # 5. Проверка конфигурации Xray
    print("\n5. Проверка конфигурации Xray...")
    config = xray_config_manager._load_config()
    if config:
        vless_inbounds = [
            inbound for inbound in config.get("inbounds", [])
            if inbound.get("protocol") == "vless"
        ]
        print(f"   Найдено VLESS inbound'ов: {len(vless_inbounds)}")
        
        # Проверяем соответствие short_id
        db_keys_dict = {k["uuid"]: k for k in keys}
        matches = 0
        mismatches = 0
        
        for inbound in vless_inbounds:
            tag = inbound.get("tag", "")
            if tag.startswith("inbound-"):
                uuid_from_tag = tag.replace("inbound-", "")
                db_key = db_keys_dict.get(uuid_from_tag)
                
                if db_key:
                    config_short_ids = inbound.get("streamSettings", {}).get("realitySettings", {}).get("shortIds", [])
                    config_short_id = config_short_ids[0] if config_short_ids else None
                    db_short_id = db_key.get("short_id")
                    
                    if db_short_id == config_short_id:
                        matches += 1
                    else:
                        mismatches += 1
                        print(f"      ❌ Несоответствие для {db_key.get('name', 'unknown')}: БД={db_short_id}, Конфиг={config_short_id}")
        
        print(f"   ✅ Соответствий: {matches}")
        if mismatches > 0:
            print(f"   ❌ Несоответствий: {mismatches}")
    
    print("\n" + "=" * 80)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 80)
    
    return validation.get('synced', False)

if __name__ == "__main__":
    success = test_short_id_sync()
    sys.exit(0 if success else 1)


