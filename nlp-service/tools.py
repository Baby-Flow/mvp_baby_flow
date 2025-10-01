"""
Tools для мультиагентной системы
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from langchain.tools import tool
import pytz

ACTIVITY_SERVICE_URL = os.getenv("ACTIVITY_SERVICE_URL", "http://localhost:8003")

@tool
def database_reader_tool(child_id: int, activity_type: str = "all") -> Dict:
    """
    Читает последние активности ребенка из БД
    """
    try:
        if activity_type == "open_sleep":
            response = requests.get(f"{ACTIVITY_SERVICE_URL}/activities/sleep/{child_id}/open")
            if response.status_code == 200:
                return response.json()
            return None
        elif activity_type == "today":
            response = requests.get(f"{ACTIVITY_SERVICE_URL}/activities/child/{child_id}/today")
            return response.json()
        else:
            response = requests.get(f"{ACTIVITY_SERVICE_URL}/activities/child/{child_id}")
            return response.json()
    except Exception as e:
        return {"error": str(e)}

@tool
def database_writer_tool(activity_type: str, data: Dict) -> Dict:
    """
    Записывает активность в БД
    activity_type: "sleep", "feeding", "walk", "diaper"
    data: словарь с данными (обязательно должен содержать child_id)
    """
    try:
        # Проверяем наличие child_id
        if 'child_id' not in data:
            return {"error": "child_id is required"}

        # Добавляем время по умолчанию если не указано (в UTC)
        current_time = datetime.now(pytz.UTC).isoformat()

        # Нормализуем тип активности
        if "sleep" in activity_type.lower() or "сон" in activity_type.lower():
            if 'start_time' not in data:
                data['start_time'] = current_time
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/sleep/", json=data)
        elif "feeding" in activity_type.lower() or "корм" in activity_type.lower():
            if 'time' not in data:
                data['time'] = current_time
            if 'type' not in data:
                data['type'] = 'unknown'
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/feeding/", json=data)
        elif "walk" in activity_type.lower() or "прогул" in activity_type.lower():
            if 'start_time' not in data:
                data['start_time'] = current_time
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/walk/", json=data)
        elif "diaper" in activity_type.lower() or "подгуз" in activity_type.lower() or "пописал" in activity_type.lower() or "покакал" in activity_type.lower():
            if 'time' not in data:
                data['time'] = current_time
            if 'type' not in data:
                # Определяем тип по activity_type
                if "покакал" in activity_type.lower() or "poop" in activity_type.lower():
                    data['type'] = 'poop'
                elif "пописал" in activity_type.lower() or "pee" in activity_type.lower():
                    data['type'] = 'pee'
                else:
                    data['type'] = 'both'
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/diaper/", json=data)
        else:
            return {"error": f"Unknown activity type: {activity_type}"}

        if response.status_code == 200:
            return response.json()
        return {"error": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@tool
def end_sleep_tool(sleep_id: int, end_time: str) -> Dict:
    """
    Завершает активный сон
    """
    try:
        # Убедимся что end_time в правильном формате
        if not end_time:
            moscow_tz = pytz.timezone('Europe/Moscow')
            end_time = datetime.now(moscow_tz).isoformat()

        response = requests.put(
            f"{ACTIVITY_SERVICE_URL}/activities/sleep/{sleep_id}/end?end_time={end_time}"
        )
        if response.status_code == 200:
            return response.json()
        return {"error": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@tool
def time_calculator_tool(time_expression: str = "сейчас") -> str:
    """
    Преобразует относительное время в абсолютное ISO формат
    Примеры: "5 минут назад", "час назад", "утром", "сейчас"
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)

    if not time_expression or time_expression == "":
        time_expression = "сейчас"

    time_expression = time_expression.lower()

    # Обработка относительного времени
    if "назад" in time_expression:
        if "минут" in time_expression:
            minutes = extract_number(time_expression)
            result = now - timedelta(minutes=minutes)
        elif "час" in time_expression:
            hours = extract_number(time_expression)
            result = now - timedelta(hours=hours)
        else:
            result = now
    elif "сейчас" in time_expression or not time_expression:
        result = now
    elif "утром" in time_expression:
        result = now.replace(hour=8, minute=0, second=0)
    elif "днем" in time_expression:
        result = now.replace(hour=14, minute=0, second=0)
    elif "вечером" in time_expression:
        result = now.replace(hour=19, minute=0, second=0)
    else:
        # Попытка распарсить конкретное время
        try:
            result = datetime.strptime(time_expression, "%H:%M")
            result = result.replace(year=now.year, month=now.month, day=now.day)
            result = moscow_tz.localize(result)
        except:
            result = now

    return result.isoformat()

def extract_number(text: str) -> int:
    """Извлекает число из текста"""
    words_to_numbers = {
        "один": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
        "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
        "пятнадцать": 15, "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50
    }

    for word, num in words_to_numbers.items():
        if word in text:
            return num

    # Попытка найти цифру
    for word in text.split():
        if word.isdigit():
            return int(word)

    return 1  # По умолчанию

@tool
def activity_validator_tool(activity_type: str, duration_minutes: Optional[int] = None) -> Dict:
    """
    Проверяет корректность данных активности
    """
    if activity_type == "sleep" and duration_minutes:
        if duration_minutes > 720:  # больше 12 часов
            return {"valid": False, "reason": "Сон больше 12 часов маловероятен для дневного сна"}
        if duration_minutes < 10:
            return {"valid": False, "reason": "Сон меньше 10 минут - возможно, ребенок не заснул"}

    if activity_type == "feeding" and duration_minutes:
        if duration_minutes > 60:
            return {"valid": False, "reason": "Кормление больше часа необычно долго"}

    if activity_type == "walk" and duration_minutes:
        if duration_minutes > 300:  # больше 5 часов
            return {"valid": False, "reason": "Прогулка больше 5 часов слишком долгая"}

    return {"valid": True}