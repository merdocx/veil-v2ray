#!/usr/bin/env python3
"""
Исправленный модуль управления конфигурацией Xray с централизованными Reality ключами
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
        self.keys_env_file = "/root/vpn-server/config/keys.env"
        
        # Создаем директорию для бэкапов
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _load_reality_keys(self) -> Dict[str, str]:
        """Загрузка Reality ключей из keys.env"""
        keys = {}
        try:
            with open(self.keys_env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PRIVATE_KEY='):
                        # Извлекаем приватный ключ, убирая префикс "Private key: "
                        private_key = line.split('=', 1)[1].strip()
                        if private_key.startswith('Private key: '):
                            private_key = private_key.replace('Private key: ', '')
                        keys['private_key'] = private_key
                    elif line.startswith('PUBLIC_KEY='):
                        keys['public_key'] = line.split('=', 1)[1].strip()
                    elif line.startswith('SHORT_ID='):
                        keys['short_id'] = line.split('=', 1)[1].strip()
        except FileNotFoundError:
            print(f"Keys file {self.keys_env_file} not found")
        return keys
    
    def _load_config(self) -> Optional[Dict]:
        """Загрузка конфигурации Xray"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
    
    def _save_config(self, config: Dict) -> bool:
        """Сохранение конфигурации Xray"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
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
    
    def _validate_config(self, config: Dict) -> bool:
        """Валидация конфигурации Xray"""
        try:
            # Проверяем базовую структуру
            if "inbounds" not in config or "outbounds" not in config:
                return False
            
            # Проверяем, что есть хотя бы один inbound
            if not config["inbounds"]:
                return False
            
            return True
        except Exception as e:
            print(f"Config validation error: {e}")
            return False
    
    def create_inbound_for_key(self, uuid: str, key_name: str) -> Optional[Dict]:
        """Создание inbound для ключа с централизованными Reality ключами"""
        # Получаем порт для ключа
        port = port_manager.get_port_for_uuid(uuid)
        if not port:
            print(f"No port assigned for UUID: {uuid}")
            return None
        
        # Загружаем централизованные Reality ключи
        reality_keys = self._load_reality_keys()
        if not reality_keys.get('private_key') or not reality_keys.get('short_id'):
            print("Error: Centralized Reality keys not found")
            return None
        
        # Создаем inbound конфигурацию с централизованными ключами
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
                    "serverNames": [
                        "www.microsoft.com",
                        "www.cloudflare.com",
                        "www.google.com",
                        "www.github.com",
                        "www.apple.com",
                        "www.amazon.com"
                    ],
                    "privateKey": reality_keys['private_key'],
                    "shortIds": [
                        "2680beb40ea2fde0",
                        "2bc4128aa76f2b7a",
                        "c3fc1008549269da",
                        "c39576010e746754"
                    ],
                    "maxTimeDiff": 600
                }
            },
            "tag": f"inbound-{uuid}"
        }
        
        return inbound
    
    def add_key_to_config(self, uuid: str, key_name: str) -> bool:
        """Добавление ключа в конфигурацию Xray с проверкой Reality ключей"""
        try:
            # Создаем резервную копию
            backup_file = self._backup_config()
            
            # Загружаем конфигурацию
            config = self._load_config()
            if not config:
                return False
            
            # Создаем inbound для ключа
            inbound = self.create_inbound_for_key(uuid, key_name)
            if not inbound:
                print(f"Failed to create inbound for key {uuid}")
                return False
            
            # Проверяем, что используются правильные Reality ключи
            reality_keys = self._load_reality_keys()
            if inbound.get('streamSettings', {}).get('realitySettings', {}).get('privateKey') != reality_keys.get('private_key'):
                print("Warning: Reality private key mismatch, correcting...")
                inbound['streamSettings']['realitySettings']['privateKey'] = reality_keys.get('private_key')
            
            if inbound.get('streamSettings', {}).get('realitySettings', {}).get('shortIds', [None])[0] != reality_keys.get('short_id'):
                print("Warning: Reality short ID mismatch, correcting...")
                inbound['streamSettings']['realitySettings']['shortIds'] = [reality_keys.get('short_id')]
            
            # Добавляем inbound в конфигурацию
            config["inbounds"].append(inbound)
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            success = self._save_config(config)
            if success:
                print(f"Successfully added key {uuid} to Xray config with centralized Reality keys")
            return success
            
        except Exception as e:
            print(f"Error adding key to config: {e}")
            return False
    
    def remove_key_from_config(self, uuid: str) -> bool:
        """Удаление ключа из конфигурации Xray"""
        try:
            # Создаем резервную копию
            backup_file = self._backup_config()
            
            # Загружаем конфигурацию
            config = self._load_config()
            if not config:
                return False
            
            # Удаляем inbound для ключа
            config["inbounds"] = [
                inbound for inbound in config["inbounds"]
                if inbound.get("tag") != f"inbound-{uuid}"
            ]
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            return self._save_config(config)
            
        except Exception as e:
            print(f"Error removing key from config: {e}")
            return False
    
    def update_config_for_keys(self, keys: List[Dict]) -> bool:
        """Обновление конфигурации для всех ключей с централизованными ключами"""
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
            return self._save_config(config)
            
        except Exception as e:
            print(f"Error updating config for keys: {e}")
            return False
    
    def get_config_status(self) -> Dict:
        """Получение статуса конфигурации"""
        try:
            config = self._load_config()
            if not config:
                return {"status": "error", "message": "Config not found"}
            
            inbounds = config.get("inbounds", [])
            vless_inbounds = [inbound for inbound in inbounds if inbound.get("protocol") == "vless"]
            
            return {
                "status": "ok",
                "total_inbounds": len(inbounds),
                "vless_inbounds": len(vless_inbounds),
                "api_inbound": any(inbound.get("tag") == "api" for inbound in inbounds)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def fix_reality_keys_in_config(self) -> bool:
        """Исправление Reality ключей во всех inbound'ах конфигурации"""
        try:
            config = self._load_config()
            if not config:
                return False
            
            # Загружаем централизованные Reality ключи
            reality_keys = self._load_reality_keys()
            if not reality_keys.get('private_key') or not reality_keys.get('short_id'):
                print("Error: Centralized Reality keys not found")
                return False
            
            fixed_count = 0
            for inbound in config.get("inbounds", []):
                if (inbound.get("protocol") == "vless" and 
                    inbound.get("streamSettings", {}).get("security") == "reality"):
                    
                    reality_settings = inbound["streamSettings"]["realitySettings"]
                    
                    # Исправляем приватный ключ
                    if reality_settings.get("privateKey") != reality_keys['private_key']:
                        reality_settings["privateKey"] = reality_keys['private_key']
                        fixed_count += 1
                        print(f"Fixed private key for inbound {inbound.get('tag', 'unknown')}")
                    
                    # Исправляем Short ID
                    if reality_settings.get("shortIds", [None])[0] != reality_keys['short_id']:
                        reality_settings["shortIds"] = [reality_keys['short_id']]
                        fixed_count += 1
                        print(f"Fixed short ID for inbound {inbound.get('tag', 'unknown')}")
            
            if fixed_count > 0:
                print(f"Fixed Reality keys in {fixed_count} inbound(s)")
                return self._save_config(config)
            else:
                print("All Reality keys are already correct")
                return True
                
        except Exception as e:
            print(f"Error fixing Reality keys: {e}")
            return False
    
    def validate_config_sync(self, keys: List[Dict]) -> Dict:
        """Валидация синхронизации конфигурации"""
        try:
            config = self._load_config()
            if not config:
                return {"synced": False, "error": "Config not found"}
            
            # Получаем UUID из keys.json
            key_uuids = {key["uuid"] for key in keys}
            
            # Получаем UUID из config.json
            config_uuids = set()
            for inbound in config.get("inbounds", []):
                if inbound.get("protocol") == "vless":
                    for client in inbound.get("settings", {}).get("clients", []):
                        config_uuids.add(client.get("id"))
            
            # Проверяем соответствие
            synced = key_uuids == config_uuids
            
            return {
                "synced": synced,
                "keys_count": len(key_uuids),
                "config_count": len(config_uuids),
                "missing_in_config": list(key_uuids - config_uuids),
                "extra_in_config": list(config_uuids - key_uuids)
            }
            
        except Exception as e:
            return {"synced": False, "error": str(e)}

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

def fix_reality_keys_in_xray_config() -> bool:
    """Исправление Reality ключей в конфигурации Xray"""
    return xray_config_manager.fix_reality_keys_in_config()
