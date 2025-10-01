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
    activity_type: "sleep", "feeding", "walk", "diaper", "temperature", "medication", "mood"
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
        elif "temperature" in activity_type.lower() or "температур" in activity_type.lower() or "градус" in activity_type.lower():
            if 'time' not in data:
                data['time'] = current_time
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/temperature/", json=data)
        elif "medication" in activity_type.lower() or "лекарств" in activity_type.lower() or "таблет" in activity_type.lower():
            if 'time' not in data:
                data['time'] = current_time
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/medication/", json=data)
        elif "mood" in activity_type.lower() or "настроен" in activity_type.lower():
            if 'time' not in data:
                data['time'] = current_time
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/activities/mood/", json=data)
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
    Примеры: "5 минут назад", "час назад", "утром", "вчера вечером"
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)

    if not time_expression or time_expression == "":
        time_expression = "сейчас"

    time_expression = time_expression.lower()

    # Текущий момент
    if any(word in time_expression for word in ["сейчас", "только что", "прямо сейчас"]):
        return now.isoformat()

    # Обработка "вчера", "позавчера"
    base_date = now
    if "позавчера" in time_expression:
        base_date = now - timedelta(days=2)
    elif "вчера" in time_expression:
        base_date = now - timedelta(days=1)
    elif "сегодня" in time_expression:
        base_date = now

    # Обработка частей дня
    if any(word in time_expression for word in ["утром", "утра"]):
        if "вчера" in time_expression or "позавчера" in time_expression:
            result = base_date.replace(hour=8, minute=0, second=0, microsecond=0)
        elif now.hour >= 12:  # Если сейчас после полудня, "утром" = сегодня утром
            result = now.replace(hour=8, minute=0, second=0, microsecond=0)
        else:
            result = now  # Если сейчас утро, то "утром" = сейчас
    elif any(word in time_expression for word in ["днем", "в обед", "обед"]):
        if "вчера" in time_expression or "позавчера" in time_expression:
            result = base_date.replace(hour=13, minute=0, second=0, microsecond=0)
        elif now.hour >= 15:
            result = now.replace(hour=13, minute=0, second=0, microsecond=0)
        else:
            result = now
    elif any(word in time_expression for word in ["вечером", "вечера"]):
        if "вчера" in time_expression or "позавчера" in time_expression:
            result = base_date.replace(hour=19, minute=0, second=0, microsecond=0)
        elif now.hour >= 21:
            result = now.replace(hour=19, minute=0, second=0, microsecond=0)
        else:
            result = now
    elif any(word in time_expression for word in ["ночью", "ночь"]):
        if "вчера" in time_expression:
            result = base_date.replace(hour=23, minute=0, second=0, microsecond=0)
        elif "позавчера" in time_expression:
            result = base_date.replace(hour=23, minute=0, second=0, microsecond=0)
        else:
            result = now.replace(hour=2, minute=0, second=0, microsecond=0)

    # Обработка относительного времени "X назад"
    elif "назад" in time_expression:
        if "минут" in time_expression:
            minutes = extract_number(time_expression)
            result = now - timedelta(minutes=minutes)
        elif "час" in time_expression:
            hours = extract_number(time_expression)
            result = now - timedelta(hours=hours)
        elif "день" in time_expression or "дня" in time_expression or "дней" in time_expression:
            days = extract_number(time_expression)
            result = now - timedelta(days=days)
        else:
            result = now

    # Обработка относительного времени "через X"
    elif "через" in time_expression:
        if "минут" in time_expression:
            minutes = extract_number(time_expression)
            result = now + timedelta(minutes=minutes)
        elif "час" in time_expression:
            hours = extract_number(time_expression)
            result = now + timedelta(hours=hours)
        else:
            result = now

    # Обработка конкретного времени "в 14:30", "в 2 часа"
    elif "в " in time_expression:
        time_part = time_expression.split("в ")[-1].strip()

        # Попытка распарсить время вида "14:30"
        if ":" in time_part:
            try:
                time_obj = datetime.strptime(time_part.split()[0], "%H:%M")
                result = base_date.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
            except:
                result = now
        # Обработка "в 2 часа", "в 14 часов"
        elif "час" in time_part:
            hour = extract_number(time_part)
            if hour > 0 and hour <= 24:
                result = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            else:
                result = now
        else:
            result = now

    # Обработка "полчаса назад", "полтора часа назад"
    elif "полчаса" in time_expression:
        if "назад" in time_expression:
            result = now - timedelta(minutes=30)
        else:
            result = now + timedelta(minutes=30)
    elif "полтора часа" in time_expression:
        if "назад" in time_expression:
            result = now - timedelta(minutes=90)
        else:
            result = now + timedelta(minutes=90)

    # По умолчанию
    else:
        # Попытка найти время в формате HH:MM
        import re
        time_pattern = re.search(r'(\d{1,2}):(\d{2})', time_expression)
        if time_pattern:
            hour, minute = int(time_pattern.group(1)), int(time_pattern.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                result = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                result = now
        else:
            result = now

    return result.isoformat()

def extract_number(text: str) -> int:
    """Извлекает число из текста"""
    words_to_numbers = {
        "один": 1, "одну": 1, "одно": 1, "одной": 1,
        "два": 2, "две": 2, "двух": 2,
        "три": 3, "трех": 3, "трёх": 3,
        "четыре": 4, "четырех": 4, "четырёх": 4,
        "пять": 5, "пяти": 5,
        "шесть": 6, "шести": 6,
        "семь": 7, "семи": 7,
        "восемь": 8, "восьми": 8,
        "девять": 9, "девяти": 9,
        "десять": 10, "десяти": 10,
        "одиннадцать": 11, "двенадцать": 12,
        "тринадцать": 13, "четырнадцать": 14,
        "пятнадцать": 15, "двадцать": 20,
        "тридцать": 30, "сорок": 40,
        "пятьдесят": 50, "шестьдесят": 60,
        "полчаса": 30, "час": 1, "пару": 2,
        "несколько": 3, "много": 5
    }

    text = text.lower()

    # Сначала ищем числа прописью
    for word, num in words_to_numbers.items():
        if word in text:
            return num

    # Потом ищем цифры
    import re
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])

    return 1  # По умолчанию

@tool
def relative_time_tool(event_type: str, time_offset: str, child_id: int) -> str:
    """
    Вычисляет время относительно последнего события
    Примеры: "через час после кормления", "за 30 минут до сна"
    """
    try:
        # Получаем последнее событие указанного типа
        if "корм" in event_type.lower() or "feeding" in event_type.lower():
            endpoint = f"/activities/child/{child_id}/today"
        elif "сон" in event_type.lower() or "sleep" in event_type.lower():
            endpoint = f"/activities/child/{child_id}/today"
        else:
            return datetime.now(pytz.UTC).isoformat()

        response = requests.get(f"{ACTIVITY_SERVICE_URL}{endpoint}")
        if response.status_code != 200:
            return datetime.now(pytz.UTC).isoformat()

        data = response.json()

        # Находим последнее событие нужного типа
        last_event_time = None
        if "корм" in event_type.lower():
            if data.get("feeding"):
                last_feeding = sorted(data["feeding"], key=lambda x: x["time"], reverse=True)[0]
                last_event_time = datetime.fromisoformat(last_feeding["time"].replace('Z', '+00:00'))
        elif "сон" in event_type.lower():
            if data.get("sleep"):
                last_sleep = sorted(data["sleep"], key=lambda x: x["start_time"], reverse=True)[0]
                last_event_time = datetime.fromisoformat(last_sleep["start_time"].replace('Z', '+00:00'))

        if not last_event_time:
            return datetime.now(pytz.UTC).isoformat()

        # Парсим offset
        if "через" in time_offset.lower() or "после" in time_offset.lower():
            if "час" in time_offset:
                hours = extract_number(time_offset)
                result = last_event_time + timedelta(hours=hours)
            elif "минут" in time_offset:
                minutes = extract_number(time_offset)
                result = last_event_time + timedelta(minutes=minutes)
            else:
                result = last_event_time
        elif "до" in time_offset.lower() or "перед" in time_offset.lower():
            if "час" in time_offset:
                hours = extract_number(time_offset)
                result = last_event_time - timedelta(hours=hours)
            elif "минут" in time_offset:
                minutes = extract_number(time_offset)
                result = last_event_time - timedelta(minutes=minutes)
            else:
                result = last_event_time
        else:
            result = last_event_time

        return result.isoformat()
    except Exception as e:
        return datetime.now(pytz.UTC).isoformat()

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