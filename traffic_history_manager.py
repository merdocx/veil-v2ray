#!/usr/bin/env python3
"""
Снапшот-менеджер трафика: для каждого ключа храним только накопительный total_bytes.
"""

from datetime import datetime
from typing import Dict, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from xray_stats_reader import get_xray_user_traffic
    XRAY_STATS_AVAILABLE = True
except ImportError:
    XRAY_STATS_AVAILABLE = False
    logger.warning("xray_stats_reader недоступен, используется fallback")


from storage.sqlite_storage import storage


class TrafficHistoryManager:
    SNAPSHOT_VERSION = "2.0"

    @staticmethod
    def _new_entry() -> Dict[str, Any]:
        return {
            "total_bytes": 0,
            "last_update": None,
            "last_snapshot": {
                "total_bytes": 0,
                "timestamp": None,
            },
            "last_xray_stats": {
                "uplink": 0,
                "downlink": 0,
                "timestamp": None,
            },
        }

    def update_key_traffic(
        self,
        key_uuid: str,
        key_name: str,
        port: int,
        current_traffic: Optional[Dict[str, Any]] = None,
    ):
        entry = storage.get_traffic_history_entry(key_uuid) or self._new_entry()

        delta, _ = self._calculate_delta(key_uuid, entry, current_traffic)
        if delta > 0:
            entry["total_bytes"] += delta

        entry["last_update"] = datetime.now().isoformat()
        storage.save_traffic_history_entry(key_uuid, entry)
        logger.info("Обновлён total_bytes %s: +%s", key_uuid, delta)

    def _calculate_delta(
        self,
        key_uuid: str,
        entry: Dict[str, Any],
        current_traffic: Optional[Dict[str, Any]],
    ):
        current_traffic = current_traffic or {}
        connections = int(current_traffic.get("connections", 0) or 0)
        now = datetime.now().isoformat()

        if XRAY_STATS_AVAILABLE:
            try:
                stats = get_xray_user_traffic(key_uuid)
                uplink = int(stats.get("uplink", 0) or 0)
                downlink = int(stats.get("downlink", 0) or 0)
                last_stats = entry.get("last_xray_stats", {})
                last_uplink = int(last_stats.get("uplink", 0) or 0)
                last_downlink = int(last_stats.get("downlink", 0) or 0)

                uplink_delta = (
                    uplink if uplink < last_uplink else max(0, uplink - last_uplink)
                )
                downlink_delta = (
                    downlink
                    if downlink < last_downlink
                    else max(0, downlink - last_downlink)
                )

                entry["last_xray_stats"] = {
                    "uplink": uplink,
                    "downlink": downlink,
                    "timestamp": now,
                }

                delta = uplink_delta + downlink_delta
                if delta > 0:
                    snapshot = entry.setdefault(
                        "last_snapshot", {"total_bytes": 0, "timestamp": None}
                    )
                    snapshot["total_bytes"] = snapshot.get("total_bytes", 0) + delta
                    snapshot["timestamp"] = now
                return delta, connections
            except Exception as exc:
                logger.error(
                    "Не удалось получить Xray stats для %s: %s", key_uuid, exc
                )

        if not current_traffic:
            return 0, connections

        current_total = int(current_traffic.get("total_bytes", 0) or 0)
        snapshot = entry.get("last_snapshot") or {}
        last_total = int(snapshot.get("total_bytes", 0) or 0)
        delta = current_total - last_total
        if delta < 0:
            delta = current_total
        entry["last_snapshot"] = {
            "total_bytes": current_total,
            "timestamp": now,
        }
        return delta, connections

    def get_key_total_traffic(self, key_uuid: str) -> Optional[Dict[str, Any]]:
        entry = storage.get_traffic_history_entry(key_uuid)
        if not entry:
            return None
        return self._format_key_snapshot(key_uuid, entry)

    def get_all_keys_total_traffic(self) -> Dict[str, Any]:
        history = storage.get_all_traffic_history()
        total_bytes = sum(entry.get("total_bytes", 0) for entry in history.values())

        keys = [
            self._format_key_snapshot(uuid, entry) for uuid, entry in history.items()
        ]

        return {
            "total_keys": len(keys),
            "total_traffic_bytes": total_bytes,
            "last_update": datetime.now().isoformat(),
            "keys": keys,
        }

    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return {
            "date": date,
            "total_bytes": 0,
            "history_tracking": False,
        }

    def get_monthly_stats(self, year_month: Optional[str] = None) -> Dict[str, Any]:
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")

        summary = self.get_all_keys_total_traffic()
        summary.update(
            {
                "year_month": year_month,
                "history_tracking": False,
            }
        )
        return summary

    def get_key_monthly_traffic(
        self, key_uuid: str, year_month: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        history = storage.get_all_traffic_history()
        entry = history.get(key_uuid)
        if not entry:
            return None

        snapshot = self._format_key_snapshot(key_uuid, entry)
        snapshot.update(
            {
                "year_month": year_month or datetime.now().strftime("%Y-%m"),
                "history_tracking": False,
                "daily_breakdown": {},
            }
        )
        return snapshot

    def reset_key_traffic(self, key_uuid: str) -> bool:
        success = storage.reset_traffic_history_entry(key_uuid)
        if success:
            logger.info("Сброшен total_bytes для %s", key_uuid)
        return success

    def cleanup_old_data(self, days_to_keep: int = 30):
        logger.info(
            "Очистка snapshot не требуется (храним только накопительные значения)."
        )

    def _format_key_snapshot(self, key_uuid: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "key_uuid": key_uuid,
            "total_traffic": {
                "total_bytes": entry.get("total_bytes", 0),
            },
        }


traffic_history = TrafficHistoryManager()