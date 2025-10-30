"""
API сервер для удалённого запуска парсера через App Script
Используется FastAPI для создания REST API endpoint
"""

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import subprocess
import os
from datetime import datetime
from typing import Optional
import hashlib
import hmac
from loguru import logger

# Настройка логирования
logger.add(
    "logs/api_server_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO"
)

app = FastAPI(
    title="Ozon Parser API",
    description="API для удалённого запуска парсера Ozon",
    version="1.0.0"
)

# Секретный ключ для аутентификации (ДОЛЖЕН БЫТЬ В .env!)
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION")

# Статус текущего выполнения
current_task_status = {
    "is_running": False,
    "started_at": None,
    "last_run": None,
    "last_status": None,
    "last_error": None
}


class TriggerRequest(BaseModel):
    """Запрос на запуск парсера"""
    source: str = "manual"  # manual, cron, app_script
    force: bool = False  # Принудительный запуск даже если уже выполняется


def verify_api_key(authorization: Optional[str]) -> bool:
    """Проверка API ключа"""
    if not authorization:
        return False
    
    try:
        # Ожидается формат: "Bearer <api_key>"
        auth_type, token = authorization.split(" ")
        if auth_type.lower() != "bearer":
            return False
        
        # Сравнение с секретным ключом
        return hmac.compare_digest(token, API_SECRET_KEY)
    except Exception:
        return False


async def run_parser_task():
    """Фоновая задача для запуска парсера"""
    global current_task_status
    
    try:
        current_task_status["is_running"] = True
        current_task_status["started_at"] = datetime.now().isoformat()
        current_task_status["last_error"] = None
        
        logger.info("Запуск парсера через API...")
        
        # Запуск main.py как subprocess
        process = await asyncio.create_subprocess_exec(
            "python", "main.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            current_task_status["last_status"] = "success"
            logger.info(f"Парсер завершён успешно: {stdout.decode('utf-8', errors='ignore')}")
        else:
            current_task_status["last_status"] = "error"
            current_task_status["last_error"] = stderr.decode('utf-8', errors='ignore')
            logger.error(f"Парсер завершён с ошибкой: {stderr.decode('utf-8', errors='ignore')}")
        
    except Exception as e:
        current_task_status["last_status"] = "error"
        current_task_status["last_error"] = str(e)
        logger.error(f"Ошибка при запуске парсера: {e}")
    
    finally:
        current_task_status["is_running"] = False
        current_task_status["last_run"] = datetime.now().isoformat()


@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "service": "Ozon Parser API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/health": "Проверка работоспособности",
            "/status": "Текущий статус парсера",
            "/trigger": "Запуск парсера (POST, требует авторизацию)"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервера"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "parser_running": current_task_status["is_running"]
    }


@app.get("/status")
async def get_status(authorization: Optional[str] = Header(None)):
    """Получение статуса текущего выполнения"""
    # Проверка авторизации
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key")
    
    return {
        "status": "ok",
        "data": current_task_status
    }


@app.post("/trigger")
async def trigger_parser(
    request: TriggerRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """
    Запуск парсера
    
    Требуется заголовок: Authorization: Bearer <API_SECRET_KEY>
    """
    # Проверка авторизации
    if not verify_api_key(authorization):
        logger.warning("Попытка запуска без авторизации")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key")
    
    # Проверка, не выполняется ли уже парсер
    if current_task_status["is_running"] and not request.force:
        logger.warning("Попытка запуска парсера, который уже выполняется")
        raise HTTPException(
            status_code=409,
            detail="Parser is already running. Use 'force: true' to override."
        )
    
    # Добавление фоновой задачи
    background_tasks.add_task(run_parser_task)
    
    logger.info(f"Парсер запущен через API (source: {request.source})")
    
    return {
        "status": "accepted",
        "message": "Parser task started",
        "source": request.source,
        "started_at": datetime.now().isoformat()
    }


@app.get("/logs")
async def get_logs(
    lines: int = 100,
    authorization: Optional[str] = Header(None)
):
    """Получение последних строк логов"""
    # Проверка авторизации
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key")
    
    try:
        # Поиск последнего лог-файла
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return {"status": "ok", "logs": []}
        
        log_files = [f for f in os.listdir(log_dir) if f.startswith("api_server_")]
        if not log_files:
            return {"status": "ok", "logs": []}
        
        latest_log = max(log_files)
        log_path = os.path.join(log_dir, latest_log)
        
        # Чтение последних N строк
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "status": "ok",
            "log_file": latest_log,
            "lines_count": len(last_lines),
            "logs": [line.strip() for line in last_lines]
        }
    
    except Exception as e:
        logger.error(f"Ошибка при чтении логов: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@app.post("/upload-cookies")
async def upload_cookies(cookies: list, authorization: str = Header(None)):
    """
    Загрузка cookies для авторизации в Ozon
    
    Тело запроса: массив объектов cookies из браузера
    """
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key")
    
    try:
        import json
        
        # Сохраняем в /data для постоянного хранилища (важно для Amvera!)
        cookies_path = '/data/ozon_cookies.json' if os.path.exists('/data') else 'ozon_cookies.json'
        
        with open(cookies_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Cookies загружены: {len(cookies)} штук в {cookies_path}")
        
        return {
            "status": "success",
            "message": "Cookies uploaded successfully",
            "cookies_count": len(cookies),
            "saved_to": cookies_path
        }
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке cookies: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading cookies: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Запуск сервера
    uvicorn.run(
        app,
        host="0.0.0.0",  # Доступен извне
        port=8000,
        log_level="info"
    )
