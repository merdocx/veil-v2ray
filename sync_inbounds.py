#!/usr/bin/env python3
"""
Пересоздание inbound'ов Xray на основе SQLite с использованием HandlerService.
Запуск: python3 sync_inbounds.py
"""

import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xray_config_manager import update_xray_config_for_keys
from storage.sqlite_storage import storage


def main():
    keys = storage.get_all_keys()
    if update_xray_config_for_keys(keys):
        print(f"Synced {len(keys)} keys with Xray via HandlerService.")
    else:
        raise SystemExit("Failed to sync Xray configuration.")


if __name__ == "__main__":
    main()











