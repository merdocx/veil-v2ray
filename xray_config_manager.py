#!/usr/bin/env python3
"""
Модуль управления конфигурацией Xray с индивидуальными портами
"""

import json
import os
import subprocess
import secrets
import string
from typing import Dict, List, Optional
from datetime import datetime

from port_manager import port_manager

class XrayConfigManager:
    def __init__(self, config_file: str = "/root/vpn-server/config/config.json"):
        self.config_file = config_file
        self.backup_dir = "/root/vpn-server/config/backups"
        
        # Создаем директорию для бэкапов
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _generate_reality_key(self) -> str:
        """Генерация приватного ключа Reality"""
        try:
            result = subprocess.run(
                ['/usr/local/bin/xray', 'x25519'],
                capture_output=True, text=True, check=True
            )
            # Извлекаем приватный ключ из вывода
            for line in result.stdout.split('\n'):
                if 'Private key:' in line:
                    return line.split(':')[1].strip()
        except Exception as e:
            print(f"Error generating Reality key: {e}")
        
        # Fallback: генерируем случайную строку
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(43))
    
    def _generate_short_id(self) -> str:
        """Генерация короткого ID для Reality"""
        return ''.join(secrets.choice(string.hexdigits.lower()) for _ in range(8))
    
    def _backup_config(self) -> str:
        """Создание резервной копии конфигурации"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"config_backup_{timestamp}.json")
        
        try:
            with open(self.config_file, 'r') as src:
                with open(backup_file, 'w') as dst:
                    dst.write(src.read())
            return backup_file
        except Exception as e:
            print(f"Error creating backup: {e}")
            return ""
    
    def _load_config(self) -> Dict:
        """Загрузка конфигурации Xray"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _save_config(self, config: Dict):
        """Сохранение конфигурации Xray"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
            raise
    
    def _validate_config(self, config: Dict) -> bool:
        """Валидация конфигурации Xray"""
        try:
            # Проверяем наличие основных секций
            required_sections = ["log", "inbounds", "outbounds"]
            for section in required_sections:
                if section not in config:
                    print(f"Missing required section: {section}")
                    return False
            
            # Проверяем inbounds
            if not config["inbounds"]:
                print("No inbounds configured")
                return False
            
            # Проверяем каждый inbound
            for inbound in config["inbounds"]:
                if "port" not in inbound:
                    print("Inbound missing port")
                    return False
                if "protocol" not in inbound:
                    print("Inbound missing protocol")
                    return False
                if "settings" not in inbound:
                    print("Inbound missing settings")
                    return False
            
            return True
        except Exception as e:
            print(f"Error validating config: {e}")
            return False
    
    def create_inbound_for_key(self, uuid: str, key_name: str) -> Optional[Dict]:
        """Создание inbound для ключа с индивидуальным портом"""
        # Получаем порт для ключа
        port = port_manager.get_port_for_uuid(uuid)
        if not port:
            print(f"No port assigned for UUID: {uuid}")
            return None
        
        # Генерируем уникальные ключи Reality
        private_key = self._generate_reality_key()
        short_id = self._generate_short_id()
        
        # Создаем inbound конфигурацию
        inbound = {
            "listen": "0.0.0.0",
            "port": port,
            "protocol": "vless",
            "settings": {
                "clients": [
                    {
                        "id": uuid,
                        "flow": "",
                        "email": uuid
                    }
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "www.microsoft.com:443",
                    "xver": 0,
                    "serverNames": ["www.microsoft.com"],
                    "privateKey": private_key,
                    "shortIds": [short_id],
                    "maxTimeDiff": 600
                }
            },
            "tag": f"inbound-{uuid}"
        }
        
        return inbound
    
    def add_key_to_config(self, uuid: str, key_name: str) -> bool:
        """Добавление ключа в конфигурацию Xray"""
        try:
            # Создаем резервную копию
            backup_file = self._backup_config()
            
            # Загружаем текущую конфигурацию
            config = self._load_config()
            if not config:
                return False
            
            # Создаем inbound для ключа
            inbound = self.create_inbound_for_key(uuid, key_name)
            if not inbound:
                return False
            
            # Добавляем inbound в конфигурацию
            config["inbounds"].append(inbound)
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            self._save_config(config)
            
            print(f"Added key {key_name} (UUID: {uuid}) to Xray config with port {inbound['port']}")
            return True
            
        except Exception as e:
            print(f"Error adding key to config: {e}")
            return False
    
    def remove_key_from_config(self, uuid: str) -> bool:
        """Удаление ключа из конфигурации Xray"""
        try:
            # Создаем резервную копию
            backup_file = self._backup_config()
            
            # Загружаем текущую конфигурацию
            config = self._load_config()
            if not config:
                return False
            
            # Находим и удаляем inbound для ключа
            original_count = len(config["inbounds"])
            config["inbounds"] = [
                inbound for inbound in config["inbounds"]
                if not (inbound.get("settings", {}).get("clients") and 
                       any(client.get("id") == uuid for client in inbound["settings"]["clients"]))
            ]
            
            if len(config["inbounds"]) == original_count:
                print(f"No inbound found for UUID: {uuid}")
                return False
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            self._save_config(config)
            
            print(f"Removed key with UUID {uuid} from Xray config")
            return True
            
        except Exception as e:
            print(f"Error removing key from config: {e}")
            return False
    
    def update_config_for_keys(self, keys: List[Dict]) -> bool:
        """Обновление конфигурации для всех ключей"""
        try:
            # Создаем резервную копию
            backup_file = self._backup_config()
            
            # Загружаем базовую конфигурацию
            config = self._load_config()
            if not config:
                return False
            
            # Очищаем существующие inbounds (кроме API)
            config["inbounds"] = [
                inbound for inbound in config["inbounds"]
                if inbound.get("tag") == "api"
            ]
            
            # Добавляем inbounds для каждого ключа
            for key in keys:
                if key.get("is_active", True):
                    inbound = self.create_inbound_for_key(key["uuid"], key["name"])
                    if inbound:
                        config["inbounds"].append(inbound)
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            self._save_config(config)
            
            print(f"Updated Xray config for {len(keys)} keys")
            return True
            
        except Exception as e:
            print(f"Error updating config for keys: {e}")
            return False
    
    def get_config_status(self) -> Dict:
        """Получение статуса конфигурации"""
        try:
            config = self._load_config()
            if not config:
                return {"error": "Failed to load config"}
            
            # Подсчитываем inbounds
            total_inbounds = len(config["inbounds"])
            vless_inbounds = len([
                inbound for inbound in config["inbounds"]
                if inbound.get("protocol") == "vless"
            ])
            api_inbounds = len([
                inbound for inbound in config["inbounds"]
                if inbound.get("tag") == "api"
            ])
            
            # Получаем информацию о портах
            port_assignments = port_manager.get_all_assignments()
            
            return {
                "total_inbounds": total_inbounds,
                "vless_inbounds": vless_inbounds,
                "api_inbounds": api_inbounds,
                "port_assignments": port_assignments,
                "config_valid": self._validate_config(config),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Failed to get config status: {e}"}
    
    def validate_config_sync(self, keys: List[Dict]) -> Dict:
        """Валидация синхронизации конфигурации с ключами"""
        try:
            config = self._load_config()
            if not config:
                return {"error": "Failed to load config"}
            
            # Получаем UUID из ключей
            key_uuids = {key["uuid"] for key in keys if key.get("is_active", True)}
            
            # Получаем UUID из конфигурации
            config_uuids = set()
            for inbound in config["inbounds"]:
                if inbound.get("protocol") == "vless":
                    clients = inbound.get("settings", {}).get("clients", [])
                    for client in clients:
                        config_uuids.add(client.get("id"))
            
            # Проверяем соответствие
            missing_in_config = key_uuids - config_uuids
            extra_in_config = config_uuids - key_uuids
            
            return {
                "synchronized": len(missing_in_config) == 0 and len(extra_in_config) == 0,
                "key_uuids": list(key_uuids),
                "config_uuids": list(config_uuids),
                "missing_in_config": list(missing_in_config),
                "extra_in_config": list(extra_in_config),
                "total_keys": len(key_uuids),
                "total_config_clients": len(config_uuids)
            }
            
        except Exception as e:
            return {"error": f"Failed to validate config sync: {e}"}

# Глобальный экземпляр менеджера конфигурации
xray_config_manager = XrayConfigManager()

# Функции для совместимости с API
def add_key_to_xray_config(uuid: str, key_name: str) -> bool:
    """Добавление ключа в конфигурацию Xray"""
    return xray_config_manager.add_key_to_config(uuid, key_name)

def remove_key_from_xray_config(uuid: str) -> bool:
    """Удаление ключа из конфигурации Xray"""
    return xray_config_manager.remove_key_from_config(uuid)

def update_xray_config_for_keys(keys: List[Dict]) -> bool:
    """Обновление конфигурации Xray для всех ключей"""
    return xray_config_manager.update_config_for_keys(keys)

def get_xray_config_status() -> Dict:
    """Получение статуса конфигурации Xray"""
    return xray_config_manager.get_config_status()

def validate_xray_config_sync(keys: List[Dict]) -> Dict:
    """Валидация синхронизации конфигурации Xray"""
    return xray_config_manager.validate_config_sync(keys) 