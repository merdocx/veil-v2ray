#!/usr/bin/env python3
"""
Centralized SQLite storage for VPN server state (keys, ports, metadata).
SQLite is the single source of truth - all data operations use SQLite directly.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = "/root/vpn-server"
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "vpn.db")

KEYS_JSON_PATH = os.path.join(PROJECT_ROOT, "config", "keys.json")
PORTS_JSON_PATH = os.path.join(PROJECT_ROOT, "config", "ports.json")
TRAFFIC_HISTORY_JSON_PATH = os.path.join(PROJECT_ROOT, "config", "traffic_history.json")


def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _write_json_atomic(path: str, data: Any):
    _ensure_parent(path)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


class SQLiteStorage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        _ensure_parent(self.db_path)
        self._init_db()
        self._migrate_from_json()
        # JSON экспорт отключен - используем только SQLite

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS keys (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    uuid TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    port INTEGER,
                    short_id TEXT,
                    sni TEXT
                )
                """
            )
            # Добавляем колонку sni если её нет (для существующих БД)
            try:
                conn.execute("ALTER TABLE keys ADD COLUMN sni TEXT")
            except sqlite3.OperationalError:
                pass  # Колонка уже существует
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS port_assignments (
                    port INTEGER PRIMARY KEY,
                    uuid TEXT NOT NULL UNIQUE,
                    key_id TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traffic_history (
                    key_uuid TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_update TEXT NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    # JSON migration helpers
    # ------------------------------------------------------------------
    def _migrate_from_json(self):
        self._migrate_keys_json()
        self._migrate_ports_json()
        self._migrate_history_json()

    def _migrate_keys_json(self):
        if not os.path.exists(KEYS_JSON_PATH):
            return
        if self.count_keys() > 0:
            return
        try:
            with open(KEYS_JSON_PATH, "r", encoding="utf-8") as fh:
                keys = json.load(fh) or []
        except (json.JSONDecodeError, FileNotFoundError):
            return

        for key in keys:
            if not isinstance(key, dict):
                continue
            key.setdefault("id", key.get("uuid") or "")
            key.setdefault("created_at", datetime.now().isoformat())
            self.add_key(key, sync_json=False)

    def _migrate_ports_json(self):
        if not os.path.exists(PORTS_JSON_PATH):
            return
        if self.get_used_ports_count() > 0:
            return
        try:
            with open(PORTS_JSON_PATH, "r", encoding="utf-8") as fh:
                ports_data = json.load(fh) or {}
        except (json.JSONDecodeError, FileNotFoundError):
            return

        assignments = ports_data.get("port_assignments", {})
        for uuid, info in assignments.items():
            try:
                port = int(info.get("port"))
            except (TypeError, ValueError):
                continue
            key_id = info.get("key_id") or info.get("keyId") or uuid
            key_name = info.get("key_name") or info.get("keyName") or uuid
            assigned_at = info.get("assigned_at") or datetime.now().isoformat()
            self.add_port_assignment(
                uuid=uuid,
                key_id=key_id,
                key_name=key_name,
                port=port,
                assigned_at=assigned_at,
                sync_json=False,
            )

    def _migrate_history_json(self):
        if not os.path.exists(TRAFFIC_HISTORY_JSON_PATH):
            return
        if self.count_traffic_history_entries() > 0:
            return
        try:
            with open(TRAFFIC_HISTORY_JSON_PATH, "r", encoding="utf-8") as fh:
                history_data = json.load(fh) or {}
        except (json.JSONDecodeError, FileNotFoundError):
            return

        keys_history = history_data.get("keys_history", {})
        for uuid, entry in keys_history.items():
            if not isinstance(entry, dict):
                continue
            self.save_traffic_history_entry(uuid, entry, sync_json=False)

    # ------------------------------------------------------------------
    # Key operations
    # ------------------------------------------------------------------
    def count_keys(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM keys").fetchone()
            return int(row["c"])

    def get_all_keys(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM keys ORDER BY datetime(created_at) ASC, name ASC"
            ).fetchall()
        return [self._format_key(row) for row in rows]

    def get_key_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM keys WHERE id = ? OR uuid = ?",
                (identifier, identifier),
            ).fetchone()
        return self._format_key(row) if row else None

    def add_key(self, key: Dict[str, Any], sync_json: bool = False):
        # Сохраняем индивидуальный short_id и sni для каждого ключа
        record = (
            key["id"],
            key["name"],
            key["uuid"],
            key.get("created_at", datetime.now().isoformat()),
            1 if key.get("is_active", True) else 0,
            key.get("port"),
            key.get("short_id"),  # Индивидуальный short_id для каждого ключа
            key.get("sni"),  # SNI для каждого ключа (выбирается случайно при создании)
        )
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO keys (id, name, uuid, created_at, is_active, port, short_id, sni)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    record,
                )
            # JSON экспорт отключен - используем только SQLite

    def delete_key_by_uuid(self, uuid: str):
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM keys WHERE uuid = ?", (uuid,))
            # JSON экспорт отключен - используем только SQLite

    def update_key_fields(self, uuid: str, **fields):
        if not fields:
            return
        columns = []
        values: List[Any] = []
        for key, value in fields.items():
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(uuid)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE keys SET {', '.join(columns)} WHERE uuid = ?", values
                )
            # JSON экспорт отключен - используем только SQLite

    def export_keys_json(self):
        keys = self.get_all_keys()
        _write_json_atomic(KEYS_JSON_PATH, keys)

    # ------------------------------------------------------------------
    # Port operations
    # ------------------------------------------------------------------
    def get_used_ports(self) -> Dict[int, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM port_assignments ORDER BY port ASC"
            ).fetchall()
        result = {}
        for row in rows:
            result[int(row["port"])] = {
                "uuid": row["uuid"],
                "key_id": row["key_id"],
                "key_name": row["key_name"],
                "assigned_at": row["assigned_at"],
                "is_active": bool(row["is_active"]),
            }
        return result

    def get_used_ports_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM port_assignments").fetchone()
            return int(row["c"])

    def get_port_for_uuid(self, uuid: str) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT port FROM port_assignments WHERE uuid = ?", (uuid,)
            ).fetchone()
        return int(row["port"]) if row else None

    def add_port_assignment(
        self,
        uuid: str,
        key_id: str,
        key_name: str,
        port: int,
        assigned_at: Optional[str] = None,
        sync_json: bool = False,
    ):
        assigned_at = assigned_at or datetime.now().isoformat()
        record = (port, uuid, key_id, key_name, assigned_at, 1)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO port_assignments
                    (port, uuid, key_id, key_name, assigned_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    record,
                )
            if sync_json:
                self.export_ports_json()

    def release_port_assignment(self, uuid: str, sync_json: bool = False) -> bool:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM port_assignments WHERE uuid = ?", (uuid,)
                )
            if cursor.rowcount and sync_json:
                self.export_ports_json()
            return cursor.rowcount > 0

    def reset_ports(self, sync_json: bool = False) -> bool:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM port_assignments")
            if sync_json:
                self.export_ports_json()
        return True

    def get_ports_snapshot(self) -> Dict[str, Any]:
        used_ports = self.get_used_ports()
        used_ports_payload = {
            str(port): {
                **info,
                "is_active": bool(info.get("is_active", True)),
            }
            for port, info in used_ports.items()
        }
        port_assignments = {}
        for port, info in used_ports.items():
            port_assignments[info["uuid"]] = {
                "port": port,
                "key_id": info["key_id"],
                "key_name": info["key_name"],
                "assigned_at": info["assigned_at"],
            }
        now = datetime.now().isoformat()
        return {
            "used_ports": used_ports_payload,
            "port_assignments": port_assignments,
            "created_at": now,
            "last_updated": now,
        }

    def export_ports_json(self):
        snapshot = self.get_ports_snapshot()
        _write_json_atomic(PORTS_JSON_PATH, snapshot)

    # ------------------------------------------------------------------
    # Traffic history operations
    # ------------------------------------------------------------------
    def count_traffic_history_entries(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM traffic_history").fetchone()
            return int(row["c"])

    def get_traffic_history_entry(self, key_uuid: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM traffic_history WHERE key_uuid = ?",
                (key_uuid,),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["payload"])
        except json.JSONDecodeError:
            return None

    def get_all_traffic_history(self) -> Dict[str, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key_uuid, payload FROM traffic_history").fetchall()
        result = {}
        for row in rows:
            try:
                result[row["key_uuid"]] = json.loads(row["payload"])
            except json.JSONDecodeError:
                continue
        return result

    def save_traffic_history_entry(
        self,
        key_uuid: str,
        entry: Dict[str, Any],
        sync_json: bool = False,
    ):
        now = datetime.now().isoformat()
        payload = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO traffic_history (key_uuid, payload, created_at, last_update)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key_uuid) DO UPDATE SET
                        payload=excluded.payload,
                        last_update=excluded.last_update
                    """,
                    (key_uuid, payload, entry.get("last_update", now) or now, now),
                )
            if sync_json:
                self.export_traffic_history_json()

    def reset_traffic_history_entry(self, key_uuid: str, sync_json: bool = False) -> bool:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM traffic_history WHERE key_uuid = ?",
                    (key_uuid,),
                )
            if cursor.rowcount and sync_json:
                self.export_traffic_history_json()
            return cursor.rowcount > 0

    def export_traffic_history_json(self):
        history = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "keys_history": self.get_all_traffic_history(),
            "last_update": datetime.now().isoformat(),
        }
        _write_json_atomic(TRAFFIC_HISTORY_JSON_PATH, history)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _format_key(row: sqlite3.Row) -> Dict[str, Any]:
        # Проверяем наличие поля sni (может отсутствовать в старых БД)
        sni = None
        try:
            if "sni" in row.keys():
                sni = row["sni"]
        except (KeyError, IndexError):
            pass
        
        return {
            "id": row["id"],
            "name": row["name"],
            "uuid": row["uuid"],
            "created_at": row["created_at"],
            "is_active": bool(row["is_active"]),
            "port": row["port"],
            "short_id": row["short_id"],
            "sni": sni,  # SNI может быть None для старых ключей
        }


storage = SQLiteStorage()

