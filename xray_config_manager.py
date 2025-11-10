#!/usr/bin/env python3
"""
Исправленный модуль управления конфигурацией Xray с централизованными Reality ключами
"""

import json
import os
import subprocess
import secrets
import string
import shutil
import tempfile
from typing import Dict, List, Optional
from datetime import datetime

from port_manager import port_manager

class XrayConfigManager:
    def __init__(self, config_file: str = "/root/vpn-server/config/config.json"):
        self.config_file = config_file
        self.backup_dir = "/root/vpn-server/config/backups"
        self.keys_env_file = "/root/vpn-server/config/keys.env"
        self.xray_api_server = os.getenv("XRAY_API_SERVER", "127.0.0.1:10808")
        self.xray_binary = os.getenv("XRAY_BINARY_PATH", "/usr/local/bin/xray")
        
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
    
    def _restore_backup(self, backup_file: str):
        """Восстановление конфигурации из резервной копии"""
        if not backup_file or not os.path.exists(backup_file):
            return
        try:
            shutil.copy2(backup_file, self.config_file)
            print(f"Configuration restored from backup {backup_file}")
        except Exception as e:
            print(f"Error restoring backup {backup_file}: {e}")

    def _call_xray_api(self, command: str, extra_args: List[str]) -> bool:
        """Вызов команды xray api"""
        if not self.xray_api_server:
            return False
        if not os.path.exists(self.xray_binary):
            print(f"Xray binary not found at {self.xray_binary}")
            return False
        try:
            cmd = [
                self.xray_binary,
                "api",
                command,
                f"--server={self.xray_api_server}",
                "-t",
                "5",
            ]
            cmd.extend(extra_args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                print(f"Xray API command {command} failed: {stderr or stdout}")
                return False
            return True
        except FileNotFoundError:
            print("Xray binary not found for API calls")
        except subprocess.TimeoutExpired:
            print(f"Xray API command {command} timed out")
        except Exception as e:
            print(f"Error calling Xray API {command}: {e}")
        return False

    def _apply_inbound_via_api(self, inbound: Dict) -> bool:
        """Применение inbound через Xray API без перезапуска"""
        if not inbound:
            return False
        tag = inbound.get("tag")
        if tag:
            self._call_xray_api("rmi", [tag])
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
                json.dump({"inbounds": [inbound]}, tmp, ensure_ascii=False)
                tmp_path = tmp.name
            return self._call_xray_api("adi", [tmp_path])
        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _remove_inbound_via_api(self, tag: str) -> bool:
        """Удаление inbound через Xray API"""
        if not tag:
            return False
        return self._call_xray_api("rmi", [tag])
    
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
    
    def _update_routing_rules(self, config: Dict) -> None:
        """Обновление правил маршрутизации на основе всех активных inbounds"""
        try:
            # Инициализируем routing, если его нет
            if "routing" not in config:
                config["routing"] = {
                    "domainStrategy": "AsIs",
                    "rules": []
                }
            
            # Получаем все теги активных vless inbounds (кроме API)
            vless_inbound_tags = []
            for inbound in config.get("inbounds", []):
                if (inbound.get("protocol") == "vless" and 
                    inbound.get("tag") != "api" and
                    inbound.get("tag")):
                    vless_inbound_tags.append(inbound.get("tag"))
            
            # Находим или создаем правило для direct маршрутизации
            routing_rules = config["routing"].get("rules", [])
            direct_rule = None
            for rule in routing_rules:
                if rule.get("outboundTag") == "direct":
                    direct_rule = rule
                    break
            
            if direct_rule:
                # Обновляем существующее правило
                direct_rule["inboundTag"] = vless_inbound_tags
            else:
                # Создаем новое правило, если его нет
                if vless_inbound_tags:
                    routing_rules.append({
                        "type": "field",
                        "inboundTag": vless_inbound_tags,
                        "outboundTag": "direct"
                    })
            
            # Убеждаемся, что правило для API есть
            api_rule_exists = any(
                rule.get("outboundTag") == "api" 
                for rule in routing_rules
            )
            if not api_rule_exists:
                routing_rules.insert(0, {
                    "type": "field",
                    "inboundTag": ["api"],
                    "outboundTag": "api"
                })
            
            config["routing"]["rules"] = routing_rules
            
        except Exception as e:
            print(f"Error updating routing rules: {e}")
    
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
    
    def create_inbound_for_key(self, uuid: str, key_name: str, short_id: Optional[str] = None) -> Optional[Dict]:
        """Создание inbound для ключа с централизованными Reality ключами"""
        # Получаем порт для ключа
        port = port_manager.get_port_for_uuid(uuid)
        if not port:
            print(f"No port assigned for UUID: {uuid}")
            return None
        
        # Загружаем централизованные Reality ключи
        reality_keys = self._load_reality_keys()
        if not reality_keys.get('private_key'):
            print("Error: Centralized Reality keys not found")
            return None

        # Определяем набор shortIds
        if short_id:
            short_ids = [short_id]
        elif reality_keys.get('short_id'):
            short_ids = [reality_keys['short_id']]
        else:
            short_ids = [
                "2680beb40ea2fde0",
                "2bc4128aa76f2b7a",
                "c3fc1008549269da",
                "c39576010e746754"
            ]
        
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
                    "shortIds": short_ids,
                    "maxTimeDiff": 600
                }
            },
            "tag": f"inbound-{uuid}"
        }
        
        return inbound
    
    def add_key_to_config(self, uuid: str, key_name: str, short_id: Optional[str] = None) -> bool:
        """Добавление ключа в конфигурацию Xray с проверкой Reality ключей"""
        try:
            # Создаем резервную копию
            backup_file = self._backup_config()
            
            # Загружаем конфигурацию
            config = self._load_config()
            if not config:
                return False
            
            # Создаем inbound для ключа
            inbound = self.create_inbound_for_key(uuid, key_name, short_id)
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
            
            # Обновляем правила маршрутизации
            self._update_routing_rules(config)
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            success = self._save_config(config)
            if success:
                if self._apply_inbound_via_api(inbound):
                    print(f"Successfully added key {uuid} to Xray config with centralized Reality keys")
                    return True
                else:
                    print(f"Failed to apply inbound for key {uuid} via Xray API, restoring backup")
                    self._restore_backup(backup_file)
                    return False
            return False
            
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
            
            # Обновляем правила маршрутизации
            self._update_routing_rules(config)
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            if self._save_config(config):
                if self._remove_inbound_via_api(f"inbound-{uuid}"):
                    return True
                else:
                    print(f"Failed to remove inbound {uuid} via Xray API, restoring backup")
                    self._restore_backup(backup_file)
                    return False
            return False
            
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

            existing_inbounds = [
                inbound for inbound in config.get("inbounds", [])
                if inbound.get("tag") and inbound.get("tag") != "api"
            ]
            
            # Очищаем существующие inbounds (кроме API)
            config["inbounds"] = [
                inbound for inbound in config["inbounds"]
                if inbound.get("tag") == "api"
            ]

            new_inbounds: List[Dict] = []
            
            # Добавляем inbounds для каждого ключа
            for key in keys:
                if key.get("is_active", True):
                    inbound = self.create_inbound_for_key(
                        key["uuid"],
                        key["name"],
                        key.get("short_id")
                    )
                    if inbound:
                        new_inbounds.append(inbound)
                        config["inbounds"].append(inbound)
            
            # Обновляем правила маршрутизации
            self._update_routing_rules(config)
            
            # Валидируем конфигурацию
            if not self._validate_config(config):
                print("Configuration validation failed")
                return False
            
            # Сохраняем конфигурацию
            if not self._save_config(config):
                return False

            # Обновляем inbounds через API (если доступен HandlerService)
            new_tags = {inbound.get("tag") for inbound in new_inbounds if inbound.get("tag")}
            for inbound in new_inbounds:
                if not self._apply_inbound_via_api(inbound):
                    print(f"Failed to apply inbound {inbound.get('tag')} via API, restoring backup")
                    self._restore_backup(backup_file)
                    return False

            # Удаляем устаревшие inbounds
            for inbound in existing_inbounds:
                tag = inbound.get("tag")
                if tag and tag not in new_tags:
                    self._remove_inbound_via_api(tag)

            return True
            
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
                    
                    # Исправляем Short ID только при отсутствии или использовании центрального значения
                    short_ids = reality_settings.get("shortIds", [])
                    if not short_ids:
                        reality_settings["shortIds"] = [reality_keys['short_id']]
                        fixed_count += 1
                        print(f"Filled missing short ID for inbound {inbound.get('tag', 'unknown')}")
                    elif reality_keys['short_id'] in short_ids and short_ids != [reality_keys['short_id']]:
                        reality_settings["shortIds"] = [reality_keys['short_id']]
                        fixed_count += 1
                        print(f"Normalized central short ID for inbound {inbound.get('tag', 'unknown')}")
            
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
def add_key_to_xray_config(uuid: str, key_name: str, short_id: Optional[str] = None) -> bool:
    """Добавление ключа в конфигурацию Xray"""
    return xray_config_manager.add_key_to_config(uuid, key_name, short_id)

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
