import json
import uuid
import subprocess
import os
import time
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

# Импорт модулей для мониторинга
from alternative_traffic_monitor import get_key_traffic_bytes, get_all_keys_traffic_bytes, reset_key_traffic_stats

app = FastAPI(title="VPN Key Management API", version="1.0.0")

# Пути к файлам
CONFIG_FILE = "/root/vpn-server/config/config.json"
KEYS_FILE = "/root/vpn-server/config/keys.json"

# API ключ для аутентификации
API_KEY = "QBDMqDzCRh17NIGUsKDtWtoUmvwRVvSHHp4W8OCMcOM="

class VPNKey(BaseModel):
    id: str
    name: str
    uuid: str
    created_at: str
    is_active: bool

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
    """Создать новый VPN ключ"""
    try:
        # Генерация UUID для ключа
        key_uuid = str(uuid.uuid4())
        
        # Создание нового ключа
        new_key = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "uuid": key_uuid,
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        # Загрузка существующих ключей
        keys = load_keys()
        keys.append(new_key)
        save_keys(keys)
        
        # Обновление конфигурации Xray
        config = load_config()
        client_config = {
            "id": key_uuid,
            "flow": "",
            "email": key_uuid  # Email для статистики (используем UUID)
        }
        config["inbounds"][0]["settings"]["clients"].append(client_config)
        save_config(config)
        
        # Проверка и обновление настроек Reality
        if not verify_reality_settings():
            raise HTTPException(status_code=500, detail="Failed to verify Reality settings")
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        # Проверка синхронизации конфигурации
        if not verify_xray_config():
            raise HTTPException(status_code=500, detail="Failed to synchronize Xray configuration")
        
        return VPNKey(**new_key)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create key: {str(e)}")

@app.delete("/api/keys/{key_id}")
async def delete_key(key_id: str, api_key: str = Depends(verify_api_key)):
    """Удалить VPN ключ"""
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
        
        # Удаление ключа из списка (по ID)
        keys = [k for k in keys if k["id"] != key_to_delete["id"]]
        save_keys(keys)
        
        # Обновление конфигурации Xray
        config = load_config()
        config["inbounds"][0]["settings"]["clients"] = [
            client for client in config["inbounds"][0]["settings"]["clients"]
            if client["id"] != key_to_delete["uuid"]
        ]
        save_config(config)
        
        # Проверка и обновление настроек Reality
        if not verify_reality_settings():
            raise HTTPException(status_code=500, detail="Failed to verify Reality settings")
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        # Проверка синхронизации конфигурации
        if not verify_xray_config():
            raise HTTPException(status_code=500, detail="Failed to synchronize Xray configuration")
        
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
        
        # Генерация конфигурации клиента
        result = subprocess.run([
            '/root/vpn-server/generate_client_config.py',
            key["uuid"],
            key["name"]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 