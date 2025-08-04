import json
import uuid
import subprocess
import os
import time
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

# Загрузка переменных окружения из .env файла
def load_env_file():
    env_file = "/root/vpn-server/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Загружаем переменные окружения
load_env_file()

# Импорт модулей для мониторинга
from alternative_traffic_monitor import get_key_traffic_bytes, get_all_keys_traffic_bytes, reset_key_traffic_stats

# Импорт новой системы мониторинга
from port_manager import port_manager, assign_port_for_key, release_port_for_key, get_port_for_key, get_all_port_assignments, reset_all_ports
from xray_config_manager import xray_config_manager, add_key_to_xray_config, remove_key_from_xray_config, update_xray_config_for_keys, get_xray_config_status, validate_xray_config_sync
from port_traffic_monitor import port_traffic_monitor, get_uuid_traffic_bytes, get_all_ports_traffic_bytes, reset_uuid_traffic_stats, get_system_traffic_summary

app = FastAPI(title="VPN Key Management API", version="1.0.0")

# Пути к файлам
CONFIG_FILE = "/root/vpn-server/config/config.json"
KEYS_FILE = "/root/vpn-server/config/keys.json"

# API ключ для аутентификации - загружается из переменных окружения
API_KEY = os.getenv("VPN_API_KEY", "QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM=")

class VPNKey(BaseModel):
    id: str
    name: str
    uuid: str
    created_at: str
    is_active: bool
    port: Optional[int] = None

class CreateKeyRequest(BaseModel):
    name: str

class DeleteKeyRequest(BaseModel):
    key_id: str

# Функция для проверки API ключа
async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Use X-API-Key header with the correct key."
        )
    return x_api_key

# Инициализация файла ключей если не существует
def init_keys_file():
    if not os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'w') as f:
            json.dump([], f)

# Загрузка конфигурации Xray
def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# Сохранение конфигурации Xray
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Загрузка ключей
def load_keys():
    init_keys_file()
    with open(KEYS_FILE, 'r') as f:
        return json.load(f)

# Сохранение ключей
def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

# Перезапуск Xray сервиса с проверкой
def restart_xray():
    try:
        # Используем полный путь к systemctl
        result = subprocess.run(['/usr/bin/systemctl', 'restart', 'xray'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"Xray restart command executed: {result.stdout}")
            
            # Ждем немного для стабилизации
            import time
            time.sleep(2)
            
            # Проверяем статус сервиса
            status_result = subprocess.run(['/usr/bin/systemctl', 'is-active', 'xray'], 
                                         capture_output=True, text=True, timeout=10)
            if status_result.returncode == 0 and status_result.stdout.strip() == 'active':
                print("Xray service is active and running")
                return True
            else:
                print(f"Xray service is not active: {status_result.stdout} {status_result.stderr}")
                return False
        else:
            print(f"Failed to restart Xray: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("Timeout while restarting Xray")
        return False
    except Exception as e:
        print(f"Error restarting Xray: {e}")
        return False

# Проверка конфигурации Xray
def verify_xray_config():
    try:
        # Проверяем, что конфигурация синхронизирована с keys.json
        keys = load_keys()
        config = load_config()
        
        # Получаем UUID из keys.json
        key_uuids = {key["uuid"] for key in keys}
        
        # Получаем UUID из config.json
        config_uuids = {client["id"] for client in config["inbounds"][0]["settings"]["clients"]}
        
        # Проверяем соответствие
        if key_uuids == config_uuids:
            print("Xray configuration is synchronized with keys.json")
            return True
        else:
            print(f"Configuration mismatch: keys.json has {key_uuids}, config.json has {config_uuids}")
            return False
    except Exception as e:
        print(f"Error verifying Xray config: {e}")
        return False

# Принудительная синхронизация конфигурации Xray
def force_sync_xray_config():
    try:
        keys = load_keys()
        config = load_config()
        
        # Обновляем конфигурацию на основе keys.json
        config["inbounds"][0]["settings"]["clients"] = []
        for key in keys:
            client_config = {
                "id": key["uuid"],
                "flow": "",
                "email": key["uuid"]
            }
            config["inbounds"][0]["settings"]["clients"].append(client_config)
        
        save_config(config)
        print("Xray configuration force-synchronized with keys.json")
        return True
    except Exception as e:
        print(f"Error force-syncing Xray config: {e}")
        return False

# Проверка и обновление настроек Reality
def verify_reality_settings():
    try:
        config = load_config()
        reality_settings = config["inbounds"][0]["streamSettings"]["realitySettings"]
        
        # Проверяем maxTimeDiff
        if reality_settings.get("maxTimeDiff", 0) == 0:
            reality_settings["maxTimeDiff"] = 600
            print("Updated maxTimeDiff to 600 seconds")
        
        # Проверяем наличие всех необходимых полей
        required_fields = ["dest", "serverNames", "privateKey", "shortIds"]
        for field in required_fields:
            if field not in reality_settings:
                print(f"Missing required Reality field: {field}")
                return False
        
        save_config(config)
        print("Reality settings verified and updated")
        return True
    except Exception as e:
        print(f"Error verifying Reality settings: {e}")
        return False

@app.get("/")
async def root():
    return {"message": "VPN Key Management API", "version": "1.0.0", "status": "running"}

@app.get("/api/")
async def api_root():
    return {"message": "VPN Key Management API", "version": "1.0.0", "status": "running"}

@app.post("/api/keys", response_model=VPNKey)
async def create_key(request: CreateKeyRequest, api_key: str = Depends(verify_api_key)):
    """Создать новый VPN ключ с индивидуальным портом"""
    try:
        # Проверяем лимит ключей (максимум 20)
        keys = load_keys()
        if len(keys) >= 20:
            raise HTTPException(status_code=400, detail="Maximum number of keys (20) reached")
        
        # Генерация UUID для ключа
        key_uuid = str(uuid.uuid4())
        
        # Назначаем порт для ключа
        assigned_port = assign_port_for_key(key_uuid, str(uuid.uuid4()), request.name)
        if not assigned_port:
            raise HTTPException(status_code=500, detail="No available ports")
        
        # Создание нового ключа
        new_key = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "uuid": key_uuid,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "port": assigned_port
        }
        
        # Загрузка существующих ключей
        keys.append(new_key)
        save_keys(keys)
        
        # Добавляем ключ в конфигурацию Xray с индивидуальным портом
        if not add_key_to_xray_config(key_uuid, request.name):
            # Откатываем изменения при ошибке
            keys = [k for k in keys if k["uuid"] != key_uuid]
            save_keys(keys)
            release_port_for_key(key_uuid)
            raise HTTPException(status_code=500, detail="Failed to add key to Xray config")
        
        # Перезапуск Xray
        if not restart_xray():
            # Откатываем изменения при ошибке
            keys = [k for k in keys if k["uuid"] != key_uuid]
            save_keys(keys)
            release_port_for_key(key_uuid)
            remove_key_from_xray_config(key_uuid)
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        return VPNKey(**new_key)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create key: {str(e)}")

@app.delete("/api/keys/{key_id}")
async def delete_key(key_id: str, api_key: str = Depends(verify_api_key)):
    """Удалить VPN ключ с освобождением порта"""
    try:
        # Загрузка ключей
        keys = load_keys()
        
        # Поиск ключа (по ID или UUID)
        key_to_delete = None
        for key in keys:
            if key["id"] == key_id or key["uuid"] == key_id:
                key_to_delete = key
                break
        
        if not key_to_delete:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # Удаление ключа из конфигурации Xray
        if not remove_key_from_xray_config(key_to_delete["uuid"]):
            raise HTTPException(status_code=500, detail="Failed to remove key from Xray config")
        
        # Освобождение порта
        if not release_port_for_key(key_to_delete["uuid"]):
            print(f"Warning: Failed to release port for UUID: {key_to_delete['uuid']}")
        
        # Удаление ключа из списка
        keys = [k for k in keys if k["id"] != key_to_delete["id"]]
        save_keys(keys)
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        return {"message": "Key deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete key: {str(e)}")

@app.get("/api/keys", response_model=List[VPNKey])
async def list_keys(api_key: str = Depends(verify_api_key)):
    """Получить список всех VPN ключей"""
    try:
        keys = load_keys()
        
        # Добавляем информацию о портах для каждого ключа
        for key in keys:
            if "port" not in key:
                port = get_port_for_key(key["uuid"])
                key["port"] = port
        
        return [VPNKey(**key) for key in keys]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load keys: {str(e)}")

@app.get("/api/keys/{key_id}", response_model=VPNKey)
async def get_key(key_id: str, api_key: str = Depends(verify_api_key)):
    """Получить информацию о конкретном ключе"""
    try:
        keys = load_keys()
        for key in keys:
            if key["id"] == key_id or key["uuid"] == key_id:
                return VPNKey(**key)
        raise HTTPException(status_code=404, detail="Key not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key: {str(e)}")

@app.get("/api/keys/{key_id}/config")
async def get_key_config(key_id: str, api_key: str = Depends(verify_api_key)):
    """Получить конфигурацию клиента для ключа"""
    try:
        keys = load_keys()
        key = None
        for k in keys:
            if k["id"] == key_id or k["uuid"] == key_id:
                key = k
                break
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # Получение порта для ключа
        port = get_port_for_key(key["uuid"])
        
        # Генерация конфигурации клиента
        result = subprocess.run([
            '/root/vpn-server/generate_client_config.py',
            key["uuid"],
            key["name"],
            str(port) if port else "443"
        ], capture_output=True, text=True, check=True)
        
        return {
            "key": VPNKey(**key),
            "client_config": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate client config: {e.stderr}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key config: {str(e)}")



# ===== ЭНДПОИНТЫ ТОЧНОГО ПОДСЧЕТА ТРАФИКА ЧЕРЕЗ XRAY API =====

@app.get("/api/traffic/exact")
async def get_exact_traffic(api_key: str = Depends(verify_api_key)):
    """Получить точную статистику трафика через Xray API"""
    try:
        keys = load_keys()
        active_keys = [k for k in keys if k["is_active"]]
        
        # Новая система мониторинга всегда доступна
        
        # Получаем точную статистику всех ключей
        all_stats = get_all_keys_traffic_bytes()
        
        if "error" in all_stats:
            raise HTTPException(status_code=500, detail=all_stats["error"])
        
        # Добавляем информацию о ключах
        result = {
            "total_keys": len(keys),
            "active_keys": len(active_keys),
            "traffic_stats": all_stats,
            "source": "xray_api"
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exact traffic: {str(e)}")

@app.get("/api/keys/{key_id}/traffic/exact")
async def get_key_exact_traffic(key_id: str, api_key: str = Depends(verify_api_key)):
    """Получить точную статистику трафика для конкретного ключа через Xray API"""
    try:
        keys = load_keys()
        key = None
        for k in keys:
            if k["id"] == key_id or k["uuid"] == key_id:
                key = k
                break
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        if not key["is_active"]:
            raise HTTPException(status_code=400, detail="Key is not active")
        
        # Новая система мониторинга всегда доступна
        
        # Получаем точную статистику трафика
        traffic_bytes = get_key_traffic_bytes(key["uuid"])
        
        return {
            "key": VPNKey(**key),
            "traffic_bytes": traffic_bytes,
            "source": "precise_monitor"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key exact traffic: {str(e)}")

@app.post("/api/keys/{key_id}/traffic/reset")
async def reset_key_traffic_stats(key_id: str, api_key: str = Depends(verify_api_key)):
    """Сбросить статистику трафика для ключа через Xray API"""
    try:
        keys = load_keys()
        key = None
        for k in keys:
            if k["id"] == key_id or k["uuid"] == key_id:
                key = k
                break
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        if not key["is_active"]:
            raise HTTPException(status_code=400, detail="Key is not active")
        
        # Сброс статистики через новую систему
        success = reset_key_traffic_stats(key["uuid"])
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset traffic stats")
        
        return {
            "message": "Traffic stats reset successfully",
            "key_id": key_id,
            "uuid": key["uuid"],
            "source": "precise_monitor"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset traffic: {str(e)}")

@app.get("/api/traffic/status")
async def get_traffic_status(api_key: str = Depends(verify_api_key)):
    """Получить статус системы мониторинга трафика"""
    try:
        keys = load_keys()
        active_keys = [k for k in keys if k["is_active"]]
        
        result = {
            "total_keys": len(keys),
            "active_keys": len(active_keys),
            "precise_monitor_available": True,
            "traffic_stats": []
        }
        
        for key in active_keys:
            # Точный расчет через новую систему
            exact = get_key_traffic_bytes(key["uuid"])
            
            key_status = {
                "key_id": key["id"],
                "key_name": key["name"],
                "uuid": key["uuid"],
                "exact_traffic": exact,
                "has_traffic_data": exact is not None and "error" not in exact
            }
            
            result["traffic_stats"].append(key_status)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traffic status: {str(e)}")

@app.post("/api/system/sync-config")
async def sync_xray_config(api_key: str = Depends(verify_api_key)):
    """Принудительная синхронизация конфигурации Xray с keys.json"""
    try:
        # Принудительная синхронизация
        if not force_sync_xray_config():
            raise HTTPException(status_code=500, detail="Failed to sync configuration")
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        # Проверка синхронизации
        if not verify_xray_config():
            raise HTTPException(status_code=500, detail="Configuration sync verification failed")
        
        return {
            "message": "Configuration synchronized successfully",
            "status": "synced",
            "timestamp": int(time.time())
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync configuration: {str(e)}")

@app.get("/api/system/config-status")
async def get_config_status(api_key: str = Depends(verify_api_key)):
    """Получить статус синхронизации конфигурации"""
    try:
        keys = load_keys()
        config = load_config()
        
        # Получаем UUID из keys.json
        key_uuids = {key["uuid"] for key in keys}
        
        # Получаем UUID из config.json
        config_uuids = {client["id"] for client in config["inbounds"][0]["settings"]["clients"]}
        
        is_synced = key_uuids == config_uuids
        
        return {
            "synchronized": is_synced,
            "keys_json_count": len(key_uuids),
            "config_json_count": len(config_uuids),
            "keys_json_uuids": list(key_uuids),
            "config_json_uuids": list(config_uuids),
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config status: {str(e)}")

@app.post("/api/system/verify-reality")
async def verify_reality_endpoint(api_key: str = Depends(verify_api_key)):
    """Проверить и обновить настройки Reality"""
    try:
        if verify_reality_settings():
            return {
                "message": "Reality settings verified and updated successfully",
                "status": "verified",
                "timestamp": int(time.time())
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to verify Reality settings")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify Reality settings: {str(e)}")

# ===== НОВЫЕ ЭНДПОИНТЫ ДЛЯ СИСТЕМЫ ПОРТОВ =====

@app.get("/api/system/ports")
async def get_ports_status(api_key: str = Depends(verify_api_key)):
    """Получить статус портов"""
    try:
        port_assignments = get_all_port_assignments()
        used_count = port_manager.get_used_ports_count()
        available_count = port_manager.get_available_ports_count()
        
        return {
            "port_assignments": port_assignments,
            "used_ports": used_count,
            "available_ports": available_count,
            "max_ports": 20,
            "port_range": "10001-10020",
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ports status: {str(e)}")

@app.post("/api/system/ports/reset")
async def reset_ports(api_key: str = Depends(verify_api_key)):
    """Сбросить все порты"""
    try:
        if reset_all_ports():
            return {
                "message": "All ports reset successfully",
                "status": "reset",
                "timestamp": int(time.time())
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reset ports")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset ports: {str(e)}")

@app.get("/api/system/ports/status")
async def get_ports_validation_status(api_key: str = Depends(verify_api_key)):
    """Получить статус валидации портов"""
    try:
        validation = port_manager.validate_port_assignments()
        return {
            "validation": validation,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ports validation status: {str(e)}")

# ===== ЭНДПОИНТЫ ТОЧНОГО МОНИТОРИНГА ТРАФИКА =====

@app.get("/api/traffic/ports/exact")
async def get_exact_ports_traffic(api_key: str = Depends(verify_api_key)):
    """Получить точную статистику трафика по портам"""
    try:
        ports_traffic = get_all_ports_traffic_bytes()
        system_summary = get_system_traffic_summary()
        
        return {
            "ports_traffic": ports_traffic,
            "system_summary": system_summary,
            "source": "port_monitor",
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exact ports traffic: {str(e)}")

@app.get("/api/keys/{key_id}/traffic/port/exact")
async def get_key_port_exact_traffic(key_id: str, api_key: str = Depends(verify_api_key)):
    """Получить точную статистику трафика для ключа по порту"""
    try:
        keys = load_keys()
        key = None
        for k in keys:
            if k["id"] == key_id or k["uuid"] == key_id:
                key = k
                break
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        if not key["is_active"]:
            raise HTTPException(status_code=400, detail="Key is not active")
        
        # Получаем точную статистику трафика по порту
        port_traffic = get_uuid_traffic_bytes(key["uuid"])
        
        return {
            "key": VPNKey(**key),
            "port_traffic": port_traffic,
            "source": "port_monitor",
            "timestamp": int(time.time())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key port exact traffic: {str(e)}")

@app.post("/api/keys/{key_id}/traffic/port/reset")
async def reset_key_port_traffic_stats(key_id: str, api_key: str = Depends(verify_api_key)):
    """Сбросить статистику трафика для ключа по порту"""
    try:
        keys = load_keys()
        key = None
        for k in keys:
            if k["id"] == key_id or k["uuid"] == key_id:
                key = k
                break
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        if not key["is_active"]:
            raise HTTPException(status_code=400, detail="Key is not active")
        
        # Сброс статистики трафика по порту
        success = reset_uuid_traffic_stats(key["uuid"])
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset port traffic stats")
        
        return {
            "message": "Port traffic stats reset successfully",
            "key_id": key_id,
            "uuid": key["uuid"],
            "port": key.get("port"),
            "source": "port_monitor",
            "timestamp": int(time.time())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset port traffic: {str(e)}")

@app.get("/api/system/traffic/summary")
async def get_system_traffic_summary_endpoint(api_key: str = Depends(verify_api_key)):
    """Получить сводку системного трафика"""
    try:
        summary = get_system_traffic_summary()
        return {
            "summary": summary,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system traffic summary: {str(e)}")

# ===== ЭНДПОИНТЫ КОНФИГУРАЦИИ XRAY =====

@app.get("/api/system/xray/config-status")
async def get_xray_config_status_endpoint(api_key: str = Depends(verify_api_key)):
    """Получить статус конфигурации Xray"""
    try:
        status = get_xray_config_status()
        return {
            "config_status": status,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Xray config status: {str(e)}")

@app.post("/api/system/xray/sync-config")
async def sync_xray_config_endpoint(api_key: str = Depends(verify_api_key)):
    """Синхронизировать конфигурацию Xray с ключами"""
    try:
        keys = load_keys()
        if update_xray_config_for_keys(keys):
            # Перезапуск Xray
            if not restart_xray():
                raise HTTPException(status_code=500, detail="Failed to restart Xray service")
            
            return {
                "message": "Xray configuration synchronized successfully",
                "status": "synced",
                "timestamp": int(time.time())
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to sync Xray configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync Xray configuration: {str(e)}")

@app.get("/api/system/xray/validate-sync")
async def validate_xray_config_sync_endpoint(api_key: str = Depends(verify_api_key)):
    """Валидировать синхронизацию конфигурации Xray"""
    try:
        keys = load_keys()
        validation = validate_xray_config_sync(keys)
        return {
            "validation": validation,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate Xray config sync: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Настройки из переменных окружения
    host = os.getenv("VPN_HOST", "0.0.0.0")
    port = int(os.getenv("VPN_PORT", "8000"))
    enable_https = os.getenv("VPN_ENABLE_HTTPS", "false").lower() == "true"
    ssl_cert = os.getenv("VPN_SSL_CERT_PATH", "/etc/ssl/certs/vpn-api.crt")
    ssl_key = os.getenv("VPN_SSL_KEY_PATH", "/etc/ssl/private/vpn-api.key")
    
    if enable_https and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f"🚀 Starting VPN API with HTTPS on {host}:{port}")
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key
        )
    else:
        print(f"🚀 Starting VPN API with HTTP on {host}:{port}")
        uvicorn.run(app, host=host, port=port) 