#!/usr/bin/env python3
"""
Анализатор трафика на основе логов Xray
Подсчитывает количество подключений для каждого пользователя
"""

import re
import json
import time
from datetime import datetime
from typing import Dict, List

def parse_access_log(log_file: str = "/root/vpn-server/logs/access.log") -> Dict[str, int]:
    """Парсинг логов доступа для подсчета подключений"""
    user_connections = {}
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Ищем строки с email пользователя
                match = re.search(r'email: ([a-f0-9-]+)', line)
                if match:
                    email = match.group(1)
                    user_connections[email] = user_connections.get(email, 0) + 1
    except FileNotFoundError:
        print(f"Файл логов {log_file} не найден")
        return {}
    
    return user_connections

def estimate_traffic_from_connections(connections: int) -> Dict:
    """Примерная оценка трафика на основе количества подключений"""
    # Примерная оценка: каждое подключение ~1-5 МБ
    avg_bytes_per_connection = 3 * 1024 * 1024  # 3 МБ в среднем
    total_bytes = connections * avg_bytes_per_connection
    
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
        "connections": connections,
        "estimated_bytes": total_bytes,
        "estimated_formatted": format_bytes(total_bytes),
        "estimated_mb": round(total_bytes / (1024 * 1024), 2),
        "source": "log_analysis"
    }

def get_traffic_from_logs(uuid: str) -> Dict:
    """Получение трафика для конкретного пользователя из логов"""
    user_connections = parse_access_log()
    
    if uuid not in user_connections:
        return {
            "uuid": uuid,
            "connections": 0,
            "estimated_bytes": 0,
            "estimated_formatted": "0 B",
            "estimated_mb": 0,
            "timestamp": int(time.time()),
            "source": "log_analysis",
            "note": "Пользователь не найден в логах"
        }
    
    traffic_data = estimate_traffic_from_connections(user_connections[uuid])
    
    return {
        "uuid": uuid,
        "connections": traffic_data["connections"],
        "estimated_bytes": traffic_data["estimated_bytes"],
        "estimated_formatted": traffic_data["estimated_formatted"],
        "estimated_mb": traffic_data["estimated_mb"],
        "timestamp": int(time.time()),
        "source": "log_analysis",
        "note": "Оценка на основе количества подключений"
    }

def get_all_traffic_from_logs() -> Dict:
    """Получение трафика для всех пользователей из логов"""
    user_connections = parse_access_log()
    
    if not user_connections:
        return {
            "total_connections": 0,
            "total_estimated_bytes": 0,
            "total_estimated_formatted": "0 B",
            "total_estimated_mb": 0,
            "users": [],
            "source": "log_analysis"
        }
    
    total_connections = sum(user_connections.values())
    total_traffic = estimate_traffic_from_connections(total_connections)
    
    users_data = []
    for uuid, connections in user_connections.items():
        user_traffic = estimate_traffic_from_connections(connections)
        users_data.append({
            "uuid": uuid,
            "connections": connections,
            "estimated_bytes": user_traffic["estimated_bytes"],
            "estimated_formatted": user_traffic["estimated_formatted"],
            "estimated_mb": user_traffic["estimated_mb"]
        })
    
    return {
        "total_connections": total_connections,
        "total_estimated_bytes": total_traffic["estimated_bytes"],
        "total_estimated_formatted": total_traffic["estimated_formatted"],
        "total_estimated_mb": total_traffic["estimated_mb"],
        "users": users_data,
        "source": "log_analysis"
    }

if __name__ == "__main__":
    # Тестирование
    print("=== АНАЛИЗ ТРАФИКА ИЗ ЛОГОВ ===")
    print()
    
    all_traffic = get_all_traffic_from_logs()
    print(f"Общий трафик: {all_traffic['total_estimated_formatted']}")
    print(f"Всего подключений: {all_traffic['total_connections']}")
    print()
    
    for user in all_traffic['users']:
        print(f"Пользователь {user['uuid']}: {user['estimated_formatted']} ({user['connections']} подключений)") 