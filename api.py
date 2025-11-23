import json
import uuid
import subprocess
import os
import time
import logging
import secrets
import random
from datetime import datetime
from typing import List, Optional, Dict
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from starlette.requests import Request
from pydantic import BaseModel
import psutil
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/vpn-server/logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
from port_manager import port_manager, assign_port_for_key, release_port_for_key, get_port_for_key, get_all_port_assignments, reset_all_ports
from xray_config_manager import xray_config_manager, add_key_to_xray_config, remove_key_from_xray_config, update_xray_config_for_keys, get_xray_config_status, validate_xray_config_sync, fix_reality_keys_in_xray_config, sync_short_ids_from_db
from traffic_history_manager import traffic_history
from storage.sqlite_storage import storage
try:
    from xray_stats_reader import get_xray_user_traffic, get_all_xray_users_traffic
    XRAY_STATS_AVAILABLE = True
except ImportError:
    XRAY_STATS_AVAILABLE = False
    logging.warning("xray_stats_reader недоступен, используется fallback")

app = FastAPI(title="VPN Key Management API", version="2.3.6")

# Настройка rate limiting с расширенными правилами
# Белый список IP для исключения из rate limiting (бот)
BOT_WHITELIST_IPS = ["77.246.105.29"]

def get_rate_limit_key(request: Request):
    """Получить ключ для rate limiting, исключая IP бота"""
    # Проверяем X-Forwarded-For (если запрос идет через nginx)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Берем первый IP из списка (реальный IP клиента)
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip in BOT_WHITELIST_IPS:
            return None  # Отключаем rate limiting для бота
    # Иначе используем стандартный метод
    client_ip = get_remote_address(request)
    if client_ip in BOT_WHITELIST_IPS:
        return None  # Отключаем rate limiting для бота
    return client_ip

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Кэш для конфигураций (TTL 60 секунд)
_config_cache = {}
_config_cache_time = {}
CACHE_TTL = 60

# Пути к файлам
CONFIG_FILE = "/root/vpn-server/config/config.json"

# API ключ для аутентификации - загружается из переменных окружения
API_KEY = os.getenv("VPN_API_KEY")
if not API_KEY:
    raise ValueError("VPN_API_KEY environment variable is required")

class VPNKey(BaseModel):
    id: str
    name: str
    uuid: str
    created_at: str
    is_active: bool
    port: Optional[int] = None
    short_id: Optional[str] = None

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

# Загрузка конфигурации Xray с кэшированием
@lru_cache(maxsize=1)
def load_config_cached():
    """Загрузка конфигурации с LRU кэшем"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def load_config():
    """Загрузка конфигурации (с автоматической инвалидацией кэша)"""
    return load_config_cached()

# Сохранение конфигурации Xray
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    # Инвалидируем кэш при сохранении
    load_config_cached.cache_clear()

# Загрузка ключей
def load_keys():
    """Чтение всех ключей из хранилища"""
    return storage.get_all_keys()

# Перезапуск Xray сервиса с проверкой
def check_xray_process():
    """Проверка наличия процесса Xray"""
    try:
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
        logger.error(f"Error checking Xray process: {e}")
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
            result = subprocess.run(['/usr/bin/systemctl', 'restart', 'xray'], 
                                  timeout=10, capture_output=True, text=True)
            time.sleep(3)
            if check_xray_process():
                logger.info("Xray restarted via systemctl")
                return True
        except Exception as e:
            logger.warning(f"systemctl restart failed: {e}")
        
        # Если systemctl не сработал, запускаем напрямую
        logger.warning("systemctl restart failed, starting Xray directly...")
        subprocess.Popen(
            ['/usr/local/bin/xray', 'run', '-config', '/root/vpn-server/config/config.json'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        time.sleep(3)
        
        if check_xray_process():
            logger.info("Xray started directly")
            return True
        else:
            logger.error("Xray restart failed")
            return False
    except Exception as e:
        logger.error(f"Error restarting Xray: {e}")
        return False

# Проверка конфигурации Xray
def verify_xray_config():
    try:
        # Проверяем, что конфигурация синхронизирована с SQLite
        keys = load_keys()
        config = load_config()
        
        # Получаем UUID из SQLite
        key_uuids = {key["uuid"] for key in keys}
        
        # Получаем UUID из config.json
        config_uuids = set()
        for inbound in config.get("inbounds", []):
            if inbound.get("protocol") == "vless":
                for client in inbound.get("settings", {}).get("clients", []):
                    config_uuids.add(client.get("id"))
        
        # Проверяем соответствие
        if key_uuids == config_uuids:
            print("Xray configuration is synchronized with SQLite")
            return True
        else:
            print(f"Configuration mismatch: SQLite has {len(key_uuids)} keys, config.json has {len(config_uuids)} clients")
            return False
    except Exception as e:
        print(f"Error verifying Xray config: {e}")
        return False

# Принудительная синхронизация конфигурации Xray
def force_sync_xray_config():
    try:
        keys = load_keys()
        config = load_config()
        
        # Обновляем конфигурацию на основе SQLite
        # Используем update_xray_config_for_keys для правильной синхронизации
        if not update_xray_config_for_keys(keys):
            print("Warning: Failed to update Xray config for keys")
            return False
        
        # Синхронизируем short_id из БД в конфигурацию
        sync_result = sync_short_ids_from_db()
        if sync_result.get("success"):
            fixed_count = sync_result.get("fixed_count", 0)
            if fixed_count > 0:
                print(f"Synced {fixed_count} short_id(s) from database to Xray config")
        else:
            print(f"Warning: Failed to sync short_ids: {sync_result.get('error')}")
        
        print("Xray configuration force-synchronized with SQLite")
        return True
    except Exception as e:
        print(f"Error force-syncing Xray config: {e}")
        import traceback
        traceback.print_exc()
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
    return {"message": "VPN Key Management API", "version": "2.3.6", "status": "running"}

@app.get("/api/")
async def api_root():
    return {"message": "VPN Key Management API", "version": "2.3.6", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check эндпоинт для мониторинга состояния системы"""
    try:
        # Проверка статуса сервисов
        # Xray проверяем через процесс, так как systemd unit может не работать
        xray_status = "running" if check_xray_process() else "stopped"
        api_status = "running" if subprocess.run(['/usr/bin/systemctl', 'is-active', 'vpn-api'], 
                                               capture_output=True, text=True).returncode == 0 else "stopped"
        nginx_status = "running" if subprocess.run(['/usr/bin/systemctl', 'is-active', 'nginx'], 
                                                 capture_output=True, text=True).returncode == 0 else "stopped"
        
        # Получение системных ресурсов
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.3.6",
            "services": {
                "xray": xray_status,
                "api": api_status,
                "nginx": nginx_status
            },
            "resources": {
                "memory_usage_percent": memory.percent,
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "disk_usage_percent": disk.percent,
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "cpu_usage_percent": psutil.cpu_percent(interval=1)
            },
            "uptime_seconds": int(time.time() - psutil.boot_time())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.post("/api/keys", response_model=VPNKey)
@limiter.limit("5/minute")
async def create_key(request: Request, key_request: CreateKeyRequest, api_key: str = Depends(verify_api_key)):
    """Создать новый VPN ключ с индивидуальным портом"""
    key_uuid = None
    assigned_port = None
    key_stored = False
    
    try:
        # Проверяем лимит ключей (максимум 100)
        if storage.count_keys() >= 100:
            raise HTTPException(status_code=400, detail="Maximum number of keys (100) reached")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Убеждаемся, что Reality ключи доступны
        reality_keys = xray_config_manager._load_reality_keys()
        if not reality_keys.get('public_key'):
            raise HTTPException(
                status_code=500,
                detail="Public key not found in keys.env. Please check configuration."
            )
        if not reality_keys.get('private_key'):
            raise HTTPException(
                status_code=500,
                detail="Private key not found in keys.env. Please check configuration."
            )
        
        # Генерация UUID для ключа
        key_uuid = str(uuid.uuid4())

        # Генерация индивидуального shortId для каждого ключа (для разделения пользователей)
        # Используем 4 байта для получения 8 hex символов (совместимость с Android)
        # Проверяем уникальность short_id
        existing_keys = storage.get_all_keys()
        existing_short_ids = {k.get('short_id') for k in existing_keys if k.get('short_id')}
        short_id = secrets.token_hex(4)  # 4 байта = 8 hex символов
        # Проверка: short_id должен быть ровно 8 символов
        if len(short_id) != 8:
            raise HTTPException(status_code=500, detail=f"Invalid short_id length: {len(short_id)}, expected 8")
        max_attempts = 10
        attempt = 0
        while short_id in existing_short_ids and attempt < max_attempts:
            short_id = secrets.token_hex(4)
            # Проверка длины при каждой генерации
            if len(short_id) != 8:
                raise HTTPException(status_code=500, detail=f"Invalid short_id length: {len(short_id)}, expected 8")
            attempt += 1
        if short_id in existing_short_ids:
            raise HTTPException(status_code=500, detail="Failed to generate unique short_id")
        
        # Выбор случайного SNI из доступных ServerNames (будет сохранен и использоваться постоянно)
        import json
        with open('/root/vpn-server/config/config.json', 'r') as f:
            config = json.load(f)
        # Находим первый vless inbound для получения списка ServerNames
        server_names = []
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                reality_settings = inbound.get('streamSettings', {}).get('realitySettings', {})
                server_names = reality_settings.get('serverNames', [])
                if server_names:
                    break
        if not server_names:
            # Fallback на стандартный список
            server_names = ['www.microsoft.com', 'www.cloudflare.com', 'www.google.com']
        # Используем фиксированный SNI для всех ключей (iOS и Android совместимость)
        selected_sni = "www.microsoft.com"  # Фиксированный для всех ключей
        
        # Назначаем порт для ключа
        assigned_port = assign_port_for_key(key_uuid, str(uuid.uuid4()), key_request.name)
        if not assigned_port:
            raise HTTPException(status_code=500, detail="No available ports")
        
        # Создание нового ключа с индивидуальным short_id и SNI
        new_key = {
            "id": str(uuid.uuid4()),
            "name": key_request.name,
            "uuid": key_uuid,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "port": assigned_port,
            "short_id": short_id,  # Индивидуальный short_id для каждого ключа
            "sni": selected_sni  # Случайно выбранный SNI, который будет использоваться постоянно
        }
        
        # Сохраняем ключ в хранилище
        storage.add_key(new_key)
        key_stored = True
        
        # Добавляем ключ в конфигурацию Xray с индивидуальным short_id
        if not add_key_to_xray_config(key_uuid, key_request.name, short_id):
            raise HTTPException(status_code=500, detail="Failed to add key to Xray config")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Убеждаемся, что publicKey добавлен в конфигурацию
        try:
            config = xray_config_manager._load_config()
            if config:
                reality_keys = xray_config_manager._load_reality_keys()
                public_key = reality_keys.get('public_key')
                if public_key:
                    for inbound in config.get('inbounds', []):
                        clients = inbound.get('settings', {}).get('clients', [])
                        for client in clients:
                            if client.get('id') == key_uuid:
                                reality_settings = inbound.get('streamSettings', {}).get('realitySettings', {})
                                if not reality_settings.get('publicKey'):
                                    # Исправляем отсутствие publicKey
                                    reality_settings['publicKey'] = public_key
                                    xray_config_manager._save_config(config)
                                    xray_config_manager._apply_inbound_via_api(inbound)
                                    logger.warning(f"Fixed missing publicKey for key {key_uuid} after creation")
                                break
        except Exception as e:
            logger.error(f"Failed to verify publicKey after key creation: {e}")
            # Не прерываем создание, но логируем ошибку
        
        # Проверяем синхронизацию short_id после создания
        try:
            # Перезагружаем ключ из БД для проверки
            created_key = storage.get_key_by_uuid(key_uuid)
            if created_key and created_key.get("short_id") != short_id:
                print(f"Warning: Short ID mismatch after creation for key {key_uuid}")
                # Исправляем несоответствие
                sync_result = sync_short_ids_from_db()
                if sync_result.get("success") and sync_result.get("fixed_count", 0) > 0:
                    print(f"Fixed {sync_result.get('fixed_count')} short_id mismatch(es)")
        except Exception as e:
            print(f"Warning: Failed to verify short_id sync after key creation: {e}")
        
        # Инициализируем историю трафика для нового ключа
        try:
            traffic_history.update_key_traffic(
                key_uuid, 
                key_request.name, 
                assigned_port, 
                {"total_bytes": 0, "rx_bytes": 0, "tx_bytes": 0, "connections": 0}
            )
        except Exception as e:
            print(f"Warning: Failed to initialize traffic history for key {key_uuid}: {e}")
        
        # Проверка корректности сгенерированного URL
        try:
            from generate_client_config import generate_client_config
            test_url = generate_client_config(key_uuid, key_request.name, assigned_port)
            # Проверяем, что URL содержит все необходимые параметры
            required_params = ['pbk=', 'sid=', 'sni=']
            if not all(param in test_url for param in required_params):
                logger.error(f"Generated URL is missing required parameters: {test_url}")
                # Не прерываем создание, но логируем ошибку
            if not test_url.startswith('vless://'):
                logger.error(f"Generated URL has invalid format: {test_url}")
            # КРИТИЧНО: Проверяем, что используется fp=chrome для Android совместимости
            if 'fp=randomized' in test_url:
                logger.error(f"Generated URL uses fp=randomized instead of fp=chrome: {test_url}")
                # Это критическая ошибка - нужно исправить
            if 'fp=chrome' not in test_url:
                logger.error(f"Generated URL missing fp=chrome: {test_url}")
        except Exception as e:
            logger.error(f"Failed to generate test URL for verification: {e}")
            # Не прерываем создание, но логируем ошибку
        
        return VPNKey(**new_key)
        
    except HTTPException:
        if assigned_port:
            release_port_for_key(key_uuid)
        if key_stored:
            storage.delete_key_by_uuid(key_uuid)
            traffic_history.reset_key_traffic(key_uuid)
        raise
    except Exception as e:
        if assigned_port:
            release_port_for_key(key_uuid)
        if key_stored:
            storage.delete_key_by_uuid(key_uuid)
            traffic_history.reset_key_traffic(key_uuid)
        raise HTTPException(status_code=500, detail=f"Failed to create key: {str(e)}")

@app.delete("/api/keys/{key_id}")
@limiter.limit("10/minute")
async def delete_key(key_id: str, request: Request, api_key: str = Depends(verify_api_key)):
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
        
        # Удаление ключа из хранилища
        storage.delete_key_by_uuid(key_to_delete["uuid"])
        
        return {"message": "Key deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete key: {str(e)}")

@app.get("/api/keys", response_model=List[VPNKey])
@limiter.limit("30/minute")
async def list_keys(request: Request, api_key: str = Depends(verify_api_key)):
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
@limiter.limit("60/minute")
async def get_key(key_id: str, request: Request, api_key: str = Depends(verify_api_key)):
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
            key.get("name", "") or "",  # Убеждаемся, что имя передается
            str(port) if port else "443"
        ], capture_output=True, text=True, encoding='utf-8', check=True)

        vless_url = result.stdout.strip()
        response = {
            "key": VPNKey(**key),
            "client_config": vless_url,
            "vless_url": vless_url
        }
        # Возвращаем short_id из БД для информации
        if key.get("short_id"):
            response["short_id"] = key["short_id"]
        
        return response
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate client config: {e.stderr}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key config: {str(e)}")



# ===== ЭНДПОИНТЫ ТОЧНОГО ПОДСЧЕТА ТРАФИКА ЧЕРЕЗ XRAY API =====




@app.post("/api/system/sync-config")
@limiter.limit("3/minute")
async def sync_xray_config(request: Request, api_key: str = Depends(verify_api_key)):
    """Принудительная синхронизация конфигурации Xray с SQLite"""
    try:
        # Принудительная синхронизация (включая short_id)
        if not force_sync_xray_config():
            raise HTTPException(status_code=500, detail="Failed to sync configuration")
        
        # Перезапуск Xray
        if not restart_xray():
            raise HTTPException(status_code=500, detail="Failed to restart Xray service")
        
        # Проверка синхронизации
        if not verify_xray_config():
            raise HTTPException(status_code=500, detail="Configuration sync verification failed")
        
        # Валидация синхронизации short_id
        keys = load_keys()
        validation = validate_xray_config_sync(keys)
        
        return {
            "message": "Configuration synchronized successfully",
            "status": "synced",
            "validation": validation,
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
        
        # Получаем UUID из SQLite
        key_uuids = {key["uuid"] for key in keys}
        
        # Получаем UUID из config.json
        config_uuids = set()
        for inbound in config.get("inbounds", []):
            if inbound.get("protocol") == "vless":
                for client in inbound.get("settings", {}).get("clients", []):
                    config_uuids.add(client.get("id"))
        
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
            "max_ports": 100,
            "port_range": "10001-10100",
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


@app.get("/api/system/xray/inbounds")
async def list_xray_inbounds(api_key: str = Depends(verify_api_key)):
    """Список активных VLESS inbound'ов согласно конфигурации"""
    try:
        config = load_config()
        inbounds = []
        for inbound in config.get("inbounds", []):
            if inbound.get("protocol") != "vless":
                continue
            clients = inbound.get("settings", {}).get("clients", [])
            reality_settings = inbound.get("streamSettings", {}).get("realitySettings", {})
            inbounds.append({
                "tag": inbound.get("tag"),
                "port": inbound.get("port"),
                "client_count": len(clients),
                "uuids": [client.get("id") for client in clients],
                "short_ids": reality_settings.get("shortIds", []),
                "dest": reality_settings.get("dest"),
                "server_names": reality_settings.get("serverNames", [])
            })
        return {
            "inbounds": inbounds,
            "timestamp": int(time.time()),
            "source": "config.json"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Xray inbounds: {str(e)}")

@app.post("/api/system/xray/sync-config")
async def sync_xray_config_endpoint(api_key: str = Depends(verify_api_key)):
    """Синхронизировать конфигурацию Xray с ключами"""
    try:
        keys = load_keys()
        if update_xray_config_for_keys(keys):
            # Синхронизируем short_id из БД в конфигурацию
            sync_result = sync_short_ids_from_db()
            if not sync_result.get("success"):
                print(f"Warning: Failed to sync short_ids: {sync_result.get('error')}")
            
            # Перезапуск Xray
            if not restart_xray():
                raise HTTPException(status_code=500, detail="Failed to restart Xray service")
            
            return {
                "message": "Xray configuration synchronized successfully",
                "status": "synced",
                "short_id_sync": sync_result,
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

@app.post("/api/system/fix-reality-keys")
async def fix_reality_keys(api_key: str = Depends(verify_api_key)):
    """Исправление Reality ключей в конфигурации Xray"""
    try:
        if fix_reality_keys_in_xray_config():
            if restart_xray():
                return {
                    "status": "fixed",
                    "message": "Reality keys fixed successfully",
                    "timestamp": int(time.time())
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to restart Xray service"
                }
        else:
            return {
                "status": "error",
                "message": "Failed to fix Reality keys"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ЭНДПОИНТЫ ТРАФИКА =====

@app.get("/api/keys/{key_id}/traffic")
async def get_key_traffic(key_id: str, api_key: str = Depends(verify_api_key)):
    """Получить накопительный трафик для конкретного ключа"""
    try:
        # Находим ключ по key_id
        keys = load_keys()
        key = next((k for k in keys if k["id"] == key_id), None)
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # Обновляем историю на основе данных из Xray Stats API перед возвратом
        if XRAY_STATS_AVAILABLE:
            traffic_history.update_key_traffic(
                key["uuid"], 
                key["name"], 
                key.get("port", 0)
            )
        
        # Получаем накопительный трафик ключа
        result = traffic_history.get_key_total_traffic(key["uuid"])
        
        if not result:
            # Если записи нет, создаем пустую
            traffic_history.update_key_traffic(
                key["uuid"], 
                key["name"], 
                key.get("port", 0)
            )
            result = traffic_history.get_key_total_traffic(key["uuid"])
        
        return {
            "status": "success",
            "key_id": key_id,
            "key_uuid": key["uuid"],
            "total_bytes": result["total_traffic"]["total_bytes"],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get key traffic: {str(e)}")

@app.post("/api/keys/{key_id}/traffic/reset")
async def reset_key_traffic(key_id: str, api_key: str = Depends(verify_api_key)):
    """Обнулить накопительный трафик для конкретного ключа"""
    try:
        # Находим ключ по key_id
        keys = load_keys()
        key = next((k for k in keys if k["id"] == key_id), None)
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # Обнуляем накопительный трафик
        success = traffic_history.reset_key_traffic(key["uuid"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Traffic history not found for this key")
        
        return {
            "status": "success",
            "message": "Traffic reset successfully",
            "key_id": key_id,
            "key_uuid": key["uuid"],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset traffic: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Настройки из переменных окружения
    host = os.getenv("VPN_HOST", "0.0.0.0")
    port = int(os.getenv("VPN_PORT", "8000"))
    workers = int(os.getenv("VPN_WORKERS", "2"))
    max_requests = int(os.getenv("VPN_WORKER_MAX_REQUESTS", "0") or 0)
    enable_https = os.getenv("VPN_ENABLE_HTTPS", "false").lower() == "true"
    ssl_cert = os.getenv("VPN_SSL_CERT_PATH", "/etc/ssl/certs/vpn-api.crt")
    ssl_key = os.getenv("VPN_SSL_KEY_PATH", "/etc/ssl/private/vpn-api.key")
    
    uvicorn_kwargs = {
        "host": host,
        "port": port,
        "workers": workers,
    }
    if max_requests > 0:
        uvicorn_kwargs["limit_max_requests"] = max_requests
    
    if enable_https and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f"🚀 Starting VPN API with HTTPS on {host}:{port} ({workers} workers)")
        uvicorn.run(
            app,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key,
            **uvicorn_kwargs,
        )
    else:
        print(f"🚀 Starting VPN API with HTTP on {host}:{port} ({workers} workers)")
        uvicorn.run(app, **uvicorn_kwargs)