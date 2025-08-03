#!/usr/bin/env python3
"""
Клиент для работы с Xray API
Использует TCP соединения для отправки команд в Xray API
"""

import socket
import json
import time
import logging
from typing import Dict, Optional, List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class XrayAPIClient:
    """Клиент для работы с Xray API"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 10085, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def _send_command(self, command: str) -> Optional[str]:
        """Отправка команды в Xray API"""
        try:
            # Создаем TCP соединение
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # Подключаемся к Xray API
            sock.connect((self.host, self.port))
            
            # Отправляем команду
            cmd = f"{command}\n".encode('utf-8')
            sock.send(cmd)
            
            # Получаем ответ
            response = b""
            while True:
                try:
                    data = sock.recv(1024)
                    if not data:
                        break
                    response += data
                except socket.timeout:
                    break
            
            sock.close()
            
            # Декодируем ответ
            result = response.decode('utf-8', errors='ignore').strip()
            logger.info(f"Command: {command}, Response: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return None
    
    def get_user_stats(self, email: str) -> Optional[Dict]:
        """Получение статистики пользователя"""
        response = self._send_command(f"stats user {email}")
        if not response:
            return None
        
        try:
            # Парсим ответ в формате: uplink:12345 downlink:67890
            stats = {}
            for line in response.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    try:
                        stats[key] = int(value)
                    except ValueError:
                        stats[key] = value
            
            return stats
            
        except Exception as e:
            logger.error(f"Error parsing user stats: {e}")
            return None
    
    def get_all_users_stats(self) -> Optional[Dict]:
        """Получение статистики всех пользователей"""
        response = self._send_command("stats users")
        if not response:
            return None
        
        try:
            # Парсим ответ
            users = {}
            for line in response.split('\n'):
                line = line.strip()
                if ':' in line:
                    email, stats_str = line.split(':', 1)
                    email = email.strip()
                    stats_str = stats_str.strip()
                    
                    # Парсим статистику пользователя
                    user_stats = {}
                    for stat in stats_str.split():
                        if '=' in stat:
                            key, value = stat.split('=', 1)
                            try:
                                user_stats[key] = int(value)
                            except ValueError:
                                user_stats[key] = value
                    
                    users[email] = user_stats
            
            return users
            
        except Exception as e:
            logger.error(f"Error parsing all users stats: {e}")
            return None
    
    def reset_user_stats(self, email: str) -> bool:
        """Сброс статистики пользователя"""
        response = self._send_command(f"stats user {email} reset")
        return response is not None
    
    def get_system_stats(self) -> Optional[Dict]:
        """Получение системной статистики"""
        response = self._send_command("stats sys")
        if not response:
            return None
        
        try:
            stats = {}
            for line in response.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    try:
                        stats[key] = int(value)
                    except ValueError:
                        stats[key] = value
            
            return stats
            
        except Exception as e:
            logger.error(f"Error parsing system stats: {e}")
            return None
    
    def is_api_available(self) -> bool:
        """Проверка доступности API"""
        try:
            response = self._send_command("stats users")
            return response is not None
        except:
            return False

# Глобальный экземпляр клиента
xray_client = XrayAPIClient()

def get_key_traffic_bytes(uuid: str) -> Dict:
    """Получение точной статистики трафика в байтах для ключа"""
    try:
        stats = xray_client.get_user_stats(uuid)
        
        if not stats:
            return {
                "uuid": uuid,
                "uplink_bytes": 0,
                "downlink_bytes": 0,
                "total_bytes": 0,
                "uplink_formatted": "0 B",
                "downlink_formatted": "0 B",
                "total_formatted": "0 B",
                "uplink_mb": 0,
                "downlink_mb": 0,
                "total_mb": 0,
                "timestamp": int(time.time()),
                "error": "API недоступен или пользователь не найден"
            }
        
        uplink = stats.get("uplink", 0)
        downlink = stats.get("downlink", 0)
        total = uplink + downlink
        
        def format_bytes(bytes_value: int) -> str:
            if bytes_value < 1024:
                return f"{bytes_value} B"
            elif bytes_value < 1024 * 1024:
                return f"{bytes_value / 1024:.2f} KB"
            elif bytes_value < 1024 * 1024 * 1024:
                return f"{bytes_value / (1024 * 1024):.2f} MB"
            else:
                return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
        
        return {
            "uuid": uuid,
            "uplink_bytes": uplink,
            "downlink_bytes": downlink,
            "total_bytes": total,
            "uplink_formatted": format_bytes(uplink),
            "downlink_formatted": format_bytes(downlink),
            "total_formatted": format_bytes(total),
            "uplink_mb": round(uplink / (1024 * 1024), 2),
            "downlink_mb": round(downlink / (1024 * 1024), 2),
            "total_mb": round(total / (1024 * 1024), 2),
            "timestamp": int(time.time()),
            "source": "xray_api"
        }
        
    except Exception as e:
        logger.error(f"Error getting traffic bytes for {uuid}: {e}")
        return {
            "uuid": uuid,
            "uplink_bytes": 0,
            "downlink_bytes": 0,
            "total_bytes": 0,
            "uplink_formatted": "0 B",
            "downlink_formatted": "0 B",
            "total_formatted": "0 B",
            "uplink_mb": 0,
            "downlink_mb": 0,
            "total_mb": 0,
            "timestamp": int(time.time()),
            "error": str(e)
        }

def get_all_keys_traffic_bytes() -> Dict:
    """Получение точной статистики трафика в байтах для всех ключей"""
    try:
        all_stats = xray_client.get_all_users_stats()
        
        if not all_stats:
            return {"error": "API недоступен или нет данных"}
        
        result = {
            "total_uplink_bytes": 0,
            "total_downlink_bytes": 0,
            "total_bytes": 0,
            "keys_stats": []
        }
        
        def format_bytes(bytes_value: int) -> str:
            if bytes_value < 1024:
                return f"{bytes_value} B"
            elif bytes_value < 1024 * 1024:
                return f"{bytes_value / 1024:.2f} KB"
            elif bytes_value < 1024 * 1024 * 1024:
                return f"{bytes_value / (1024 * 1024):.2f} MB"
            else:
                return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
        
        for user_email, stats in all_stats.items():
            uplink = stats.get("uplink", 0)
            downlink = stats.get("downlink", 0)
            total = uplink + downlink
            
            key_stats = {
                "uuid": user_email,
                "uplink_bytes": uplink,
                "downlink_bytes": downlink,
                "total_bytes": total,
                "uplink_formatted": format_bytes(uplink),
                "downlink_formatted": format_bytes(downlink),
                "total_formatted": format_bytes(total),
                "uplink_mb": round(uplink / (1024 * 1024), 2),
                "downlink_mb": round(downlink / (1024 * 1024), 2),
                "total_mb": round(total / (1024 * 1024), 2)
            }
            
            result["keys_stats"].append(key_stats)
            result["total_uplink_bytes"] += uplink
            result["total_downlink_bytes"] += downlink
            result["total_bytes"] += total
        
        # Добавляем форматированные значения для общих сумм
        result["total_uplink_formatted"] = format_bytes(result["total_uplink_bytes"])
        result["total_downlink_formatted"] = format_bytes(result["total_downlink_bytes"])
        result["total_formatted"] = format_bytes(result["total_bytes"])
        result["total_uplink_mb"] = round(result["total_uplink_bytes"] / (1024 * 1024), 2)
        result["total_downlink_mb"] = round(result["total_downlink_bytes"] / (1024 * 1024), 2)
        result["total_mb"] = round(result["total_bytes"] / (1024 * 1024), 2)
        result["source"] = "xray_api"
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting all keys traffic bytes: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Тест клиента
    print("Testing Xray API Client...")
    
    if xray_client.is_api_available():
        print("✅ API доступен")
        
        # Тест получения статистики всех пользователей
        all_stats = xray_client.get_all_users_stats()
        print(f"All users stats: {json.dumps(all_stats, indent=2)}")
        
        # Тест получения статистики конкретного пользователя
        if all_stats:
            for email in all_stats.keys():
                user_stats = xray_client.get_user_stats(email)
                print(f"User {email} stats: {json.dumps(user_stats, indent=2)}")
                break
        
        # Тест получения системной статистики
        sys_stats = xray_client.get_system_stats()
        print(f"System stats: {json.dumps(sys_stats, indent=2)}")
        
    else:
        print("❌ API недоступен") 