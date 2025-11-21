#!/usr/bin/env python3
"""
Простая и надежная система мониторинга трафика на основе активных соединений
"""

import subprocess
import json
import time
import re
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.sqlite_storage import storage

class SimpleTrafficMonitor:
    def __init__(self):
        self.cache_duration = 30  # seconds
        self._cache = {}
        self._cache_time = 0
        self._last_interface_traffic = None
        self._last_time = None
    
    def _get_interface_traffic(self) -> Dict:
        """Получение общего трафика интерфейса"""
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
                        if interface.startswith(('ens', 'eth', 'eno')):
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
            print(f"Error getting interface traffic: {e}")
            return {
                "rx_bytes": 0,
                "tx_bytes": 0,
                "total_bytes": 0,
                "timestamp": time.time()
            }
    
    def _get_port_connections(self, port: int) -> List[Dict]:
        """Получение активных соединений для порта"""
        try:
            # Получаем все TCP соединения (не только ESTABLISHED)
            result = subprocess.run([
                'ss', '-tnp'
            ], capture_output=True, text=True, timeout=10)
            
            connections = []
            for line in result.stdout.split('\n'):
                if f':{port}' in line and ('ESTAB' in line or 'LAST-ACK' in line or 'CLOSE-WAIT' in line):
                    # Парсим строку соединения
                    parts = line.split()
                    if len(parts) >= 4:
                        state = parts[0]
                        local_addr = parts[3]
                        remote_addr = parts[4] if len(parts) > 4 else "unknown"
                        
                        connections.append({
                            "local": local_addr,
                            "remote": remote_addr,
                            "state": state
                        })
            
            return connections
        except Exception as e:
            print(f"Error getting port connections: {e}")
            return []
    
    def _get_all_port_connections(self) -> Dict[int, List[Dict]]:
        """Получение активных соединений для всех портов"""
        try:
            result = subprocess.run([
                'ss', '-tnp'
            ], capture_output=True, text=True, timeout=10)
            
            port_connections = {}
            
            for line in result.stdout.split('\n'):
                if 'ESTAB' in line or 'LAST-ACK' in line or 'CLOSE-WAIT' in line:
                    # Ищем порты в диапазоне 10001-10100
                    for port in range(10001, 10101):
                        if f':{port}' in line:
                            if port not in port_connections:
                                port_connections[port] = []
                            
                            parts = line.split()
                            if len(parts) >= 4:
                                state = parts[0]
                                local_addr = parts[3]
                                remote_addr = parts[4] if len(parts) > 4 else "unknown"
                                
                                port_connections[port].append({
                                    "local": local_addr,
                                    "remote": remote_addr,
                                    "state": state
                                })
            
            return port_connections
        except Exception as e:
            print(f"Error getting all port connections: {e}")
            return {}
    
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
    
    def _estimate_traffic_from_connections(self, port: int, connections: List[Dict], 
                                         current_traffic: Dict, last_traffic: Dict = None) -> Dict:
        """Оценка трафика на основе активных соединений"""
        try:
            # Получаем общий трафик интерфейса
            total_interface_traffic = current_traffic["total_bytes"]
            
            # Если есть предыдущие данные, вычисляем дельту
            if last_traffic:
                traffic_delta = total_interface_traffic - last_traffic["total_bytes"]
                time_delta = current_traffic["timestamp"] - last_traffic["timestamp"]
                
                if time_delta > 0:
                    # Вычисляем скорость трафика (байт/сек)
                    traffic_rate = traffic_delta / time_delta
                    
                    # Если есть активные соединения, распределяем трафик
                    if connections:
                        # Оцениваем трафик на соединение (примерно 1KB/сек на соединение)
                        estimated_traffic_per_connection = 1024  # 1KB/сек
                        estimated_total = len(connections) * estimated_traffic_per_connection * time_delta
                        
                        # Используем минимум из реального трафика и оценки
                        actual_traffic = min(traffic_delta, estimated_total)
                        
                        return {
                            "rx_bytes": actual_traffic // 2,
                            "tx_bytes": actual_traffic // 2,
                            "total_bytes": actual_traffic,
                            "traffic_rate": traffic_rate,
                            "connections_count": len(connections)
                        }
            
            # Если нет предыдущих данных или соединений, возвращаем 0
            return {
                "rx_bytes": 0,
                "tx_bytes": 0,
                "total_bytes": 0,
                "traffic_rate": 0,
                "connections_count": len(connections)
            }
            
        except Exception as e:
            print(f"Error estimating traffic: {e}")
            return {
                "rx_bytes": 0,
                "tx_bytes": 0,
                "total_bytes": 0,
                "traffic_rate": 0,
                "connections_count": len(connections) if connections else 0
            }
    
    def get_port_traffic(self, port: int) -> Dict:
        """Получение трафика для порта"""
        current_time = time.time()
        
        # Проверяем кэш
        cache_key = f"port_{port}"
        if cache_key in self._cache and current_time - self._cache_time < self.cache_duration:
            return self._cache[cache_key]
        
        # Получаем данные
        connections = self._get_port_connections(port)
        current_traffic = self._get_interface_traffic()
        
        # Оцениваем трафик
        traffic_estimate = self._estimate_traffic_from_connections(
            port, connections, current_traffic, self._last_interface_traffic
        )
        
        # Формируем результат
        result = {
            "port": port,
            "connections": len(connections),
            "total_bytes": traffic_estimate["total_bytes"],
            "rx_bytes": traffic_estimate["rx_bytes"],
            "tx_bytes": traffic_estimate["tx_bytes"],
            "total_formatted": self._format_bytes(traffic_estimate["total_bytes"]),
            "rx_formatted": self._format_bytes(traffic_estimate["rx_bytes"]),
            "tx_formatted": self._format_bytes(traffic_estimate["tx_bytes"]),
            "traffic_rate": traffic_estimate["traffic_rate"],
            "interface_traffic": current_traffic,
            "connection_details": connections,
            "timestamp": current_time,
            "source": "simple_monitor",
            "method": "connection_based_estimation"
        }
        
        # Кэшируем результат
        self._cache[cache_key] = result
        self._cache_time = current_time
        
        # Сохраняем текущий трафик для следующего расчета
        self._last_interface_traffic = current_traffic
        self._last_time = current_time
        
        return result
    
    def get_uuid_traffic(self, uuid: str) -> Dict:
        """Получение трафика для UUID (находит порт по UUID из SQLite)"""
        try:
            # Получаем порт для UUID из SQLite
            port = storage.get_port_for_uuid(uuid)
            
            if port is None:
                return {
                    "error": f"No port found for UUID: {uuid}",
                    "uuid": uuid,
                    "port": None,
                    "total_bytes": 0,
                    "connections": 0,
                    "timestamp": time.time()
                }
            
            # Получаем трафик для порта
            port_traffic = self.get_port_traffic(port)
            port_traffic["uuid"] = uuid
            
            return port_traffic
            
        except Exception as e:
            return {
                "error": str(e),
                "uuid": uuid,
                "port": None,
                "total_bytes": 0,
                "connections": 0,
                "timestamp": time.time()
            }
    
    def get_all_ports_traffic(self) -> Dict:
        """Получение трафика для всех портов из SQLite"""
        try:
            # Получаем все назначения портов из SQLite
            used_ports = storage.get_used_ports()
            
            all_traffic = {
                "ports": {},
                "total_connections": 0,
                "total_bytes": 0,
                "timestamp": time.time()
            }
            
            # Обрабатываем все активные порты
            for port, assignment in used_ports.items():
                if assignment.get('is_active', True):
                    uuid = assignment.get('uuid')
                    port_traffic = self.get_port_traffic(port)
                    port_traffic["uuid"] = uuid
                    all_traffic["ports"][str(port)] = port_traffic
                    all_traffic["total_connections"] += port_traffic["connections"]
                    all_traffic["total_bytes"] += port_traffic["total_bytes"]
            
            return all_traffic
            
        except Exception as e:
            return {
                "error": str(e),
                "ports": {},
                "total_connections": 0,
                "total_bytes": 0,
                "timestamp": time.time()
            }
    
    def reset_port_traffic(self, port: int) -> bool:
        """Сброс статистики для порта"""
        try:
            # Очищаем кэш
            cache_key = f"port_{port}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Сбрасываем базовые значения
            self._last_interface_traffic = None
            self._last_time = None
            
            return True
            
        except Exception as e:
            print(f"Error resetting port traffic: {e}")
            return False
    
    def reset_uuid_traffic(self, uuid: str) -> bool:
        """Сброс статистики для UUID"""
        try:
            # Получаем порт для UUID из SQLite
            port = storage.get_port_for_uuid(uuid)
            
            if port:
                return self.reset_port_traffic(port)
            
            return False
            
        except Exception as e:
            print(f"Error resetting UUID traffic: {e}")
            return False

# Глобальный экземпляр монитора
simple_traffic_monitor = SimpleTrafficMonitor()

# Функции для API
def get_simple_port_traffic(port: int) -> Dict:
    """Получение трафика для порта"""
    return simple_traffic_monitor.get_port_traffic(port)

def get_simple_uuid_traffic(uuid: str) -> Dict:
    """Получение трафика для UUID"""
    return simple_traffic_monitor.get_uuid_traffic(uuid)

def get_simple_all_ports_traffic() -> Dict:
    """Получение трафика для всех портов"""
    return simple_traffic_monitor.get_all_ports_traffic()

def reset_simple_port_traffic(port: int) -> bool:
    """Сброс статистики для порта"""
    return simple_traffic_monitor.reset_port_traffic(port)

def reset_simple_uuid_traffic(uuid: str) -> bool:
    """Сброс статистики для UUID"""
    return simple_traffic_monitor.reset_uuid_traffic(uuid) 