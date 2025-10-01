import os
import asyncio
import logging
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from chart_generator import create_sleep_chart, create_feeding_chart, create_activity_summary_chart

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
                "• гуляем в парке\n"
                "• вчера вечером плохо спал\n"
                "• температура была 37.5 позавчера\n\n"
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
        if response.status_code != 200:
            await message.answer("Не могу получить данные, попробуйте позже 🙏")
            return

        data = response.json()
        text = "📊 *Сегодня у малыша:*\n\n"

        # Сон
        if data.get("sleep"):
            text += "😴 *Сон:*\n"
            moscow_tz = pytz.timezone('Europe/Moscow')
            for sleep in data["sleep"]:
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

        # Температура
        if data.get("temperatures"):
            text += "\n🌡️ *Температура:*\n"
            moscow_tz = pytz.timezone('Europe/Moscow')
            for temp in data["temperatures"]:
                time_dt = datetime.fromisoformat(temp["time"].replace('Z', '+00:00'))
                time_moscow = time_dt.astimezone(moscow_tz)
                time = time_moscow.strftime("%H:%M")

                text += f"• {time} - {temp['temperature']}°C"
                if temp.get("measurement_type"):
                    text += f" ({temp['measurement_type']})"
                text += "\n"

        # Лекарства
        if data.get("medications"):
            text += "\n💊 *Лекарства:*\n"
            moscow_tz = pytz.timezone('Europe/Moscow')
            for med in data["medications"]:
                time_dt = datetime.fromisoformat(med["time"].replace('Z', '+00:00'))
                time_moscow = time_dt.astimezone(moscow_tz)
                time = time_moscow.strftime("%H:%M")

                text += f"• {time} - {med['medication_name']}"
                if med.get("dosage"):
                    text += f" ({med['dosage']})"
                text += "\n"

        # Настроение
        if data.get("moods"):
            text += "\n😊 *Настроение:*\n"
            moscow_tz = pytz.timezone('Europe/Moscow')
            mood_emojis = {
                "веселое": "😄",
                "спокойное": "😌",
                "капризное": "😤",
                "плачет": "😢",
                "хорошее": "😊",
                "плохое": "😔"
            }
            for mood_entry in data["moods"]:
                time_dt = datetime.fromisoformat(mood_entry["time"].replace('Z', '+00:00'))
                time_moscow = time_dt.astimezone(moscow_tz)
                time = time_moscow.strftime("%H:%M")

                mood = mood_entry["mood"]
                emoji = mood_emojis.get(mood.lower(), "😊")
                text += f"• {time} - {emoji} {mood}"
                if mood_entry.get("notes"):
                    text += f" ({mood_entry['notes']})"
                text += "\n"

        # Проверяем есть ли вообще записи
        if not any([data.get("sleep"), data.get("feeding"), data.get("walks"),
                    data.get("diapers"), data.get("temperatures"),
                    data.get("medications"), data.get("moods")]):
            text = "Пока нет записей за сегодня. Расскажите, что делает малыш? 😊"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in today_handler: {e}")
        await message.answer("Что-то пошло не так 😔")


@dp.message(Command("stats"))
async def stats_handler(message: Message):
    """Показать статистику за неделю"""
    telegram_id = message.from_user.id

    if telegram_id not in user_mapping:
        await message.answer("Сначала добавьте малыша через /add_child")
        return

    child_id = user_mapping[telegram_id]["child_id"]

    try:
        response = requests.get(f"{ACTIVITY_SERVICE_URL}/analytics/child/{child_id}/stats?days=7")
        if response.status_code != 200:
            await message.answer("Не могу получить статистику, попробуйте позже 🙏")
            return

        data = response.json()
        text = "📊 *Статистика за неделю:*\n\n"

        # Сон
        sleep = data["sleep"]
        text += f"😴 *Сон:*\n"
        text += f"• Всего: {sleep['count']} раз\n"
        text += f"• Средняя длительность: {sleep['avg_duration_hours']} ч\n"
        text += f"• Общее время: {sleep['total_duration_hours']} ч\n\n"

        # Кормление
        feeding = data["feeding"]
        text += f"🍼 *Кормление:*\n"
        text += f"• Всего: {feeding['count']} раз\n"
        if feeding['avg_amount_ml'] > 0:
            text += f"• Средний объем: {int(feeding['avg_amount_ml'])} мл\n"
            text += f"• Общий объем: {int(feeding['total_amount_ml'])} мл\n"
        if feeding['by_type']:
            text += "• По типам:\n"
            for ftype, count in feeding['by_type'].items():
                text += f"  - {ftype}: {count}\n"
        text += "\n"

        # Прогулки
        walks = data["walks"]
        if walks['count'] > 0:
            text += f"🚶 *Прогулки:*\n"
            text += f"• Всего: {walks['count']} раз\n"
            text += f"• Средняя длительность: {walks['avg_duration_hours']} ч\n\n"

        # Подгузники
        diapers = data["diapers"]
        if diapers['count'] > 0:
            text += f"🚼 *Подгузники:*\n"
            text += f"• Всего: {diapers['count']} раз\n"
            if diapers['by_type']:
                for dtype, count in diapers['by_type'].items():
                    emoji = "💩" if dtype == "poop" else "💧" if dtype == "pee" else "🚼"
                    text += f"• {emoji} {dtype}: {count}\n"
            text += "\n"

        # Температура
        temp = data["temperature"]
        if temp['count'] > 0:
            text += f"🌡️ *Температура:*\n"
            text += f"• Измерений: {temp['count']}\n"
            text += f"• Средняя: {temp['avg']:.1f}°C\n"
            text += f"• Минимум: {temp['min']:.1f}°C\n"
            text += f"• Максимум: {temp['max']:.1f}°C\n"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in stats_handler: {e}")
        await message.answer("Что-то пошло не так 😔")


@dp.message(Command("week"))
async def week_handler(message: Message):
    """Показать активности за неделю"""
    telegram_id = message.from_user.id

    if telegram_id not in user_mapping:
        await message.answer("Сначала добавьте малыша через /add_child")
        return

    child_id = user_mapping[telegram_id]["child_id"]

    try:
        response = requests.get(f"{ACTIVITY_SERVICE_URL}/analytics/child/{child_id}/daily?days=7")
        if response.status_code != 200:
            await message.answer("Не могу получить данные, попробуйте позже 🙏")
            return

        daily_data = response.json()
        text = "📅 *Активности за неделю:*\n\n"

        for day in daily_data:
            from datetime import datetime
            date_obj = datetime.fromisoformat(day['date'])
            day_name = date_obj.strftime("%d.%m (%a)")

            text += f"*{day_name}:*\n"
            text += f"  😴 Сон: {day['sleep']['total_hours']}ч ({day['sleep']['count']} раз)\n"
            text += f"  🍼 Кормлений: {day['feeding']['count']}"
            if day['feeding']['total_ml']:
                text += f" ({day['feeding']['total_ml']}мл)"
            text += f"\n"
            text += f"  🚼 Подгузников: {day['diapers']['count']}\n\n"

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in week_handler: {e}")
        await message.answer("Что-то пошло не так 😔")


@dp.message(Command("chart"))
async def chart_handler(message: Message):
    """Отправить графики статистики"""
    telegram_id = message.from_user.id

    if telegram_id not in user_mapping:
        await message.answer("Сначала добавьте малыша через /add_child")
        return

    child_id = user_mapping[telegram_id]["child_id"]

    try:
        # Получаем данные
        stats_response = requests.get(f"{ACTIVITY_SERVICE_URL}/analytics/child/{child_id}/stats?days=7")
        daily_response = requests.get(f"{ACTIVITY_SERVICE_URL}/analytics/child/{child_id}/daily?days=7")

        if stats_response.status_code != 200 or daily_response.status_code != 200:
            await message.answer("Не могу получить данные для графиков 😔")
            return

        stats_data = stats_response.json()
        daily_data = daily_response.json()

        await message.answer("📈 Генерирую графики статистики...")

        # Создаем графики
        import tempfile
        import os

        # График сна
        sleep_chart = create_sleep_chart(daily_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(sleep_chart)
            sleep_chart_path = tmp_file.name

        # График кормлений
        feeding_chart = create_feeding_chart(daily_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(feeding_chart)
            feeding_chart_path = tmp_file.name

        # Сводная статистика
        summary_chart = create_activity_summary_chart(stats_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(summary_chart)
            summary_chart_path = tmp_file.name

        # Отправляем графики
        await bot.send_photo(
            message.chat.id,
            FSInputFile(sleep_chart_path),
            caption="😴 График сна за неделю"
        )

        await bot.send_photo(
            message.chat.id,
            FSInputFile(feeding_chart_path),
            caption="🍼 График кормлений за неделю"
        )

        await bot.send_photo(
            message.chat.id,
            FSInputFile(summary_chart_path),
            caption="📊 Сводная статистика за неделю"
        )

        # Удаляем временные файлы
        os.unlink(sleep_chart_path)
        os.unlink(feeding_chart_path)
        os.unlink(summary_chart_path)

    except Exception as e:
        logger.error(f"Error in chart_handler: {e}")
        await message.answer("Не удалось создать графики 😔")


@dp.message(Command("help"))
async def help_handler(message: Message):
    """Помощь"""
    help_text = """
*Я Алиса, ваша помощница* 🤱

*Команды:*
/start - начать работу
/add_child - добавить малыша
/today - что было сегодня
/stats - статистика за неделю
/week - активности за неделю
/chart - графики статистики
/help - эта справка

*Просто пишите что происходит:*
• "уснул" - запишу начало сна
• "проснулся" - отмечу пробуждение
• "покормила" - запишу кормление
• "гуляем" - отмечу прогулку
• "покакал" - запишу смену подгузника
• "пописал" - отмечу мокрый подгузник
• "температура 37.2" - запишу температуру
• "дали нурофен 5мл" - запишу лекарство
• "веселый" или "капризничает" - отмечу настроение

*Примеры сообщений:*
• спит с 14:30
• только что проснулся
• покормила грудью
• выпил 200мл смеси
• гуляем в парке
• вчера вечером плохо спал
• позавчера температура была 37.5
• покормила через час после сна
• в обед покакал

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