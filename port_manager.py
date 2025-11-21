#!/usr/bin/env python3
"""
SQLite-backed port management with legacy JSON syncing.
"""

import subprocess
from typing import Dict, Optional

from storage.sqlite_storage import storage


class PortManager:
    def __init__(self):
        self.port_range_start = 10001
        self.port_range_end = 10100
        self.max_ports = self.port_range_end - self.port_range_start + 1  # 100 портов (10001-10100)
    
    def _check_port_availability(self, port: int) -> bool:
        """Проверка доступности порта"""
        try:
            # Проверяем, что порт не используется другими процессами
            result = subprocess.run(
                ['/usr/bin/ss', '-tuln'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                # Ищем порт в выводе
                for line in result.stdout.split('\n'):
                    if f':{port}' in line:
                        return False  # Порт занят
                return True  # Порт свободен
            else:
                print(f"Error running ss command: {result.stderr}")
                return True  # В случае ошибки считаем порт свободным
        except Exception as e:
            print(f"Error checking port availability: {e}")
            return True  # В случае ошибки считаем порт свободным
    
    def get_available_port(self) -> Optional[int]:
        """Получение свободного порта"""
        used_ports = set(storage.get_used_ports().keys())
        
        # Если это первый ключ, используем порт 10001 (443 занят Nginx)
        if len(used_ports) == 0:
            if self._check_port_availability(10001):
                return 10001
        
        # Ищем первый свободный порт в диапазоне 10001-10100
        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in used_ports and self._check_port_availability(port):
                return port
        
        return None
    
    def assign_port(self, uuid: str, key_id: str, key_name: str) -> Optional[int]:
        """Назначение порта для ключа"""
        port = self.get_available_port()
        if not port:
            return None
        storage.add_port_assignment(uuid, key_id, key_name, port)
        return port
    
    def release_port(self, uuid: str) -> bool:
        """Освобождение порта"""
        return storage.release_port_assignment(uuid)
    
    def get_port_for_uuid(self, uuid: str) -> Optional[int]:
        """Получение порта для UUID"""
        return storage.get_port_for_uuid(uuid)
    
    def get_uuid_for_port(self, port: int) -> Optional[str]:
        """Получение UUID для порта"""
        used_ports = storage.get_used_ports()
        if port in used_ports:
            return used_ports[port]["uuid"]
        return None
    
    def get_all_assignments(self) -> Dict:
        """Получение всех назначений портов"""
        return storage.get_ports_snapshot()
    
    def get_used_ports_count(self) -> int:
        """Получение количества использованных портов"""
        return storage.get_used_ports_count()
    
    def get_available_ports_count(self) -> int:
        """Получение количества свободных портов"""
        return self.max_ports - self.get_used_ports_count()
    
    def reset_all_ports(self) -> bool:
        """Сброс всех портов"""
        return storage.reset_ports()
    
    def validate_port_assignments(self) -> Dict:
        """Валидация назначений портов"""
        ports_data = storage.get_ports_snapshot()
        issues = []
        
        # Проверяем соответствие между used_ports и port_assignments
        for port_str, port_info in ports_data["used_ports"].items():
            uuid = port_info["uuid"]
            if uuid not in ports_data["port_assignments"]:
                issues.append(f"Port {port_str} has no assignment for UUID {uuid}")
        
        for uuid, assignment in ports_data["port_assignments"].items():
            port_str = str(assignment["port"])
            if port_str not in ports_data["used_ports"]:
                issues.append(f"UUID {uuid} has no port in used_ports")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_assignments": len(ports_data["port_assignments"]),
            "total_used_ports": len(ports_data["used_ports"])
        }

# Глобальный экземпляр менеджера портов
port_manager = PortManager()

# Функции для совместимости с API
def assign_port_for_key(uuid: str, key_id: str, key_name: str) -> Optional[int]:
    """Назначение порта для ключа"""
    return port_manager.assign_port(uuid, key_id, key_name)

def release_port_for_key(uuid: str) -> bool:
    """Освобождение порта для ключа"""
    return port_manager.release_port(uuid)

def get_port_for_key(uuid: str) -> Optional[int]:
    """Получение порта для ключа"""
    return port_manager.get_port_for_uuid(uuid)

def get_all_port_assignments() -> Dict:
    """Получение всех назначений портов"""
    return port_manager.get_all_assignments()

def reset_all_ports() -> bool:
    """Сброс всех портов"""
    return port_manager.reset_all_ports() 