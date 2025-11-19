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
from typing import Any, Dict

import psutil

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

ENV_PATH = "/root/vpn-server/.env"
STATE_FILE = "/root/vpn-server/logs/monitor_state.json"


def load_env_file(path: str):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file(ENV_PATH)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)
SERVER_NAME = os.getenv("SERVER_NAME", "VPN Server")

CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "75"))
CPU_ALERT_COUNT = int(os.getenv("CPU_ALERT_COUNT", "5"))


def send_telegram_message(text: str):
    if not TELEGRAM_ENABLED:
        return
    try:
        # Добавляем префикс с названием сервера
        message = f"🖥️ [{SERVER_NAME}]\n\n{text}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        }
        response = requests.post(url, data=payload, timeout=5)
        if response.status_code != 200:
            logger.error(
                "Failed to send Telegram message: %s", response.text[:200]
            )
    except Exception as exc:
        logger.error("Telegram notification error: %s", exc)


def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:
            logger.error("Failed to load monitor state: %s", exc)
    return {"cpu_high_count": 0, "last_cpu": 0.0}


def save_state(state: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    except Exception as exc:
        logger.error("Failed to save monitor state: %s", exc)


def check_cpu_usage(state: Dict[str, Any]):
    cpu_usage = psutil.cpu_percent(interval=1)
    state["last_cpu"] = cpu_usage
    logger.info("CPU usage: %.1f%%", cpu_usage)

    if cpu_usage >= CPU_THRESHOLD:
        state["cpu_high_count"] = state.get("cpu_high_count", 0) + 1
        logger.warning(
            "CPU usage above threshold %.1f%% (%d/%d)",
            CPU_THRESHOLD,
            state["cpu_high_count"],
            CPU_ALERT_COUNT,
        )
        if state["cpu_high_count"] >= CPU_ALERT_COUNT:
            send_telegram_message(
                f"⚠️ CPU load {cpu_usage:.1f}% превышает порог {CPU_THRESHOLD}% "
                f"{CPU_ALERT_COUNT} проверок подряд"
            )
            state["cpu_high_count"] = 0
    else:
        state["cpu_high_count"] = 0

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
    state = load_state()
    
    xray_ok = check_xray()
    ports_ok = check_ports()
    api_ok = check_api()
    
    issues = []
    
    if not xray_ok:
        issues.append("Xray")
        logger.error("Xray is not running, attempting restart...")
        send_telegram_message("⚠️ Xray сервис не активен. Перезапуск...")
        if restart_xray():
            logger.info("✅ Xray restarted successfully")
            send_telegram_message("✅ Xray перезапущен успешно")
        else:
            logger.error("❌ Failed to restart Xray")
            send_telegram_message("❌ Ошибка перезапуска Xray")
    
    if not ports_ok and xray_ok:
        issues.append("Ports")
        logger.warning("Some VPN ports are not open, restarting Xray...")
        send_telegram_message("⚠️ Обнаружены проблемы с VPN портами. Запускаю перезапуск Xray")
        restart_xray()
    
    if not api_ok:
        issues.append("API")
        logger.error("API is not responding, attempting restart...")
        send_telegram_message("⚠️ API не отвечает. Перезапуск службы...")
        if restart_api():
            logger.info("✅ API restarted successfully")
            send_telegram_message("✅ API перезапущен успешно")
        else:
            logger.error("❌ Failed to restart API")
            send_telegram_message("❌ Ошибка перезапуска API")
    
    if xray_ok and ports_ok and api_ok:
        logger.info("✅ All checks passed - system healthy")
        check_cpu_usage(state)
        save_state(state)
        return 0
    else:
        logger.warning(f"⚠️  Issues detected: {', '.join(issues)}")
        send_telegram_message(f"⚠️ Обнаружены проблемы мониторинга: {', '.join(issues)}")
        check_cpu_usage(state)
        save_state(state)
        return 1

if __name__ == '__main__':
    exit(main())

