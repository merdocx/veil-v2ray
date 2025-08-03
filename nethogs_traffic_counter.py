#!/usr/bin/env python3
"""
Система точного подсчета трафика через nethogs
Получает реальную статистику трафика по процессам
"""

import subprocess
import json
import time
import re
from typing import Dict, List, Optional

class NethogsTrafficCounter:
    def __init__(self):
        self.xray_process = "xray"
    
    def get_xray_traffic(self) -> Dict:
        """Получение трафика для процесса Xray"""
        try:
            # Запускаем nethogs в фоновом режиме для получения статистики
            result = subprocess.run([
                "timeout", "5", "nethogs", "-t", "-v", "3"
            ], capture_output=True, text=True, check=True)
            
            # Парсим вывод nethogs
            lines = result.stdout.split('\n')
            xray_traffic = {
                "process": "xray",
                "sent_bytes": 0,
                "received_bytes": 0,
                "total_bytes": 0,
                "sent_formatted": "0 B",
                "received_formatted": "0 B",
                "total_formatted": "0 B",
                "sent_mb": 0,
                "received_mb": 0,
                "total_mb": 0,
                "timestamp": int(time.time()),
                "source": "nethogs"
            }
            
            for line in lines:
                if self.xray_process in line.lower():
                    # Парсим строку nethogs
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            sent = float(parts[-2])  # Отправлено
                            received = float(parts[-1])  # Получено
                            
                            # Конвертируем в байты (nethogs показывает в KB)
                            sent_bytes = int(sent * 1024)
                            received_bytes = int(received * 1024)
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
                            
                            xray_traffic.update({
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
                            break
                        except (ValueError, IndexError):
                            continue
            
            return xray_traffic
            
        except subprocess.TimeoutExpired:
            return {
                "process": "xray",
                "sent_bytes": 0,
                "received_bytes": 0,
                "total_bytes": 0,
                "sent_formatted": "0 B",
                "received_formatted": "0 B",
                "total_formatted": "0 B",
                "sent_mb": 0,
                "received_mb": 0,
                "total_mb": 0,
                "timestamp": int(time.time()),
                "source": "nethogs",
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "process": "xray",
                "sent_bytes": 0,
                "received_bytes": 0,
                "total_bytes": 0,
                "sent_formatted": "0 B",
                "received_formatted": "0 B",
                "total_formatted": "0 B",
                "sent_mb": 0,
                "received_mb": 0,
                "total_mb": 0,
                "timestamp": int(time.time()),
                "source": "nethogs",
                "error": str(e)
            }
    
    def get_all_processes_traffic(self) -> Dict:
        """Получение трафика для всех процессов"""
        try:
            result = subprocess.run([
                "timeout", "5", "nethogs", "-t", "-v", "3"
            ], capture_output=True, text=True, check=True)
            
            processes = []
            total_sent = 0
            total_received = 0
            
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('Refreshing'):
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            process_name = parts[0]
                            sent = float(parts[-2])
                            received = float(parts[-1])
                            
                            sent_bytes = int(sent * 1024)
                            received_bytes = int(received * 1024)
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
                            
                            processes.append({
                                "process": process_name,
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
                            
                            total_sent += sent_bytes
                            total_received += received_bytes
                            
                        except (ValueError, IndexError):
                            continue
            
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
                "total_sent_bytes": total_sent,
                "total_received_bytes": total_received,
                "total_bytes": total_sent + total_received,
                "total_sent_formatted": format_bytes(total_sent),
                "total_received_formatted": format_bytes(total_received),
                "total_formatted": format_bytes(total_sent + total_received),
                "total_sent_mb": round(total_sent / (1024 * 1024), 2),
                "total_received_mb": round(total_received / (1024 * 1024), 2),
                "total_mb": round((total_sent + total_received) / (1024 * 1024), 2),
                "processes": processes,
                "source": "nethogs"
            }
            
        except Exception as e:
            return {
                "total_sent_bytes": 0,
                "total_received_bytes": 0,
                "total_bytes": 0,
                "total_sent_formatted": "0 B",
                "total_received_formatted": "0 B",
                "total_formatted": "0 B",
                "total_sent_mb": 0,
                "total_received_mb": 0,
                "total_mb": 0,
                "processes": [],
                "source": "nethogs",
                "error": str(e)
            }

# Глобальный экземпляр
nethogs_counter = NethogsTrafficCounter()

def get_xray_traffic_bytes() -> Dict:
    """Получение точной статистики трафика для Xray"""
    return nethogs_counter.get_xray_traffic()

def get_all_processes_traffic_bytes() -> Dict:
    """Получение точной статистики трафика для всех процессов"""
    return nethogs_counter.get_all_processes_traffic()

if __name__ == "__main__":
    print("=== СИСТЕМА ТОЧНОГО ПОДСЧЕТА ТРАФИКА (NETHOGS) ===")
    print()
    
    # Тестирование
    xray_traffic = get_xray_traffic_bytes()
    print(f"Xray трафик: {xray_traffic['total_formatted']}")
    print(f"Отправлено: {xray_traffic['sent_formatted']}")
    print(f"Получено: {xray_traffic['received_formatted']}")
    print()
    
    all_traffic = get_all_processes_traffic_bytes()
    print(f"Общий трафик системы: {all_traffic['total_formatted']}")
    print(f"Всего процессов: {len(all_traffic['processes'])}")
    print()
    
    for proc in all_traffic['processes'][:5]:  # Показываем топ-5
        print(f"{proc['process']}: {proc['total_formatted']}") 