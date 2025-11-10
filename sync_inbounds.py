#!/usr/bin/env python3
"""
Пересоздание inbound'ов Xray на основе keys.json с использованием HandlerService.
Запуск: python3 sync_inbounds.py
"""

import json
from pathlib import Path

from xray_config_manager import update_xray_config_for_keys

KEYS_PATH = Path("/root/vpn-server/config/keys.json")


def load_keys():
    if not KEYS_PATH.exists():
        return []
    with KEYS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    keys = load_keys()
    if update_xray_config_for_keys(keys):
        print(f"Synced {len(keys)} keys with Xray via HandlerService.")
    else:
        raise SystemExit("Failed to sync Xray configuration.")


if __name__ == "__main__":
    main()


