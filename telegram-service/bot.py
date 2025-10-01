import os
import asyncio
import logging
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NLP_SERVICE_URL = os.getenv("NLP_SERVICE_URL", "http://localhost:8002")
ACTIVITY_SERVICE_URL = os.getenv("ACTIVITY_SERVICE_URL", "http://localhost:8003")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временное хранилище для связи telegram_id с user_id и child_id
# В продакшене использовать Redis или БД
user_mapping = {}


@dp.message(CommandStart())
async def start_handler(message: Message):
    """Обработка команды /start"""
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name or "Пользователь"
    username = message.from_user.username

    # Проверяем или создаем пользователя
    try:
        response = requests.get(f"{ACTIVITY_SERVICE_URL}/users/telegram/{telegram_id}")
        if response.status_code == 404:
            # Создаем нового пользователя
            user_data = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name
            }
            response = requests.post(f"{ACTIVITY_SERVICE_URL}/users/", json=user_data)
            user = response.json()
            await message.answer(
                f"👋 Привет, {first_name}!\n\n"
                "Я Алиса - помогу вести дневник развития вашего малыша.\n"
                "Просто пишите мне обычными словами, например:\n"
                "• уснул\n"
                "• проснулся\n"
                "• покормила 200мл\n"
                "• гуляем в парке\n\n"
                "Сначала добавьте малыша командой:\n"
                "/add_child Имя 2024-01-15"
            )
        else:
            user = response.json()
            # Проверяем есть ли дети
            children_response = requests.get(f"{ACTIVITY_SERVICE_URL}/children/user/{user['id']}")
            children = children_response.json()

            if children:
                child = children[0]  # Берем первого ребенка
                user_mapping[telegram_id] = {"user_id": user["id"], "child_id": child["id"]}
                await message.answer(
                    f"С возвращением, {first_name}!\n"
                    f"Записываю активности для: {child['name']}\n\n"
                    "Просто пишите что происходит с малышом."
                )
            else:
                await message.answer(
                    f"С возвращением, {first_name}!\n\n"
                    "Добавьте ребенка командой:\n"
                    "/add_child Имя 2024-01-15"
                )
    except Exception as e:
        logger.error(f"Error in start_handler: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@dp.message(Command("add_child"))
async def add_child_handler(message: Message):
    """Добавление ребенка"""
    telegram_id = message.from_user.id

    try:
        # Получаем user_id
        response = requests.get(f"{ACTIVITY_SERVICE_URL}/users/telegram/{telegram_id}")
        if response.status_code == 404:
            await message.answer("Сначала выполните /start")
            return

        user = response.json()

        # Парсим команду
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer(
                "Формат: /add_child Имя ГГГГ-ММ-ДД\n"
                "Пример: /add_child Саша 2024-01-15"
            )
            return

        name = parts[1]
        birth_date = parts[2]

        # Создаем ребенка
        child_data = {
            "user_id": user["id"],
            "name": name,
            "birth_date": birth_date
        }

        response = requests.post(f"{ACTIVITY_SERVICE_URL}/children/", json=child_data)
        if response.status_code == 200:
            child = response.json()
            user_mapping[telegram_id] = {"user_id": user["id"], "child_id": child["id"]}
            await message.answer(
                f"✅ Добавлен ребенок: {name}\n"
                f"Дата рождения: {birth_date}\n\n"
                "Теперь можете записывать активности!"
            )
        else:
            await message.answer("Ошибка при добавлении. Проверьте формат даты.")
    except Exception as e:
        logger.error(f"Error in add_child: {e}")
        await message.answer("Произошла ошибка. Проверьте формат команды.")


@dp.message(Command("today"))
async def today_handler(message: Message):
    """Показать активности за сегодня"""
    telegram_id = message.from_user.id

    if telegram_id not in user_mapping:
        await message.answer("Сначала добавьте малыша через /add_child")
        return

    child_id = user_mapping[telegram_id]["child_id"]

    try:
        response = requests.get(f"{ACTIVITY_SERVICE_URL}/activities/child/{child_id}/today")
        if response.status_code == 200:
            data = response.json()

            text = "📊 *Сегодня у малыша:*\n\n"

            # Сон
            if data.get("sleep"):
                text += "😴 *Сон:*\n"
                moscow_tz = pytz.timezone('Europe/Moscow')
                for sleep in data["sleep"]:
                    # Парсим время и конвертируем в московское
                    start_dt = datetime.fromisoformat(sleep["start_time"].replace('Z', '+00:00'))
                    start_moscow = start_dt.astimezone(moscow_tz)
                    start = start_moscow.strftime("%H:%M")

                    if sleep["end_time"]:
                        end_dt = datetime.fromisoformat(sleep["end_time"].replace('Z', '+00:00'))
                        end_moscow = end_dt.astimezone(moscow_tz)
                        end = end_moscow.strftime("%H:%M")
                        duration = sleep.get("duration_minutes", 0)
                        hours = duration // 60
                        minutes = duration % 60
                        if hours > 0:
                            duration_str = f"{hours}ч {minutes}мин"
                        else:
                            duration_str = f"{minutes} мин"
                        text += f"• {start} - {end} ({duration_str})\n"
                    else:
                        text += f"• Спит с {start} 💤\n"

            # Кормление
            if data.get("feeding"):
                text += "\n🍼 *Кормления:*\n"
                moscow_tz = pytz.timezone('Europe/Moscow')
                for feed in data["feeding"]:
                    time_dt = datetime.fromisoformat(feed["time"].replace('Z', '+00:00'))
                    time_moscow = time_dt.astimezone(moscow_tz)
                    time = time_moscow.strftime("%H:%M")
                    text += f"• {time}"
                    if feed.get("amount_ml"):
                        text += f" - {feed['amount_ml']}мл"
                    if feed.get("food_name"):
                        text += f" ({feed['food_name']})"
                    text += "\n"

            # Прогулки
            if data.get("walks"):
                text += "\n🚶 *Прогулки:*\n"
                moscow_tz = pytz.timezone('Europe/Moscow')
                for walk in data["walks"]:
                    start_dt = datetime.fromisoformat(walk["start_time"].replace('Z', '+00:00'))
                    start_moscow = start_dt.astimezone(moscow_tz)
                    start = start_moscow.strftime("%H:%M")
                    if walk["end_time"]:
                        end_dt = datetime.fromisoformat(walk["end_time"].replace('Z', '+00:00'))
                        end_moscow = end_dt.astimezone(moscow_tz)
                        end = end_moscow.strftime("%H:%M")
                        text += f"• {start} - {end}"
                        if walk.get("location"):
                            text += f" ({walk['location']})"
                    else:
                        text += f"• Гуляем с {start} 🌳"
                    text += "\n"

            # Подгузники
            if data.get("diapers"):
                text += "\n🚼 *Подгузники:*\n"
                moscow_tz = pytz.timezone('Europe/Moscow')
                for diaper in data["diapers"]:
                    time_dt = datetime.fromisoformat(diaper["time"].replace('Z', '+00:00'))
                    time_moscow = time_dt.astimezone(moscow_tz)
                    time = time_moscow.strftime("%H:%M")

                    if diaper["type"] == "poop":
                        emoji = "💩"
                    elif diaper["type"] == "pee":
                        emoji = "💧"
                    else:
                        emoji = "🚼"

                    text += f"• {time} {emoji}"
                    if diaper.get("consistency"):
                        text += f" ({diaper['consistency']})"
                    text += "\n"

            if not any([data.get("sleep"), data.get("feeding"), data.get("walks"), data.get("diapers")]):
                text = "Пока нет записей за сегодня. Расскажите, что делает малыш? 😊"

            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("Не могу получить данные, попробуйте позже 🙏")
    except Exception as e:
        logger.error(f"Error in today_handler: {e}")
        await message.answer("Что-то пошло не так 😔")
        await message.answer("Сначала добавьте ребенка через /add_child")
        return

    child_id = user_mapping[telegram_id]["child_id"]

    try:
        response = requests.get(f"{ACTIVITY_SERVICE_URL}/activities/child/{child_id}/today")
        if response.status_code == 200:
            data = response.json()

            text = "📊 *Сегодняшние активности:*\n\n"

            # Сон
            if data.get("sleep"):
                text += "😴 *Сон:*\n"
                moscow_tz = pytz.timezone('Europe/Moscow')
                for sleep in data["sleep"]:
                    # Парсим время и конвертируем в московское
                    start_dt = datetime.fromisoformat(sleep["start_time"].replace('Z', '+00:00'))
                    start_moscow = start_dt.astimezone(moscow_tz)
                    start = start_moscow.strftime("%H:%M")

                    if sleep["end_time"]:
                        end_dt = datetime.fromisoformat(sleep["end_time"].replace('Z', '+00:00'))
                        end_moscow = end_dt.astimezone(moscow_tz)
                        end = end_moscow.strftime("%H:%M")
                        duration = sleep.get("duration_minutes", 0)
                        hours = duration // 60
                        minutes = duration % 60
                        if hours > 0:
                            duration_str = f"{hours}ч {minutes}мин"
                        else:
                            duration_str = f"{minutes} мин"
                        text += f"• {start} - {end} ({duration_str})\n"
                    else:
                        text += f"• Спит с {start}\n"

            # Кормление
            if data.get("feeding"):
                text += "\n🍼 *Кормления:*\n"
                for feed in data["feeding"]:
                    time = feed["time"].split("T")[1][:5]
                    text += f"• {time}"
                    if feed.get("amount_ml"):
                        text += f" - {feed['amount_ml']}мл"
                    if feed.get("food_name"):
                        text += f" ({feed['food_name']})"
                    text += "\n"

            # Прогулки
            if data.get("walks"):
                text += "\n🚶 *Прогулки:*\n"
                for walk in data["walks"]:
                    start = walk["start_time"].split("T")[1][:5]
                    if walk["end_time"]:
                        end = walk["end_time"].split("T")[1][:5]
                        text += f"• {start} - {end}"
                        if walk.get("location"):
                            text += f" ({walk['location']})"
                    else:
                        text += f"• Гуляет с {start}"
                    text += "\n"

            if not any([data.get("sleep"), data.get("feeding"), data.get("walks")]):
                text = "Пока нет записей за сегодня"

            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("Ошибка при получении данных")
    except Exception as e:
        logger.error(f"Error in today_handler: {e}")
        await message.answer("Произошла ошибка")


@dp.message(Command("help"))
async def help_handler(message: Message):
    """Помощь"""
    help_text = """
*Я Алиса, ваша помощница* 🤱

*Команды:*
/start - начать работу
/add_child - добавить малыша
/today - что было сегодня
/help - эта справка

*Просто пишите что происходит:*
• "уснул" - запишу начало сна
• "проснулся" - отмечу пробуждение
• "покормила" - запишу кормление
• "гуляем" - отмечу прогулку
• "покакал" - запишу смену подгузника
• "пописал" - отмечу мокрый подгузник

*Примеры сообщений:*
• спит с 14:30
• только что проснулся
• покормила грудью
• выпил 200мл смеси
• гуляем в парке

Я всегда рядом и помогу! 💕
"""
    await message.answer(help_text, parse_mode="Markdown")


@dp.message()
async def message_handler(message: Message):
    """Обработка всех текстовых сообщений"""
    telegram_id = message.from_user.id

    # Проверяем есть ли пользователь в маппинге
    if telegram_id not in user_mapping:
        # Пытаемся загрузить из БД
        try:
            response = requests.get(f"{ACTIVITY_SERVICE_URL}/users/telegram/{telegram_id}")
            if response.status_code == 200:
                user = response.json()
                children_response = requests.get(f"{ACTIVITY_SERVICE_URL}/children/user/{user['id']}")
                children = children_response.json()
                if children:
                    child = children[0]
                    user_mapping[telegram_id] = {"user_id": user["id"], "child_id": child["id"]}
                else:
                    await message.answer("Сначала добавьте ребенка через /add_child")
                    return
            else:
                await message.answer("Пожалуйста, начните с команды /start")
                return
        except:
            await message.answer("Пожалуйста, начните с команды /start")
            return

    child_id = user_mapping[telegram_id]["child_id"]

    # Отправляем в NLP service
    try:
        nlp_data = {
            "message": message.text,
            "child_id": child_id,
            "user_id": user_mapping[telegram_id]["user_id"],
            "telegram_chat_id": message.chat.id
        }

        response = requests.post(f"{NLP_SERVICE_URL}/process", json=nlp_data)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                await message.answer(result["response"])
            else:
                await message.answer(f"Не удалось обработать: {result.get('response', 'неизвестная ошибка')}")
        else:
            await message.answer("Сервис временно недоступен")
    except Exception as e:
        logger.error(f"Error in message_handler: {e}")
        await message.answer("Произошла ошибка при обработке сообщения")


async def main():
    """Главная функция"""
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())