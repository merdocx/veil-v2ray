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
import sys
from typing import Any, Dict

import psutil

# Добавляем путь к проекту для импорта storage
sys.path.insert(0, '/root/vpn-server')
from storage import sqlite_storage

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
    """Проверка статуса Xray сервиса - проверяет процесс напрямую"""
    try:
        # Проверяем наличие процесса xray
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'xray' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    if 'xray' in cmdline and 'config.json' in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception as e:
        logger.error(f"Error checking Xray: {e}")
        return False

def check_ports():
    """Проверка открытых портов VPN"""
    try:
        result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True, timeout=10)
        
        # Получаем количество активных ключей из SQLite
        try:
            all_keys = sqlite_storage.storage.get_all_keys()
            expected_ports = len([k for k in all_keys if k.get('is_active', True)])
        except Exception as e:
            logger.warning(f"Failed to get keys count from SQLite: {e}, falling back to JSON")
            # Fallback на JSON если SQLite недоступен
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
    """Проверка API - пробует HTTP и HTTPS"""
    try:
        # Сначала пробуем HTTP
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Если HTTP не работает, пробуем HTTPS
        try:
            response = requests.get('https://localhost:8000/health', 
                                  verify=False, timeout=5)
            return response.status_code == 200
        except:
            return False
    except Exception as e:
        logger.error(f"Error checking API: {e}")
        return False

def restart_xray():
    """Перезапуск Xray - сначала через systemctl, если не работает - напрямую"""
    try:
        # Останавливаем все процессы xray
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'xray' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    if 'xray' in cmdline and 'config.json' in cmdline:
                        proc.terminate()
                        proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        
        time.sleep(2)
        
        # Пробуем через systemctl
        try:
            result = subprocess.run(['systemctl', 'restart', 'xray'], 
                                  timeout=10, capture_output=True, text=True)
            time.sleep(3)
            if check_xray():
                logger.info("Xray restarted via systemctl")
                return True
        except:
            pass
        
        # Если systemctl не сработал, запускаем напрямую
        logger.warning("systemctl restart failed, starting Xray directly...")
        subprocess.Popen(
            ['/usr/local/bin/xray', 'run', '-config', '/root/vpn-server/config/config.json'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        time.sleep(3)
        
        if check_xray():
            logger.info("Xray started directly")
            return True
        else:
            logger.error("Xray restart failed")
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
    
    # Загружаем состояние предыдущих проверок
    last_issues = state.get('last_issues', [])
    last_alert_time = state.get('last_alert_time', 0)
    alert_cooldown = 300  # 5 минут между повторными уведомлениями
    
    xray_ok = check_xray()
    ports_ok = check_ports()
    api_ok = check_api()
    
    issues = []
    new_issues = []
    
    if not xray_ok:
        issues.append("Xray")
        if "Xray" not in last_issues:
            new_issues.append("Xray")
            logger.error("Xray is not running, attempting restart...")
            send_telegram_message("⚠️ Xray сервис не активен. Перезапуск...")
        if restart_xray():
            logger.info("✅ Xray restarted successfully")
            if "Xray" in last_issues:
                send_telegram_message("✅ Xray перезапущен успешно")
        else:
            logger.error("❌ Failed to restart Xray")
            if "Xray" in last_issues and time.time() - last_alert_time > alert_cooldown:
                send_telegram_message("❌ Ошибка перезапуска Xray")
                state['last_alert_time'] = time.time()
    
    if not ports_ok and xray_ok:
        issues.append("Ports")
        if "Ports" not in last_issues:
            new_issues.append("Ports")
            logger.warning("Some VPN ports are not open, restarting Xray...")
            send_telegram_message("⚠️ Обнаружены проблемы с VPN портами. Запускаю перезапуск Xray")
        restart_xray()
    
    if not api_ok:
        issues.append("API")
        if "API" not in last_issues:
            new_issues.append("API")
            logger.error("API is not responding, attempting restart...")
            send_telegram_message("⚠️ API не отвечает. Перезапуск службы...")
        if restart_api():
            logger.info("✅ API restarted successfully")
            if "API" in last_issues:
                send_telegram_message("✅ API перезапущен успешно")
        else:
            logger.error("❌ Failed to restart API")
            if "API" in last_issues and time.time() - last_alert_time > alert_cooldown:
                send_telegram_message("❌ Ошибка перезапуска API")
                state['last_alert_time'] = time.time()
    
    # Отправляем общее сообщение только при новых проблемах или если проблемы исчезли
    if new_issues:
        send_telegram_message(f"⚠️ Обнаружены проблемы мониторинга: {', '.join(new_issues)}")
        state['last_alert_time'] = time.time()
    elif not issues and last_issues:
        send_telegram_message("✅ Все проблемы устранены. Система работает нормально.")
    
    state['last_issues'] = issues
    
    if xray_ok and ports_ok and api_ok:
        logger.info("✅ All checks passed - system healthy")
        check_cpu_usage(state)
        save_state(state)
        return 0
    else:
        logger.warning(f"⚠️  Issues detected: {', '.join(issues)}")
        check_cpu_usage(state)
        save_state(state)
        return 1

if __name__ == '__main__':
    exit(main())

