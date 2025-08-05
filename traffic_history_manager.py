#!/usr/bin/env python3
"""
Модуль для управления историческими данными о трафике VPN ключей
Отслеживает общий объем трафика с момента создания каждого ключа
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficHistoryManager:
    """Менеджер для управления историческими данными о трафике"""
    
    def __init__(self, history_file: str = "config/traffic_history.json"):
        self.history_file = history_file
        self.ensure_history_file()
    
    def ensure_history_file(self):
        """Создает файл истории если он не существует"""
        if not os.path.exists(self.history_file):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            initial_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "keys_history": {},
                "daily_stats": {},
                "last_update": datetime.now().isoformat()
            }
            self._save_history(initial_data)
            logger.info(f"Создан новый файл истории трафика: {self.history_file}")
    
    def _load_history(self) -> Dict[str, Any]:
        """Загружает данные истории из файла"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Ошибка загрузки истории трафика: {e}")
            return {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "keys_history": {},
                "daily_stats": {},
                "last_update": datetime.now().isoformat()
            }
    
    def _save_history(self, data: Dict[str, Any]):
        """Сохраняет данные истории в файл"""
        try:
            data["last_update"] = datetime.now().isoformat()
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории трафика: {e}")
    
    def update_key_traffic(self, key_uuid: str, key_name: str, port: int, 
                          current_traffic: Dict[str, Any]):
        """Обновляет данные трафика для конкретного ключа"""
        history = self._load_history()
        
        # Получаем или создаем запись для ключа
        if key_uuid not in history["keys_history"]:
            history["keys_history"][key_uuid] = {
                "key_name": key_name,
                "port": port,
                "created_at": datetime.now().isoformat(),
                "total_traffic": {
                    "total_bytes": 0,
                    "rx_bytes": 0,
                    "tx_bytes": 0,
                    "total_connections": 0
                },
                "daily_traffic": {},
                "last_activity": None,
                "is_active": False
            }
        
        key_history = history["keys_history"][key_uuid]
        
        # Обновляем общую статистику
        current_bytes = current_traffic.get("total_bytes", 0)
        current_rx = current_traffic.get("rx_bytes", 0)
        current_tx = current_traffic.get("tx_bytes", 0)
        current_connections = current_traffic.get("connections", 0)
        
        # Добавляем только новый трафик (разницу)
        if "last_traffic" in key_history:
            last_traffic = key_history["last_traffic"]
            traffic_delta = max(0, current_bytes - last_traffic.get("total_bytes", 0))
            rx_delta = max(0, current_rx - last_traffic.get("rx_bytes", 0))
            tx_delta = max(0, current_tx - last_traffic.get("tx_bytes", 0))
            
            key_history["total_traffic"]["total_bytes"] += traffic_delta
            key_history["total_traffic"]["rx_bytes"] += rx_delta
            key_history["total_traffic"]["tx_bytes"] += tx_delta
        else:
            # Первое обновление - добавляем весь текущий трафик
            key_history["total_traffic"]["total_bytes"] += current_bytes
            key_history["total_traffic"]["rx_bytes"] += current_rx
            key_history["total_traffic"]["tx_bytes"] += current_tx
        
        # Обновляем максимальное количество соединений
        key_history["total_traffic"]["total_connections"] = max(
            key_history["total_traffic"]["total_connections"],
            current_connections
        )
        
        # Обновляем ежедневную статистику
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in key_history["daily_traffic"]:
            key_history["daily_traffic"][today] = {
                "total_bytes": 0,
                "rx_bytes": 0,
                "tx_bytes": 0,
                "max_connections": 0,
                "sessions": 0
            }
        
        daily_stats = key_history["daily_traffic"][today]
        if "last_traffic" in key_history:
            last_traffic = key_history["last_traffic"]
            traffic_delta = max(0, current_bytes - last_traffic.get("total_bytes", 0))
            rx_delta = max(0, current_rx - last_traffic.get("rx_bytes", 0))
            tx_delta = max(0, current_tx - last_traffic.get("tx_bytes", 0))
            
            daily_stats["total_bytes"] += traffic_delta
            daily_stats["rx_bytes"] += rx_delta
            daily_stats["tx_bytes"] += tx_delta
        else:
            daily_stats["total_bytes"] += current_bytes
            daily_stats["rx_bytes"] += current_rx
            daily_stats["tx_bytes"] += current_tx
        
        daily_stats["max_connections"] = max(daily_stats["max_connections"], current_connections)
        
        # Увеличиваем счетчик сессий если есть активные соединения
        if current_connections > 0:
            daily_stats["sessions"] += 1
        
        # Сохраняем текущие данные как последние
        key_history["last_traffic"] = {
            "total_bytes": current_bytes,
            "rx_bytes": current_rx,
            "tx_bytes": current_tx,
            "connections": current_connections,
            "timestamp": datetime.now().isoformat()
        }
        
        key_history["last_activity"] = datetime.now().isoformat()
        key_history["is_active"] = current_connections > 0
        
        # Обновляем общую ежедневную статистику
        self._update_daily_stats(history, today, current_bytes, current_connections)
        
        self._save_history(history)
        logger.info(f"Обновлена история трафика для ключа {key_name} (UUID: {key_uuid})")
    
    def _update_daily_stats(self, history: Dict[str, Any], date: str, 
                           traffic_bytes: int, connections: int):
        """Обновляет общую ежедневную статистику"""
        if date not in history["daily_stats"]:
            history["daily_stats"][date] = {
                "total_bytes": 0,
                "total_connections": 0,
                "active_keys": 0,
                "total_sessions": 0
            }
        
        daily_stats = history["daily_stats"][date]
        daily_stats["total_bytes"] += traffic_bytes
        daily_stats["total_connections"] = max(daily_stats["total_connections"], connections)
        daily_stats["total_sessions"] += 1 if connections > 0 else 0
    
    def get_key_total_traffic(self, key_uuid: str) -> Optional[Dict[str, Any]]:
        """Получает общий объем трафика для ключа с момента создания"""
        history = self._load_history()
        
        if key_uuid not in history["keys_history"]:
            return None
        
        key_history = history["keys_history"][key_uuid]
        total_traffic = key_history["total_traffic"]
        
        return {
            "key_uuid": key_uuid,
            "key_name": key_history["key_name"],
            "port": key_history["port"],
            "created_at": key_history["created_at"],
            "last_activity": key_history["last_activity"],
            "is_active": key_history["is_active"],
            "total_traffic": {
                "total_bytes": total_traffic["total_bytes"],
                "rx_bytes": total_traffic["rx_bytes"],
                "tx_bytes": total_traffic["tx_bytes"],
                "total_connections": total_traffic["total_connections"],
                "total_formatted": self._format_bytes(total_traffic["total_bytes"]),
                "rx_formatted": self._format_bytes(total_traffic["rx_bytes"]),
                "tx_formatted": self._format_bytes(total_traffic["tx_bytes"])
            },
            "daily_stats": key_history["daily_traffic"]
        }
    
    def get_all_keys_total_traffic(self) -> Dict[str, Any]:
        """Получает общий объем трафика для всех ключей"""
        history = self._load_history()
        
        result = {
            "total_keys": len(history["keys_history"]),
            "active_keys": 0,
            "total_traffic_bytes": 0,
            "total_rx_bytes": 0,
            "total_tx_bytes": 0,
            "keys": []
        }
        
        for key_uuid, key_history in history["keys_history"].items():
            total_traffic = key_history["total_traffic"]
            
            if key_history["is_active"]:
                result["active_keys"] += 1
            
            result["total_traffic_bytes"] += total_traffic["total_bytes"]
            result["total_rx_bytes"] += total_traffic["rx_bytes"]
            result["total_tx_bytes"] += total_traffic["tx_bytes"]
            
            key_data = {
                "key_uuid": key_uuid,
                "key_name": key_history["key_name"],
                "port": key_history["port"],
                "created_at": key_history["created_at"],
                "last_activity": key_history["last_activity"],
                "is_active": key_history["is_active"],
                "total_traffic": {
                    "total_bytes": total_traffic["total_bytes"],
                    "rx_bytes": total_traffic["rx_bytes"],
                    "tx_bytes": total_traffic["tx_bytes"],
                    "total_connections": total_traffic["total_connections"],
                    "total_formatted": self._format_bytes(total_traffic["total_bytes"]),
                    "rx_formatted": self._format_bytes(total_traffic["rx_bytes"]),
                    "tx_formatted": self._format_bytes(total_traffic["tx_bytes"])
                }
            }
            
            result["keys"].append(key_data)
        
        result["total_traffic_formatted"] = self._format_bytes(result["total_traffic_bytes"])
        result["total_rx_formatted"] = self._format_bytes(result["total_rx_bytes"])
        result["total_tx_formatted"] = self._format_bytes(result["total_tx_bytes"])
        
        return result
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Получает ежедневную статистику"""
        history = self._load_history()
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date not in history["daily_stats"]:
            return {
                "date": date,
                "total_bytes": 0,
                "total_connections": 0,
                "active_keys": 0,
                "total_sessions": 0,
                "total_formatted": "0 B"
            }
        
        daily_stats = history["daily_stats"][date]
        return {
            "date": date,
            "total_bytes": daily_stats["total_bytes"],
            "total_connections": daily_stats["total_connections"],
            "active_keys": daily_stats["active_keys"],
            "total_sessions": daily_stats["total_sessions"],
            "total_formatted": self._format_bytes(daily_stats["total_bytes"])
        }

    def get_monthly_stats(self, year_month: Optional[str] = None) -> Dict[str, Any]:
        """Получает месячную статистику трафика для всех ключей"""
        history = self._load_history()
        
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        
        result = {
            "year_month": year_month,
            "total_keys": len(history["keys_history"]),
            "active_keys": 0,
            "total_traffic_bytes": 0,
            "total_rx_bytes": 0,
            "total_tx_bytes": 0,
            "total_connections": 0,
            "total_sessions": 0,
            "keys": []
        }
        
        for key_uuid, key_history in history["keys_history"].items():
            monthly_traffic = {
                "total_bytes": 0,
                "rx_bytes": 0,
                "tx_bytes": 0,
                "max_connections": 0,
                "sessions": 0
            }
            
            # Суммируем данные за месяц
            for date, daily_data in key_history["daily_traffic"].items():
                if date.startswith(year_month):
                    monthly_traffic["total_bytes"] += daily_data["total_bytes"]
                    monthly_traffic["rx_bytes"] += daily_data["rx_bytes"]
                    monthly_traffic["tx_bytes"] += daily_data["tx_bytes"]
                    monthly_traffic["max_connections"] = max(
                        monthly_traffic["max_connections"],
                        daily_data["max_connections"]
                    )
                    monthly_traffic["sessions"] += daily_data["sessions"]
            
            if key_history["is_active"]:
                result["active_keys"] += 1
            
            result["total_traffic_bytes"] += monthly_traffic["total_bytes"]
            result["total_rx_bytes"] += monthly_traffic["rx_bytes"]
            result["total_tx_bytes"] += monthly_traffic["tx_bytes"]
            result["total_connections"] = max(result["total_connections"], monthly_traffic["max_connections"])
            result["total_sessions"] += monthly_traffic["sessions"]
            
            key_data = {
                "key_uuid": key_uuid,
                "key_name": key_history["key_name"],
                "port": key_history["port"],
                "created_at": key_history["created_at"],
                "last_activity": key_history["last_activity"],
                "is_active": key_history["is_active"],
                "monthly_traffic": {
                    "total_bytes": monthly_traffic["total_bytes"],
                    "rx_bytes": monthly_traffic["rx_bytes"],
                    "tx_bytes": monthly_traffic["tx_bytes"],
                    "max_connections": monthly_traffic["max_connections"],
                    "sessions": monthly_traffic["sessions"],
                    "total_formatted": self._format_bytes(monthly_traffic["total_bytes"]),
                    "rx_formatted": self._format_bytes(monthly_traffic["rx_bytes"]),
                    "tx_formatted": self._format_bytes(monthly_traffic["tx_bytes"])
                }
            }
            
            result["keys"].append(key_data)
        
        result["total_traffic_formatted"] = self._format_bytes(result["total_traffic_bytes"])
        result["total_rx_formatted"] = self._format_bytes(result["total_rx_bytes"])
        result["total_tx_formatted"] = self._format_bytes(result["total_tx_bytes"])
        
        return result

    def get_key_monthly_traffic(self, key_uuid: str, year_month: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Получает месячную статистику трафика для конкретного ключа"""
        history = self._load_history()
        
        if key_uuid not in history["keys_history"]:
            return None
        
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        
        key_history = history["keys_history"][key_uuid]
        monthly_traffic = {
            "total_bytes": 0,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "max_connections": 0,
            "sessions": 0,
            "daily_breakdown": {}
        }
        
        # Суммируем данные за месяц
        for date, daily_data in key_history["daily_traffic"].items():
            if date.startswith(year_month):
                monthly_traffic["total_bytes"] += daily_data["total_bytes"]
                monthly_traffic["rx_bytes"] += daily_data["rx_bytes"]
                monthly_traffic["tx_bytes"] += daily_data["tx_bytes"]
                monthly_traffic["max_connections"] = max(
                    monthly_traffic["max_connections"],
                    daily_data["max_connections"]
                )
                monthly_traffic["sessions"] += daily_data["sessions"]
                monthly_traffic["daily_breakdown"][date] = daily_data
        
        return {
            "key_uuid": key_uuid,
            "key_name": key_history["key_name"],
            "port": key_history["port"],
            "created_at": key_history["created_at"],
            "last_activity": key_history["last_activity"],
            "is_active": key_history["is_active"],
            "year_month": year_month,
            "monthly_traffic": {
                "total_bytes": monthly_traffic["total_bytes"],
                "rx_bytes": monthly_traffic["rx_bytes"],
                "tx_bytes": monthly_traffic["tx_bytes"],
                "max_connections": monthly_traffic["max_connections"],
                "sessions": monthly_traffic["sessions"],
                "total_formatted": self._format_bytes(monthly_traffic["total_bytes"]),
                "rx_formatted": self._format_bytes(monthly_traffic["rx_bytes"]),
                "tx_formatted": self._format_bytes(monthly_traffic["tx_bytes"])
            },
            "daily_breakdown": monthly_traffic["daily_breakdown"]
        }
    
    def reset_key_traffic(self, key_uuid: str) -> bool:
        """Сбрасывает статистику трафика для ключа"""
        history = self._load_history()
        
        if key_uuid not in history["keys_history"]:
            return False
        
        key_history = history["keys_history"][key_uuid]
        key_history["total_traffic"] = {
            "total_bytes": 0,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "total_connections": 0
        }
        key_history["daily_traffic"] = {}
        key_history["last_traffic"] = None
        key_history["last_activity"] = None
        key_history["is_active"] = False
        
        self._save_history(history)
        logger.info(f"Сброшена статистика трафика для ключа {key_uuid}")
        return True
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Очищает старые данные истории"""
        history = self._load_history()
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Очищаем ежедневную статистику
        dates_to_remove = []
        for date_str in history["daily_stats"].keys():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if date_obj < cutoff_date:
                    dates_to_remove.append(date_str)
            except ValueError:
                continue
        
        for date_str in dates_to_remove:
            del history["daily_stats"][date_str]
        
        # Очищаем ежедневную статистику ключей
        for key_uuid, key_history in history["keys_history"].items():
            dates_to_remove = []
            for date_str in key_history["daily_traffic"].keys():
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if date_obj < cutoff_date:
                        dates_to_remove.append(date_str)
                except ValueError:
                    continue
            
            for date_str in dates_to_remove:
                del key_history["daily_traffic"][date_str]
        
        self._save_history(history)
        logger.info(f"Очищены данные истории старше {days_to_keep} дней")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Форматирует байты в читаемый вид"""
        if bytes_value == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{bytes_value} B"
        else:
            return f"{bytes_value:.2f} {units[unit_index]}"


# Глобальный экземпляр менеджера
traffic_history = TrafficHistoryManager() 