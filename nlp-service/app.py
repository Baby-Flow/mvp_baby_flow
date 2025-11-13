"""
NLP Service с мультиагентной системой
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import logging
from dotenv import load_dotenv

from orchestrator import BabyFlowOrchestrator

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="BabyFlow NLP Service")

# Инициализируем orchestrator
orchestrator = BabyFlowOrchestrator()

class MessageRequest(BaseModel):
    message: str
    child_id: int = 1
    user_id: Optional[int] = None
    telegram_chat_id: Optional[int] = None

class MessageResponse(BaseModel):
    success: bool
    response: str
    reasoning: Optional[str] = None
    error: Optional[str] = None

@app.get("/")
def root():
    return {"service": "NLP Service", "status": "running"}

@app.post("/process", response_model=MessageResponse)
def process_message(request: MessageRequest):
    """
    Обрабатывает сообщение от пользователя через мультиагентную систему
    """
    logger.info(f"Processing message from child_id={request.child_id}: {request.message}")
    try:
        result = orchestrator.process_message(
            message=request.message,
            child_id=request.child_id
        )
        logger.info(f"Successfully processed message: {result.get('response', '')}")
        return MessageResponse(**result)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "activity_service_url": os.getenv("ACTIVITY_SERVICE_URL", "not set")
    }

# Тестовые эндпоинты для отладки
@app.post("/test/parse_time")
def test_parse_time(expression: str):
    """Тестирует парсинг времени"""
    from tools import time_calculator_tool
    result = time_calculator_tool.invoke({"time_expression": expression})
    return {"input": expression, "parsed": result}

@app.get("/test/child/{child_id}/activities")
def test_get_activities(child_id: int):
    """Тестирует получение активностей"""
    from tools import database_reader_tool
    result = database_reader_tool.invoke({"child_id": child_id, "activity_type": "today"})
    return result