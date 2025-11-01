#!/usr/bin/env python3
"""
Скрипт мониторинга здоровья VPN сервиса
Проверяет Xray, API, порты и автоматически перезапускает при проблемах
"""

import subprocess
import time
import requests
import json
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/vpn-server/logs/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Отключение предупреждений SSL
requests.packages.urllib3.disable_warnings()

def check_xray():
    """Проверка статуса Xray сервиса"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'xray'], 
                              capture_output=True, text=True, timeout=5)
        is_active = result.stdout.strip() == 'active'
        if not is_active:
            logger.warning(f"Xray status: {result.stdout.strip()}")
        return is_active
    except Exception as e:
        logger.error(f"Error checking Xray: {e}")
        return False

def check_ports():
    """Проверка открытых портов VPN"""
    try:
        result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True, timeout=10)
        
        # Получаем количество активных ключей
        keys_file = '/root/vpn-server/config/keys.json'
        if os.path.exists(keys_file):
            with open(keys_file, 'r') as f:
                keys = json.load(f)
            expected_ports = len([k for k in keys if k.get('is_active', True)])
        else:
            expected_ports = 0
        
        # Считаем открытые VPN порты
        vpn_ports_count = 0
        for line in result.stdout.split('\n'):
            for port in range(10001, 10101):
                if f':{port}' in line and 'LISTEN' in line:
                    vpn_ports_count += 1
                    break
        
        # 90% портов должны быть открыты (минимально 1 если есть ключи)
        if expected_ports == 0:
            return True  # Нет ключей - нет проблем
        
        min_expected = max(1, int(expected_ports * 0.9))
        is_ok = vpn_ports_count >= min_expected
        
        if not is_ok:
            logger.warning(f"Ports check: {vpn_ports_count}/{expected_ports} ports open")
        
        return is_ok
    except Exception as e:
        logger.error(f"Error checking ports: {e}")
        return False

def check_api():
    """Проверка API"""
    try:
        response = requests.get('https://localhost:8000/health', 
                              verify=False, timeout=5)
        is_ok = response.status_code == 200
        if not is_ok:
            logger.warning(f"API status code: {response.status_code}")
        return is_ok
    except Exception as e:
        logger.error(f"Error checking API: {e}")
        return False

def restart_xray():
    """Перезапуск Xray"""
    try:
        logger.warning("Restarting Xray service...")
        result = subprocess.run(['systemctl', 'restart', 'xray'], 
                              timeout=30, capture_output=True, text=True)
        time.sleep(5)
        if result.returncode == 0:
            is_active = check_xray()
            if is_active:
                logger.info("Xray restarted successfully")
                return True
            else:
                logger.error("Xray restart failed - service not active")
                return False
        else:
            logger.error(f"Xray restart command failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error restarting Xray: {e}")
        return False

def restart_api():
    """Перезапуск API"""
    try:
        logger.warning("Restarting VPN API service...")
        result = subprocess.run(['systemctl', 'restart', 'vpn-api'], 
                              timeout=30, capture_output=True, text=True)
        time.sleep(5)
        if result.returncode == 0:
            is_active = check_api()
            if is_active:
                logger.info("API restarted successfully")
                return True
            else:
                logger.error("API restart failed - not responding")
                return False
        else:
            logger.error(f"API restart command failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error restarting API: {e}")
        return False

def main():
    """Основная функция мониторинга"""
    logger.info("=== VPN Health Check ===")
    
    xray_ok = check_xray()
    ports_ok = check_ports()
    api_ok = check_api()
    
    issues = []
    
    if not xray_ok:
        issues.append("Xray")
        logger.error("Xray is not running, attempting restart...")
        if restart_xray():
            logger.info("✅ Xray restarted successfully")
        else:
            logger.error("❌ Failed to restart Xray")
    
    if not ports_ok and xray_ok:
        issues.append("Ports")
        logger.warning("Some VPN ports are not open, restarting Xray...")
        restart_xray()
    
    if not api_ok:
        issues.append("API")
        logger.error("API is not responding, attempting restart...")
        if restart_api():
            logger.info("✅ API restarted successfully")
        else:
            logger.error("❌ Failed to restart API")
    
    if xray_ok and ports_ok and api_ok:
        logger.info("✅ All checks passed - system healthy")
        return 0
    else:
        logger.warning(f"⚠️  Issues detected: {', '.join(issues)}")
        return 1

if __name__ == '__main__':
    exit(main())

