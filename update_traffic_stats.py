#!/usr/bin/env python3
"""
Скрипт для периодического обновления статистики трафика из Xray Stats API
Запускается через systemd timer
"""

import sys
import os
import json
import logging
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traffic_history_manager import traffic_history

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/vpn-server/logs/traffic_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_keys():
    """Загрузка ключей"""
    keys_file = "/root/vpn-server/config/keys.json"
    try:
        with open(keys_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading keys: {e}")
        return []

def main():
    """Основная функция обновления статистики"""
    logger.info("=== Обновление статистики трафика ===")
    
    keys = load_keys()
    active_keys = [k for k in keys if k.get("is_active", True)]
    
    logger.info(f"Обновление статистики для {len(active_keys)} активных ключей")
    
    updated_count = 0
    error_count = 0
    
    for key in active_keys:
        try:
            uuid = key.get("uuid")
            name = key.get("name")
            port = key.get("port", 0)
            
            if not uuid:
                logger.warning(f"Ключ {name} не имеет UUID, пропускаем")
                continue
            
            # Обновляем статистику (использует Xray Stats API если доступен)
            traffic_history.update_key_traffic(uuid, name, port)
            updated_count += 1
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики для ключа {key.get('name', 'unknown')}: {e}")
            error_count += 1
    
    logger.info(f"Обновление завершено: {updated_count} успешно, {error_count} ошибок")
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

