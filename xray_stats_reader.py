#!/usr/bin/env python3
"""
Модуль для чтения реальной статистики трафика из Xray Stats API
"""

import subprocess
import json
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class XrayStatsReader:
    """Чтение статистики из Xray Stats API"""
    
    def __init__(self, stats_api_server: str = "127.0.0.1:10808"):
        self.stats_api_server = stats_api_server
    
    def _query_stats(self, pattern: str = "") -> Optional[Dict]:
        """Запрос статистики из Xray Stats API"""
        try:
            cmd = ['/usr/local/bin/xray', 'api', 'statsquery', 
                   f'--server={self.stats_api_server}']
            
            if pattern:
                cmd.extend(['-pattern', pattern])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error(f"Xray Stats API error: {result.stderr}")
                return None
            
            try:
                data = json.loads(result.stdout)
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Stats API response: {e}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Xray Stats API timeout")
            return None
        except Exception as e:
            logger.error(f"Error querying Stats API: {e}")
            return None
    
    def get_user_traffic(self, user_uuid: str) -> Dict[str, int]:
        """Получить трафик конкретного пользователя по UUID"""
        pattern = f"user>>>{user_uuid}"
        data = self._query_stats(pattern)
        
        if not data or 'stat' not in data:
            return {
                "uplink": 0,
                "downlink": 0,
                "total": 0
            }
        
        uplink = 0
        downlink = 0
        
        for stat in data.get('stat', []):
            name = stat.get('name', '')
            value = stat.get('value', 0)
            
            if 'uplink' in name:
                uplink = value
            elif 'downlink' in name:
                downlink = value
        
        return {
            "uplink": int(uplink),
            "downlink": int(downlink),
            "total": int(uplink + downlink)
        }
    
    def get_all_users_traffic(self) -> Dict[str, Dict[str, int]]:
        """Получить трафик всех пользователей"""
        data = self._query_stats()
        
        if not data or 'stat' not in data:
            return {}
        
        users_traffic = {}
        
        for stat in data['stat']:
            name = stat.get('name', '')
            value = stat.get('value', 0)
            
            # Парсим имя: user>>>UUID>>>traffic>>>direction
            if 'user>>>' in name and '>>>traffic>>>' in name:
                parts = name.split('>>>')
                if len(parts) >= 4:
                    user_uuid = parts[1]
                    direction = parts[3]  # uplink или downlink
                    
                    if user_uuid not in users_traffic:
                        users_traffic[user_uuid] = {
                            "uplink": 0,
                            "downlink": 0,
                            "total": 0
                        }
                    
                    users_traffic[user_uuid][direction] = value
                    users_traffic[user_uuid]["total"] = (
                        users_traffic[user_uuid]["uplink"] + 
                        users_traffic[user_uuid]["downlink"]
                    )
        
        return users_traffic
    
    def get_inbound_traffic(self, inbound_tag: str) -> Dict[str, int]:
        """Получить трафик для конкретного inbound"""
        pattern = f"inbound>>>{inbound_tag}"
        data = self._query_stats(pattern)
        
        if not data or 'stat' not in data:
            return {
                "uplink": 0,
                "downlink": 0,
                "total": 0
            }
        
        uplink = 0
        downlink = 0
        
        for stat in data['stat']:
            name = stat.get('name', '')
            value = stat.get('value', 0)
            
            if 'uplink' in name:
                uplink = value
            elif 'downlink' in name:
                downlink = value
        
        return {
            "uplink": uplink,
            "downlink": downlink,
            "total": uplink + downlink
        }


# Глобальный экземпляр
xray_stats_reader = XrayStatsReader()

def get_xray_user_traffic(uuid: str) -> Dict[str, int]:
    """Получить трафик пользователя из Xray Stats API"""
    return xray_stats_reader.get_user_traffic(uuid)

def get_all_xray_users_traffic() -> Dict[str, Dict[str, int]]:
    """Получить трафик всех пользователей из Xray Stats API"""
    return xray_stats_reader.get_all_users_traffic()

