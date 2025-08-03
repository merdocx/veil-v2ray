#!/usr/bin/env python3
"""
Система точного подсчета трафика через iptables
Создает отдельные правила для каждого пользователя VPN
"""

import subprocess
import json
import time
import re
from typing import Dict, List, Optional

class IptablesTrafficCounter:
    def __init__(self):
        self.chain_name = "VPN_TRAFFIC"
        self.setup_chain()
    
    def setup_chain(self):
        """Создание цепочки iptables для подсчета трафика"""
        try:
            # Создаем новую цепочку
            subprocess.run(["iptables", "-N", self.chain_name], 
                         capture_output=True, check=False)
            
            # Добавляем правило для перехода в нашу цепочку
            subprocess.run(["iptables", "-A", "OUTPUT", "-p", "tcp", "--dport", "443", 
                          "-j", self.chain_name], capture_output=True, check=False)
            
            print(f"✅ Цепочка {self.chain_name} создана")
        except Exception as e:
            print(f"⚠️ Цепочка уже существует или ошибка: {e}")
    
    def add_user_rule(self, uuid: str, port: int = 443):
        """Добавление правила для подсчета трафика пользователя"""
        try:
            # Удаляем существующее правило если есть
            self.remove_user_rule(uuid)
            
            # Добавляем правило для подсчета исходящего трафика
            subprocess.run([
                "iptables", "-A", self.chain_name,
                "-p", "tcp", "--dport", str(port),
                "-m", "comment", "--comment", f"user_{uuid}",
                "-j", "ACCEPT"
            ], capture_output=True, check=True)
            
            print(f"✅ Правило для пользователя {uuid} добавлено")
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления правила для {uuid}: {e}")
            return False
    
    def remove_user_rule(self, uuid: str):
        """Удаление правила для пользователя"""
        try:
            # Находим и удаляем правило
            result = subprocess.run([
                "iptables", "-L", self.chain_name, "--line-numbers"
            ], capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n'):
                if f"user_{uuid}" in line:
                    line_num = line.split()[0]
                    subprocess.run([
                        "iptables", "-D", self.chain_name, line_num
                    ], capture_output=True, check=True)
                    print(f"✅ Правило для пользователя {uuid} удалено")
                    break
        except Exception as e:
            print(f"⚠️ Ошибка удаления правила для {uuid}: {e}")
    
    def get_user_traffic(self, uuid: str) -> Dict:
        """Получение статистики трафика для пользователя"""
        try:
            result = subprocess.run([
                "iptables", "-L", self.chain_name, "-n", "-v"
            ], capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n'):
                if f"user_{uuid}" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        packets = int(parts[1])
                        bytes_count = int(parts[2])
                        
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
                            "packets": packets,
                            "bytes": bytes_count,
                            "formatted": format_bytes(bytes_count),
                            "mb": round(bytes_count / (1024 * 1024), 2),
                            "timestamp": int(time.time()),
                            "source": "iptables"
                        }
            
            return {
                "uuid": uuid,
                "packets": 0,
                "bytes": 0,
                "formatted": "0 B",
                "mb": 0,
                "timestamp": int(time.time()),
                "source": "iptables",
                "error": "Правило не найдено"
            }
            
        except Exception as e:
            return {
                "uuid": uuid,
                "packets": 0,
                "bytes": 0,
                "formatted": "0 B",
                "mb": 0,
                "timestamp": int(time.time()),
                "source": "iptables",
                "error": str(e)
            }
    
    def get_all_traffic(self) -> Dict:
        """Получение статистики трафика для всех пользователей"""
        try:
            result = subprocess.run([
                "iptables", "-L", self.chain_name, "-n", "-v"
            ], capture_output=True, text=True, check=True)
            
            users_data = []
            total_packets = 0
            total_bytes = 0
            
            for line in result.stdout.split('\n'):
                if "user_" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        packets = int(parts[1])
                        bytes_count = int(parts[2])
                        
                        # Извлекаем UUID из комментария
                        uuid_match = re.search(r"user_([a-f0-9-]+)", line)
                        if uuid_match:
                            uuid = uuid_match.group(1)
                            
                            def format_bytes(bytes_value: int) -> str:
                                if bytes_value < 1024:
                                    return f"{bytes_value} B"
                                elif bytes_value < 1024 * 1024:
                                    return f"{bytes_value / 1024:.2f} KB"
                                elif bytes_value < 1024 * 1024 * 1024:
                                    return f"{bytes_value / (1024 * 1024):.2f} MB"
                                else:
                                    return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
                            
                            users_data.append({
                                "uuid": uuid,
                                "packets": packets,
                                "bytes": bytes_count,
                                "formatted": format_bytes(bytes_count),
                                "mb": round(bytes_count / (1024 * 1024), 2)
                            })
                            
                            total_packets += packets
                            total_bytes += bytes_count
            
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
                "total_packets": total_packets,
                "total_bytes": total_bytes,
                "total_formatted": format_bytes(total_bytes),
                "total_mb": round(total_bytes / (1024 * 1024), 2),
                "users": users_data,
                "source": "iptables"
            }
            
        except Exception as e:
            return {
                "total_packets": 0,
                "total_bytes": 0,
                "total_formatted": "0 B",
                "total_mb": 0,
                "users": [],
                "source": "iptables",
                "error": str(e)
            }
    
    def reset_user_traffic(self, uuid: str) -> bool:
        """Сброс статистики для пользователя"""
        try:
            # Удаляем и добавляем правило заново
            self.remove_user_rule(uuid)
            return self.add_user_rule(uuid)
        except Exception as e:
            print(f"❌ Ошибка сброса статистики для {uuid}: {e}")
            return False

# Глобальный экземпляр
traffic_counter = IptablesTrafficCounter()

def get_key_traffic_bytes(uuid: str) -> Dict:
    """Получение точной статистики трафика для ключа"""
    return traffic_counter.get_user_traffic(uuid)

def get_all_keys_traffic_bytes() -> Dict:
    """Получение точной статистики трафика для всех ключей"""
    return traffic_counter.get_all_traffic()

def add_key_to_traffic_counter(uuid: str) -> bool:
    """Добавление ключа в систему подсчета трафика"""
    return traffic_counter.add_user_rule(uuid)

def reset_key_traffic(uuid: str) -> bool:
    """Сброс статистики трафика для ключа"""
    return traffic_counter.reset_user_traffic(uuid)

if __name__ == "__main__":
    print("=== СИСТЕМА ТОЧНОГО ПОДСЧЕТА ТРАФИКА ===")
    print()
    
    # Тестирование
    all_traffic = get_all_keys_traffic_bytes()
    print(f"Общий трафик: {all_traffic['total_formatted']}")
    print(f"Всего пакетов: {all_traffic['total_packets']}")
    print()
    
    for user in all_traffic['users']:
        print(f"Пользователь {user['uuid']}: {user['formatted']} ({user['packets']} пакетов)") 