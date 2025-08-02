import json
import uuid
import subprocess
import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="VPN Key Management API", version="1.0.0")

# Пути к файлам
CONFIG_FILE = "/root/vpn-server/config/config.json"
KEYS_FILE = "/root/vpn-server/config/keys.json"

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

# Перезапуск Xray сервиса
def restart_xray():
    try:
        # Используем полный путь к systemctl
        result = subprocess.run(['/usr/bin/systemctl', 'restart', 'xray'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"Xray restarted successfully: {result.stdout}")
            return True
        else:
            print(f"Failed to restart Xray: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("Timeout while restarting Xray")
        return False
    except Exception as e:
        print(f"Error restarting Xray: {e}")
        return False

@app.get("/")
async def root():
    return {"message": "VPN Key Management API", "version": "1.0.0"}

@app.post("/api/keys", response_model=VPNKey)
async def create_key(request: CreateKeyRequest):
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
            "flow": ""
        }
        config["inbounds"][0]["settings"]["clients"].append(client_config)
        save_config(config)
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        return VPNKey(**new_key)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create key: {str(e)}")

@app.delete("/api/keys/{key_id}")
async def delete_key(key_id: str):
    """Удалить VPN ключ"""
    try:
        # Загрузка ключей
        keys = load_keys()
        
        # Поиск ключа
        key_to_delete = None
        for key in keys:
            if key["id"] == key_id:
                key_to_delete = key
                break
        
        if not key_to_delete:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # Удаление ключа из списка
        keys = [k for k in keys if k["id"] != key_id]
        save_keys(keys)
        
        # Обновление конфигурации Xray
        config = load_config()
        config["inbounds"][0]["settings"]["clients"] = [
            client for client in config["inbounds"][0]["settings"]["clients"]
            if client["id"] != key_to_delete["uuid"]
        ]
        save_config(config)
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        return {"message": "Key deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete key: {str(e)}")

@app.get("/api/keys", response_model=List[VPNKey])
async def list_keys():
    """Получить список всех VPN ключей"""
    try:
        keys = load_keys()
        return [VPNKey(**key) for key in keys]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load keys: {str(e)}")

@app.get("/api/keys/{key_id}", response_model=VPNKey)
async def get_key(key_id: str):
    """Получить информацию о конкретном ключе"""
    try:
        keys = load_keys()
        for key in keys:
            if key["id"] == key_id:
                return VPNKey(**key)
        raise HTTPException(status_code=404, detail="Key not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key: {str(e)}")

@app.get("/api/keys/{key_id}/config")
async def get_key_config(key_id: str):
    """Получить конфигурацию клиента для ключа"""
    try:
        keys = load_keys()
        key = None
        for k in keys:
            if k["id"] == key_id:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 