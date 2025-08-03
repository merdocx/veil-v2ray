#!/usr/bin/env python3
"""
Интегрированная система точного подсчета трафика
Объединяет nethogs для точного трафика и анализ логов для сопоставления с пользователями
"""

import subprocess
import json
import time
import re
from typing import Dict, List, Optional
from datetime import datetime

class PreciseTrafficMonitor:
    def __init__(self):
        self.xray_process = "xray"
        self.log_file = "/root/vpn-server/logs/access.log"
        self.cache_duration = 30  # секунды
        self._cache = {}
        self._cache_time = 0
    
    def _get_nethogs_data(self) -> Dict:
        """Получение данных от nethogs"""
        try:
            result = subprocess.run([
                "timeout", "3", "nethogs", "-t", "-v", "3"
            ], capture_output=True, text=True, check=True)
            
            print(f"DEBUG: nethogs output: {result.stdout}")
            
            xray_data = {
                "sent_bytes": 0,
                "received_bytes": 0,
                "total_bytes": 0,
                "sent_formatted": "0 B",
                "received_formatted": "0 B",
                "total_formatted": "0 B",
                "sent_mb": 0,
                "received_mb": 0,
                "total_mb": 0
            }
            
            for line in result.stdout.split('\n'):
                if '/usr/local/bin/xray' in line:
                    print(f"DEBUG: Found xray line: {line}")
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            sent = float(parts[-2])
                            received = float(parts[-1])
                            
                            print(f"DEBUG: Raw values - sent: {sent}, received: {received}")
                            
                            # nethogs показывает в KB, но может быть в научной нотации
                            # Если значения очень маленькие, считаем их в байтах
                            if sent < 0.001 and received < 0.001:
                                # Очень маленькие значения - возможно в байтах
                                sent_bytes = int(sent)
                                received_bytes = int(received)
                                print(f"DEBUG: Using as bytes - sent: {sent_bytes}, received: {received_bytes}")
                            else:
                                # Нормальные значения - конвертируем из KB
                                sent_bytes = int(sent * 1024)
                                received_bytes = int(received * 1024)
                                print(f"DEBUG: Using as KB - sent: {sent_bytes}, received: {received_bytes}")
                            
                            total_bytes = sent_bytes + received_bytes
                            
                            def format_bytes(bytes_value: int) -> str:
                                if bytes_value < 1024:
                                    return f"{bytes_value} B"
                                elif bytes_value < 1024 * 1024:
                                    return f"{bytes_value / 1024:.2f} KB"
                                elif bytes_value < 1024 * 1024 * 1024:
                                    return f"{bytes_value / (1024 * 1024):.2f} MB"
                                else:
                                    return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
                            
                            xray_data.update({
                                "sent_bytes": sent_bytes,
                                "received_bytes": received_bytes,
                                "total_bytes": total_bytes,
                                "sent_formatted": format_bytes(sent_bytes),
                                "received_formatted": format_bytes(received_bytes),
                                "total_formatted": format_bytes(total_bytes),
                                "sent_mb": round(sent_bytes / (1024 * 1024), 2),
                                "received_mb": round(received_bytes / (1024 * 1024), 2),
                                "total_mb": round(total_bytes / (1024 * 1024), 2)
                            })
                            print(f"DEBUG: Final xray_data: {xray_data}")
                            break
                        except (ValueError, IndexError) as e:
                            print(f"DEBUG: Error parsing line: {e}")
                            continue
            
            return xray_data
            
        except Exception as e:
            return {
                "sent_bytes": 0,
                "received_bytes": 0,
                "total_bytes": 0,
                "sent_formatted": "0 B",
                "received_formatted": "0 B",
                "total_formatted": "0 B",
                "sent_mb": 0,
                "received_mb": 0,
                "total_mb": 0,
                "error": str(e)
            }
    
    def _get_user_connections(self) -> Dict[str, int]:
        """Получение количества подключений для каждого пользователя из логов"""
        user_connections = {}
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    match = re.search(r'email: ([a-f0-9-]+)', line)
                    if match:
                        email = match.group(1)
                        user_connections[email] = user_connections.get(email, 0) + 1
        except FileNotFoundError:
            pass
        
        return user_connections
    
    def _get_connection_stats(self, connections: int) -> Dict:
        """Получение статистики подключений"""
        return {
            "connections": connections
        }
    
    def get_key_traffic(self, uuid: str) -> Dict:
        """Получение точной статистики трафика для ключа"""
        # Проверяем кэш
        current_time = time.time()
        if current_time - self._cache_time < self.cache_duration:
            if uuid in self._cache:
                return self._cache[uuid]
        
        # Получаем данные nethogs
        nethogs_data = self._get_nethogs_data()
        
        # Получаем данные о подключениях
        user_connections = self._get_user_connections()
        
        # Определяем долю трафика для пользователя
        total_connections = sum(user_connections.values())
        user_connections_count = user_connections.get(uuid, 0)
        
        if total_connections > 0 and user_connections_count > 0:
            # Распределяем трафик пропорционально количеству подключений
            user_ratio = user_connections_count / total_connections
            user_sent = int(nethogs_data["sent_bytes"] * user_ratio)
            user_received = int(nethogs_data["received_bytes"] * user_ratio)
            user_total = user_sent + user_received
        else:
            user_sent = 0
            user_received = 0
            user_total = 0
        
        def format_bytes(bytes_value: int) -> str:
            if bytes_value < 1024:
                return f"{bytes_value} B"
            elif bytes_value < 1024 * 1024:
                return f"{bytes_value / 1024:.2f} KB"
            elif bytes_value < 1024 * 1024 * 1024:
                return f"{bytes_value / (1024 * 1024):.2f} MB"
            else:
                return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
        
        # Данные о подключениях
        connection_data = self._get_connection_stats(user_connections_count)
        
        result = {
            "uuid": uuid,
            "connections": user_connections_count,
            "connection_ratio": round(user_connections_count / total_connections * 100, 2) if total_connections > 0 else 0,
            
            # Точный трафик (распределенный)
            "sent_bytes": user_sent,
            "received_bytes": user_received,
            "total_bytes": user_total,
            "sent_formatted": format_bytes(user_sent),
            "received_formatted": format_bytes(user_received),
            "total_formatted": format_bytes(user_total),
            "sent_mb": round(user_sent / (1024 * 1024), 2),
            "received_mb": round(user_received / (1024 * 1024), 2),
            "total_mb": round(user_total / (1024 * 1024), 2),
            
            # Статистика подключений
            "connections_count": connection_data["connections"],
            
            "timestamp": int(current_time),
            "source": "precise_monitor",
            "method": "nethogs_distribution"
        }
        
        # Кэшируем результат
        self._cache[uuid] = result
        self._cache_time = current_time
        
        return result
    
    def get_all_keys_traffic(self) -> Dict:
        """Получение статистики трафика для всех ключей"""
        # Получаем данные nethogs
        nethogs_data = self._get_nethogs_data()
        
        # Получаем данные о подключениях
        user_connections = self._get_user_connections()
        
        if not user_connections:
            return {
                "total_keys": 0,
                "active_keys": 0,
                "total_connections": 0,
                "total_bytes": 0,
                "total_formatted": "0 B",
                "total_mb": 0,
                "keys_stats": [],
                "source": "precise_monitor"
            }
        
        keys_stats = []
        total_connections = sum(user_connections.values())
        
        for uuid, connections in user_connections.items():
            key_traffic = self.get_key_traffic(uuid)
            keys_stats.append(key_traffic)
        
        return {
            "total_keys": len(user_connections),
            "active_keys": len([k for k in keys_stats if k["connections"] > 0]),
            "total_connections": total_connections,
            "total_bytes": nethogs_data["total_bytes"],
            "total_formatted": nethogs_data["total_formatted"],
            "total_mb": nethogs_data["total_mb"],
            "keys_stats": keys_stats,
            "source": "precise_monitor"
        }
    
    def reset_key_traffic(self, uuid: str) -> bool:
        """Сброс статистики для ключа (очистка кэша)"""
        if uuid in self._cache:
            del self._cache[uuid]
        return True

# Глобальный экземпляр
precise_monitor = PreciseTrafficMonitor()

def get_key_traffic_bytes(uuid: str) -> Dict:
    """Получение точной статистики трафика для ключа"""
    return precise_monitor.get_key_traffic(uuid)

def get_all_keys_traffic_bytes() -> Dict:
    """Получение точной статистики трафика для всех ключей"""
    return precise_monitor.get_all_keys_traffic()

def reset_key_traffic_stats(uuid: str) -> bool:
    """Сброс статистики трафика для ключа"""
    return precise_monitor.reset_key_traffic(uuid)

if __name__ == "__main__":
    print("=== ИНТЕГРИРОВАННАЯ СИСТЕМА ТОЧНОГО ПОДСЧЕТА ТРАФИКА ===")
    print()
    
    # Тестирование
    all_traffic = get_all_keys_traffic_bytes()
    print(f"Всего ключей: {all_traffic['total_keys']}")
    print(f"Активных ключей: {all_traffic['active_keys']}")
    print(f"Общий трафик: {all_traffic['total_formatted']}")
    print()
    
    for key in all_traffic['keys_stats']:
        print(f"Ключ {key['uuid']}:")
        print(f"  Подключений: {key['connections']}")
        print(f"  Точный трафик: {key['total_formatted']}")
        print() 