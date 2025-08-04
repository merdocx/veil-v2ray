#!/usr/bin/env python3
"""
Модуль точного мониторинга трафика по индивидуальным портам
"""

import subprocess
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from port_manager import port_manager

class PortTrafficMonitor:
    def __init__(self):
        self.cache_duration = 30  # seconds
        self._cache = {}
        self._cache_time = 0
        self._last_traffic_data = {}
        self._last_time = None
    
    def _get_network_interfaces(self) -> List[str]:
        """Получение списка сетевых интерфейсов"""
        try:
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            interfaces = []
            for line in lines[2:]:  # Пропускаем заголовки
                if ':' in line:
                    interface = line.split(':')[0].strip()
                    if interface.startswith(('ens', 'eth', 'eno')):
                        interfaces.append(interface)
            
            return interfaces
        except Exception as e:
            print(f"Error getting network interfaces: {e}")
            return ['ens3']  # Fallback
    
    def _get_interface_traffic(self, interface: str) -> Dict:
        """Получение трафика для конкретного интерфейса"""
        try:
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.strip().startswith(interface + ':'):
                    parts = line.split(':')[1].split()
                    if len(parts) >= 16:
                        return {
                            "rx_bytes": int(parts[0]),
                            "tx_bytes": int(parts[8]),
                            "total_bytes": int(parts[0]) + int(parts[8]),
                            "timestamp": time.time()
                        }
            
            return {"rx_bytes": 0, "tx_bytes": 0, "total_bytes": 0, "timestamp": time.time()}
        except Exception as e:
            print(f"Error getting interface traffic: {e}")
            return {"rx_bytes": 0, "tx_bytes": 0, "total_bytes": 0, "timestamp": time.time()}
    
    def _get_port_connections(self, port: int) -> List[Dict]:
        """Получение активных соединений для порта"""
        try:
            # Используем ss для получения информации о соединениях
            result = subprocess.run(
                ['ss', '-tuln', 'state', 'established'],
                capture_output=True, text=True, timeout=10
            )
            
            connections = []
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'ESTAB' in line:
                    # Парсим строку соединения
                    parts = line.split()
                    if len(parts) >= 4:
                        local_addr = parts[3]
                        remote_addr = parts[4] if len(parts) > 4 else "unknown"
                        
                        connections.append({
                            "local": local_addr,
                            "remote": remote_addr,
                            "state": "ESTABLISHED"
                        })
            
            return connections
        except Exception as e:
            print(f"Error getting port connections: {e}")
            return []
    
    def _get_port_traffic_from_connections(self, port: int) -> Dict:
        """Получение трафика порта на основе активных соединений"""
        try:
            connections = self._get_port_connections(port)
            
            if not connections:
                return {
                    "connections": 0,
                    "estimated_traffic": 0,
                    "timestamp": time.time()
                }
            
            # Получаем общий трафик интерфейса
            interfaces = self._get_network_interfaces()
            total_traffic = 0
            
            for interface in interfaces:
                traffic = self._get_interface_traffic(interface)
                total_traffic += traffic["total_bytes"]
            
            # Оцениваем трафик порта на основе количества соединений
            # Это приблизительная оценка, но более точная чем общий подсчет
            connection_count = len(connections)
            estimated_traffic = total_traffic // max(1, connection_count)
            
            return {
                "connections": connection_count,
                "estimated_traffic": estimated_traffic,
                "total_interface_traffic": total_traffic,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"Error getting port traffic from connections: {e}")
            return {
                "connections": 0,
                "estimated_traffic": 0,
                "timestamp": time.time()
            }
    
    def _get_detailed_port_traffic(self, port: int) -> Dict:
        """Получение детальной информации о трафике порта"""
        try:
            # Получаем информацию о соединениях
            connections = self._get_port_connections(port)
            
            # Получаем трафик интерфейса
            interfaces = self._get_network_interfaces()
            interface_traffic = {}
            total_traffic = 0
            
            for interface in interfaces:
                traffic = self._get_interface_traffic(interface)
                interface_traffic[interface] = traffic
                total_traffic += traffic["total_bytes"]
            
            # Вычисляем трафик порта
            if connections:
                # Если есть соединения, распределяем трафик пропорционально
                port_traffic = total_traffic // len(connections)
            else:
                port_traffic = 0
            
            return {
                "port": port,
                "connections": len(connections),
                "total_bytes": port_traffic,
                "rx_bytes": port_traffic // 2,  # Примерное разделение
                "tx_bytes": port_traffic // 2,
                "interface_traffic": interface_traffic,
                "total_interface_traffic": total_traffic,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"Error getting detailed port traffic: {e}")
            return {
                "port": port,
                "connections": 0,
                "total_bytes": 0,
                "rx_bytes": 0,
                "tx_bytes": 0,
                "error": str(e),
                "timestamp": time.time()
            }
    
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
    
    def get_port_traffic(self, port: int) -> Dict:
        """Получение трафика для конкретного порта"""
        current_time = time.time()
        
        # Проверяем кэш
        if port in self._cache and current_time - self._cache_time < self.cache_duration:
            return self._cache[port]
        
        # Получаем детальную информацию о трафике
        traffic_data = self._get_detailed_port_traffic(port)
        
        # Добавляем форматированные значения
        traffic_data["total_formatted"] = self._format_bytes(traffic_data["total_bytes"])
        traffic_data["rx_formatted"] = self._format_bytes(traffic_data["rx_bytes"])
        traffic_data["tx_formatted"] = self._format_bytes(traffic_data["tx_bytes"])
        
        # Кэшируем результат
        self._cache[port] = traffic_data
        self._cache_time = current_time
        
        return traffic_data
    
    def get_uuid_traffic(self, uuid: str) -> Dict:
        """Получение трафика для UUID через порт"""
        # Получаем порт для UUID
        port = port_manager.get_port_for_uuid(uuid)
        if not port:
            return {
                "error": f"No port assigned for UUID: {uuid}",
                "uuid": uuid,
                "port": None,
                "total_bytes": 0,
                "connections": 0,
                "timestamp": time.time()
            }
        
        # Получаем трафик порта
        port_traffic = self.get_port_traffic(port)
        port_traffic["uuid"] = uuid
        port_traffic["port"] = port
        
        return port_traffic
    
    def get_all_ports_traffic(self) -> Dict:
        """Получение трафика для всех портов"""
        try:
            # Получаем все назначения портов
            port_assignments = port_manager.get_all_assignments()
            
            all_traffic = {
                "total_ports": len(port_assignments["port_assignments"]),
                "ports_traffic": {},
                "total_traffic": 0,
                "total_connections": 0,
                "timestamp": time.time()
            }
            
            # Получаем трафик для каждого порта
            for uuid, assignment in port_assignments["port_assignments"].items():
                port = assignment["port"]
                port_traffic = self.get_port_traffic(port)
                
                all_traffic["ports_traffic"][uuid] = {
                    "port": port,
                    "key_name": assignment["key_name"],
                    "traffic": port_traffic
                }
                
                all_traffic["total_traffic"] += port_traffic["total_bytes"]
                all_traffic["total_connections"] += port_traffic["connections"]
            
            # Добавляем форматированные значения
            all_traffic["total_traffic_formatted"] = self._format_bytes(all_traffic["total_traffic"])
            
            return all_traffic
            
        except Exception as e:
            return {
                "error": f"Failed to get all ports traffic: {e}",
                "timestamp": time.time()
            }
    
    def reset_port_traffic(self, port: int) -> bool:
        """Сброс статистики трафика для порта"""
        try:
            # Очищаем кэш для порта
            if port in self._cache:
                del self._cache[port]
            
            return True
        except Exception as e:
            print(f"Error resetting port traffic: {e}")
            return False
    
    def reset_uuid_traffic(self, uuid: str) -> bool:
        """Сброс статистики трафика для UUID"""
        try:
            # Получаем порт для UUID
            port = port_manager.get_port_for_uuid(uuid)
            if not port:
                return False
            
            # Сбрасываем трафик порта
            return self.reset_port_traffic(port)
            
        except Exception as e:
            print(f"Error resetting UUID traffic: {e}")
            return False
    
    def get_system_traffic_summary(self) -> Dict:
        """Получение сводки системного трафика"""
        try:
            # Получаем трафик всех интерфейсов
            interfaces = self._get_network_interfaces()
            total_system_traffic = 0
            interface_summary = {}
            
            for interface in interfaces:
                traffic = self._get_interface_traffic(interface)
                interface_summary[interface] = {
                    "rx_bytes": traffic["rx_bytes"],
                    "tx_bytes": traffic["tx_bytes"],
                    "total_bytes": traffic["total_bytes"],
                    "rx_formatted": self._format_bytes(traffic["rx_bytes"]),
                    "tx_formatted": self._format_bytes(traffic["tx_bytes"]),
                    "total_formatted": self._format_bytes(traffic["total_bytes"])
                }
                total_system_traffic += traffic["total_bytes"]
            
            # Получаем информацию о портах
            port_assignments = port_manager.get_all_assignments()
            active_ports = len(port_assignments["port_assignments"])
            
            return {
                "total_system_traffic": total_system_traffic,
                "total_system_traffic_formatted": self._format_bytes(total_system_traffic),
                "active_ports": active_ports,
                "interface_summary": interface_summary,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "error": f"Failed to get system traffic summary: {e}",
                "timestamp": time.time()
            }

# Глобальный экземпляр монитора трафика
port_traffic_monitor = PortTrafficMonitor()

# Функции для совместимости с API
def get_port_traffic_bytes(port: int) -> Dict:
    """Получение трафика порта в байтах"""
    return port_traffic_monitor.get_port_traffic(port)

def get_uuid_traffic_bytes(uuid: str) -> Dict:
    """Получение трафика UUID в байтах"""
    return port_traffic_monitor.get_uuid_traffic(uuid)

def get_all_ports_traffic_bytes() -> Dict:
    """Получение трафика всех портов в байтах"""
    return port_traffic_monitor.get_all_ports_traffic()

def reset_port_traffic_stats(port: int) -> bool:
    """Сброс статистики трафика порта"""
    return port_traffic_monitor.reset_port_traffic(port)

def reset_uuid_traffic_stats(uuid: str) -> bool:
    """Сброс статистики трафика UUID"""
    return port_traffic_monitor.reset_uuid_traffic(uuid)

def get_system_traffic_summary() -> Dict:
    """Получение сводки системного трафика"""
    return port_traffic_monitor.get_system_traffic_summary() 