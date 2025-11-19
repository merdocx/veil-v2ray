#!/usr/bin/env python3
"""
Проверка доступности SNI-доменов.
Выполняет curl -I запросы к каждому домену, логирует результаты
и отправляет уведомление в Telegram, если найдены недоступные SNI.
"""

import json
import logging
import os
import subprocess
import time
from typing import List, Dict, Any

import requests

PROJECT_ROOT = "/root/vpn-server"
LOG_FILE = f"{PROJECT_ROOT}/logs/sni_check.log"
SNI_CONFIG_FILE = f"{PROJECT_ROOT}/config/sni_list.json"
ENV_PATH = f"{PROJECT_ROOT}/.env"


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

DEFAULT_SNI = [
    "www.microsoft.com",
    "www.cloudflare.com",
    "www.google.com",
    "www.github.com",
    "www.apple.com",
    "www.amazon.com",
    "static.reddit.com",
    "speedtest.net",
    "www.adobe.com",
    "global.shopify.com",
]


os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
            logger.error("Telegram error: %s", response.text[:200])
    except Exception as exc:
        logger.error("Telegram notification failed: %s", exc)


def load_sni_list() -> List[str]:
    if os.path.exists(SNI_CONFIG_FILE):
        try:
            with open(SNI_CONFIG_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list) and data:
                    return data
        except Exception as exc:
            logger.error("Failed to load custom SNI list: %s", exc)
    return DEFAULT_SNI


def check_domain(domain: str) -> Dict[str, Any]:
    cmd = [
        "curl",
        "-I",
        f"https://{domain}",
        "--max-time",
        "5",
        "-o",
        "/dev/null",
        "-s",
        "-w",
        "%{http_code}",
    ]
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=False
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        http_code = result.stdout.strip() or "N/A"
        success = (
            result.returncode == 0 and http_code and http_code[0] in ("2", "3")
        )
        return {
            "domain": domain,
            "ok": success,
            "code": http_code,
            "latency_ms": elapsed_ms,
            "error": result.stderr.strip(),
        }
    except Exception as exc:
        return {
            "domain": domain,
            "ok": False,
            "code": "ERR",
            "latency_ms": 0,
            "error": str(exc),
        }


def format_report(results: List[Dict[str, Any]]) -> str:
    lines = []
    for item in results:
        status = "OK" if item["ok"] else "FAIL"
        lines.append(
            f"{item['domain']:<22} {status:<4} code={item['code']} "
            f"latency={item['latency_ms']}ms"
        )
    return "\n".join(lines)


def main():
    logger.info("Starting SNI check")
    domains = load_sni_list()
    results = [check_domain(domain) for domain in domains]

    report = format_report(results)
    logger.info("\n%s", report)

    failed = [item for item in results if not item["ok"]]
    if failed:
        summary_lines = [
            f"- {item['domain']}: code={item['code']} err={item['error'] or 'n/a'}"
            for item in failed
        ]
        send_telegram_message(
            "⚠️ SNI проверка: недоступны домены:\n" + "\n".join(summary_lines)
        )
    else:
        logger.info("All SNI domains responded successfully")


if __name__ == "__main__":
    main()


