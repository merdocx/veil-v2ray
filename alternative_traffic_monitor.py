#!/usr/bin/env python3
"""
Альтернативный мониторинг трафика через /proc/net/dev
"""

import subprocess
import json
import time
import re
from typing import Dict, List, Optional
from datetime import datetime

class AlternativeTrafficMonitor:
    def __init__(self):
        self.log_file = "/root/vpn-server/logs/access.log"
        self.cache_duration = 30  # seconds
        self._cache = {}
        self._cache_time = 0
        self._last_traffic = None
        self._last_time = None
    
    def _get_network_traffic(self) -> Dict:
        """Получение общего сетевого трафика из /proc/net/dev"""
        try:
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            total_rx = 0
            total_tx = 0
            
            for line in lines[2:]:  # Пропускаем заголовки
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        interface = parts[0].strip()
                        if interface.startswith('ens') or interface.startswith('eth'):
                            stats = parts[1].split()
                            if len(stats) >= 10:
                                rx_bytes = int(stats[0])
                                tx_bytes = int(stats[8])
                                total_rx += rx_bytes
                                total_tx += tx_bytes
            
            return {
                "rx_bytes": total_rx,
                "tx_bytes": total_tx,
                "total_bytes": total_rx + total_tx,
                "timestamp": time.time()
            }
        except Exception as e:
            print(f"Error getting network traffic: {e}")
            return {
                "rx_bytes": 0,
                "tx_bytes": 0,
                "total_bytes": 0,
                "timestamp": time.time()
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
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Форматирование байтов в читаемый вид"""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.2f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
    
    def get_key_traffic(self, uuid: str) -> Dict:
        """Получение трафика для конкретного ключа"""
        current_time = time.time()
        
        # Проверяем кэш
        if uuid in self._cache and current_time - self._cache_time < self.cache_duration:
            return self._cache[uuid]
        
        # Получаем текущий трафик
        current_traffic = self._get_network_traffic()
        
        # Если это первый запуск, сохраняем базовые значения
        if self._last_traffic is None:
            self._last_traffic = current_traffic
            self._last_time = current_time
            result = {
                "total_bytes": 0,
                "total_formatted": "0 B",
                "total_mb": 0,
                "connections": 0,
                "connection_ratio": 0,
                "connections_count": 0,
                "source": "alternative_monitor",
                "method": "network_distribution",
                "timestamp": int(current_time)
            }
            self._cache[uuid] = result
            self._cache_time = current_time
            return result
        
        # Вычисляем разницу трафика
        time_diff = current_time - self._last_time
        if time_diff < 1:  # Минимум 1 секунда
            time_diff = 1
        
        traffic_diff = current_traffic["total_bytes"] - self._last_traffic["total_bytes"]
        
        # Получаем подключения пользователей
        user_connections = self._get_user_connections()
        total_connections = sum(user_connections.values())
        
        # Получаем подключения для конкретного пользователя
        user_connections_count = user_connections.get(uuid, 0)
        
        # Распределяем трафик пропорционально подключениям
        if total_connections > 0:
            user_traffic = int(traffic_diff * (user_connections_count / total_connections))
            connection_ratio = round((user_connections_count / total_connections) * 100, 2)
        else:
            user_traffic = 0
            connection_ratio = 0
        
        result = {
            "total_bytes": user_traffic,
            "total_formatted": self._format_bytes(user_traffic),
            "total_mb": round(user_traffic / (1024 * 1024), 2),
            "connections": user_connections_count,
            "connection_ratio": connection_ratio,
            "connections_count": user_connections_count,
            "source": "alternative_monitor",
            "method": "network_distribution",
            "timestamp": int(current_time)
        }
        
        # Обновляем кэш
        self._cache[uuid] = result
        self._cache_time = current_time
        
        # Обновляем последние значения
        self._last_traffic = current_traffic
        self._last_time = current_time
        
        return result
    
    def get_all_keys_traffic(self) -> Dict:
        """Получение трафика для всех ключей"""
        # Получаем все UUID из логов
        user_connections = self._get_user_connections()
        
        keys_stats = []
        total_traffic = 0
        
        for uuid in user_connections.keys():
            traffic_data = self.get_key_traffic(uuid)
            keys_stats.append({
                "uuid": uuid,
                "connections": traffic_data["connections"],
                "total_bytes": traffic_data["total_bytes"],
                "total_formatted": traffic_data["total_formatted"],
                "total_mb": traffic_data["total_mb"],
                "connection_ratio": traffic_data["connection_ratio"]
            })
            total_traffic += traffic_data["total_bytes"]
        
        return {
            "total_keys": len(user_connections),
            "active_keys": len(user_connections),
            "total_traffic": self._format_bytes(total_traffic),
            "traffic_stats": {
                "keys_stats": keys_stats
            },
            "source": "alternative_monitor",
            "timestamp": int(time.time())
        }
    
    def reset_key_traffic(self, uuid: str) -> bool:
        """Сброс трафика для ключа"""
        if uuid in self._cache:
            del self._cache[uuid]
        return True

# Создаем глобальный экземпляр
alternative_monitor = AlternativeTrafficMonitor()

def get_key_traffic_bytes(uuid: str) -> Dict:
    return alternative_monitor.get_key_traffic(uuid)

def get_all_keys_traffic_bytes() -> Dict:
    return alternative_monitor.get_all_keys_traffic()

def reset_key_traffic_stats(uuid: str) -> bool:
    return alternative_monitor.reset_key_traffic(uuid)

if __name__ == "__main__":
    print("=== АЛЬТЕРНАТИВНАЯ СИСТЕМА МОНИТОРИНГА ТРАФИКА ===")
    print()
    
    # Первый запуск для инициализации
    all_traffic = get_all_keys_traffic_bytes()
    
    print(f"Всего ключей: {all_traffic['total_keys']}")
    print(f"Активных ключей: {all_traffic['active_keys']}")
    print(f"Общий трафик: {all_traffic['total_traffic']}")
    print()
    
    for key in all_traffic['traffic_stats']['keys_stats']:
        print(f"Ключ {key['uuid']}:")
        print(f"  Подключений: {key['connections']}")
        print(f"  Точный трафик: {key['total_formatted']}")
        print()
    
    print("Ожидание 5 секунд для накопления трафика...")
    time.sleep(5)
    
    # Второй запуск для показа трафика
    all_traffic = get_all_keys_traffic_bytes()
    
    print(f"Общий трафик после 5 секунд: {all_traffic['total_traffic']}")
    print()
    
    for key in all_traffic['traffic_stats']['keys_stats']:
        print(f"Ключ {key['uuid']}:")
        print(f"  Подключений: {key['connections']}")
        print(f"  Точный трафик: {key['total_formatted']}")
        print() 