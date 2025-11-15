# Техническая реализация меню и кнопок

## 🎯 Цель
Улучшить UX Telegram бота, добавив интуитивное меню с кнопками для частых действий.

---

## 📱 1. ГЛАВНОЕ МЕНЮ (Reply Keyboard)

### Реализация в aiogram 3.x

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    """Главное меню с 4 основными кнопками"""
    keyboard = [
        [
            KeyboardButton(text="📝 Сегодня"),
            KeyboardButton(text="📊 Статистика")
        ],
        [
            KeyboardButton(text="⚡ Быстрые действия"),
            KeyboardButton(text="❓ Помощь")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,  # Адаптировать размер
        one_time_keyboard=False,  # Не скрывать после нажатия
        input_field_placeholder="Напишите что происходит..."  # Подсказка в поле ввода
    )
```

### Использование при /start

```python
@dp.message(CommandStart())
async def start_handler(message: Message):
    # ... существующий код регистрации ...

    await message.answer(
        f"👋 Привет, {first_name}!\n\n"
        "Я Алиса - помогу вести дневник развития вашего малыша.\n"
        "Просто пишите мне обычными словами, что происходит!",
        reply_markup=get_main_menu()  # ← Добавить меню
    )
```

---

## ⚡ 2. БЫСТРЫЕ ДЕЙСТВИЯ (Inline Keyboard)

### Реализация

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

# Callback data класс для типизации
class QuickAction(CallbackData, prefix="quick"):
    action: str  # sleep_start, sleep_end, feed, walk, diaper_poop, diaper_pee

def get_quick_actions_keyboard():
    """Inline клавиатура с быстрыми действиями"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="😴 Уснул",
                callback_data=QuickAction(action="sleep_start").pack()
            ),
            InlineKeyboardButton(
                text="👁️ Проснулся",
                callback_data=QuickAction(action="sleep_end").pack()
            ),
            InlineKeyboardButton(
                text="🍼 Покормила",
                callback_data=QuickAction(action="feed").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="🚶 Прогулка",
                callback_data=QuickAction(action="walk").pack()
            ),
            InlineKeyboardButton(
                text="💩 Покакал",
                callback_data=QuickAction(action="diaper_poop").pack()
            ),
            InlineKeyboardButton(
                text="💧 Пописал",
                callback_data=QuickAction(action="diaper_pee").pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
```

### Обработчик нажатий кнопок

```python
@dp.callback_query(QuickAction.filter())
async def quick_action_handler(
    callback: CallbackQuery,
    callback_data: QuickAction
):
    """Обработка быстрых действий"""
    telegram_id = callback.from_user.id

    # Проверяем авторизацию
    if telegram_id not in user_mapping:
        await callback.answer("Сначала выполните /start", show_alert=True)
        return

    child_id = user_mapping[telegram_id]["child_id"]
    action = callback_data.action

    # Формируем сообщение для NLP сервиса
    action_messages = {
        "sleep_start": "уснул сейчас",
        "sleep_end": "проснулся сейчас",
        "feed": "покормила сейчас",
        "walk": "начали прогулку",
        "diaper_poop": "покакал сейчас",
        "diaper_pee": "пописал сейчас"
    }

    message_text = action_messages.get(action, "")

    # Отправляем в NLP
    try:
        nlp_data = {
            "message": message_text,
            "child_id": child_id,
            "user_id": user_mapping[telegram_id]["user_id"],
            "telegram_chat_id": callback.message.chat.id
        }

        response = requests.post(f"{NLP_SERVICE_URL}/process", json=nlp_data)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                await callback.message.answer(result["response"])
                await callback.answer("✅ Записано!")
            else:
                await callback.answer("Ошибка записи", show_alert=True)
        else:
            await callback.answer("Сервис недоступен", show_alert=True)

    except Exception as e:
        logger.error(f"Error in quick_action: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
```

---

## 📝 3. ОБРАБОТЧИКИ КНОПОК МЕНЮ

### "📝 Сегодня" - дублирует /today

```python
@dp.message(lambda message: message.text == "📝 Сегодня")
async def menu_today_handler(message: Message):
    """Обработка кнопки 'Сегодня'"""
    await today_handler(message)  # Вызываем существующий обработчик
```

### "📊 Статистика" - улучшенная версия

```python
def get_stats_period_keyboard():
    """Выбор периода для статистики"""
    keyboard = [
        [
            InlineKeyboardButton(text="📅 За неделю", callback_data="stats_week"),
            InlineKeyboardButton(text="📅 За месяц", callback_data="stats_month")
        ],
        [
            InlineKeyboardButton(text="📈 Графики", callback_data="stats_charts")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(lambda message: message.text == "📊 Статистика")
async def menu_stats_handler(message: Message):
    """Обработка кнопки 'Статистика'"""
    await message.answer(
        "📊 Выберите период для статистики:",
        reply_markup=get_stats_period_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("stats_"))
async def stats_period_handler(callback: CallbackQuery):
    """Обработка выбора периода"""
    telegram_id = callback.from_user.id

    if telegram_id not in user_mapping:
        await callback.answer("Сначала добавьте малыша", show_alert=True)
        return

    child_id = user_mapping[telegram_id]["child_id"]

    if callback.data == "stats_week":
        # Показать статистику за неделю
        await show_stats(callback.message, child_id, days=7)
        await callback.answer()

    elif callback.data == "stats_month":
        # Показать статистику за месяц
        await show_stats(callback.message, child_id, days=30)
        await callback.answer()

    elif callback.data == "stats_charts":
        # Показать графики
        await show_charts(callback.message, child_id)
        await callback.answer("📈 Генерирую графики...")

async def show_stats(message: Message, child_id: int, days: int):
    """Показать статистику за период"""
    try:
        response = requests.get(
            f"{ACTIVITY_SERVICE_URL}/analytics/child/{child_id}/stats?days={days}"
        )
        if response.status_code != 200:
            await message.answer("Не могу получить статистику 🙏")
            return

        data = response.json()
        period_text = "неделю" if days == 7 else "месяц"
        text = f"📊 *Статистика за {period_text}:*\n\n"

        # ... форматирование данных (как в текущем stats_handler) ...

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in show_stats: {e}")
        await message.answer("Что-то пошло не так 😔")
```

### "⚡ Быстрые действия" - показывает inline кнопки

```python
@dp.message(lambda message: message.text == "⚡ Быстрые действия")
async def menu_quick_actions_handler(message: Message):
    """Обработка кнопки 'Быстрые действия'"""
    await message.answer(
        "⚡ Выберите действие:",
        reply_markup=get_quick_actions_keyboard()
    )
```

### "❓ Помощь" - дублирует /help

```python
@dp.message(lambda message: message.text == "❓ Помощь")
async def menu_help_handler(message: Message):
    """Обработка кнопки 'Помощь'"""
    await help_handler(message)
```

---

## 🔄 4. ОБНОВЛЕННЫЙ /today С INLINE КНОПКАМИ

### Добавить действия после просмотра

```python
def get_today_actions_keyboard():
    """Действия после просмотра сегодняшних активностей"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_today"),
            InlineKeyboardButton(text="📈 Графики", callback_data="today_charts")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("today"))
async def today_handler(message: Message):
    """Показать активности за сегодня"""
    # ... существующий код формирования текста ...

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_today_actions_keyboard()  # ← Добавить кнопки
    )

@dp.callback_query(lambda c: c.data == "refresh_today")
async def refresh_today_handler(callback: CallbackQuery):
    """Обновить данные за сегодня"""
    await callback.message.delete()  # Удалить старое сообщение
    await today_handler(callback.message)  # Показать новое
    await callback.answer("✅ Обновлено!")
```

---

## 🎨 5. УЛУЧШЕНИЕ ВИЗУАЛЬНОГО ОФОРМЛЕНИЯ

### Эмодзи для всех типов активностей

```python
# Константы для консистентности
ACTIVITY_EMOJIS = {
    "sleep": "😴",
    "feeding": "🍼",
    "walk": "🚶",
    "diaper_poop": "💩",
    "diaper_pee": "💧",
    "diaper": "🚼",
    "temperature": "🌡️",
    "medication": "💊",
    "mood_happy": "😊",
    "mood_sad": "😢",
    "mood_angry": "😤",
    "mood_calm": "😌"
}

# Использование
def format_activity_response(activity_type: str, details: str) -> str:
    """Форматировать ответ с эмодзи"""
    emoji = ACTIVITY_EMOJIS.get(activity_type, "✅")
    return f"{emoji} {details}"
```

### Улучшенное форматирование времени

```python
from datetime import datetime, timedelta
import pytz

def format_relative_time(dt: datetime) -> str:
    """Форматирует время относительно текущего момента"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)

    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    dt_moscow = dt.astimezone(moscow_tz)
    diff = now - dt_moscow

    if diff < timedelta(minutes=1):
        return "только что"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} мин назад"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} ч назад"
    else:
        return dt_moscow.strftime("%d.%m в %H:%M")

# Использование
# "😴 Малыш уснул только что"
# "🍼 Покормили 2 ч назад"
```

---

## 📋 6. ПЛАН ВНЕДРЕНИЯ

### Шаг 1: Базовое меню (1-2 часа)
```python
# В bot.py добавить:
1. Функцию get_main_menu()
2. Добавить reply_markup=get_main_menu() в start_handler
3. Обработчики для 4 кнопок меню
4. Протестировать
```

### Шаг 2: Быстрые действия (2-3 часа)
```python
# В bot.py добавить:
1. Класс QuickAction(CallbackData)
2. Функцию get_quick_actions_keyboard()
3. Обработчик quick_action_handler
4. Протестировать все 6 действий
```

### Шаг 3: Inline кнопки в статистике (1-2 часа)
```python
# В bot.py добавить:
1. Функцию get_stats_period_keyboard()
2. Обработчик stats_period_handler
3. Функцию show_stats() для переиспользования
4. Протестировать
```

### Шаг 4: Полировка (1 час)
```python
# В bot.py улучшить:
1. Добавить ACTIVITY_EMOJIS константы
2. Улучшить форматирование всех ответов
3. Добавить inline кнопки в /today
4. Финальное тестирование
```

**Общее время: 5-8 часов разработки**

---

## 🧪 7. ТЕСТИРОВАНИЕ

### Сценарии для тестирования

```
1. Первый запуск
   - /start → Видно меню с 4 кнопками ✓
   - Плейсхолдер в поле ввода ✓

2. Быстрые действия
   - "⚡ Быстрые действия" → Показались inline кнопки ✓
   - Нажать "😴 Уснул" → Записалось в БД ✓
   - Нажать "👁️ Проснулся" → Записалось правильное время ✓

3. Просмотр сегодня
   - "📝 Сегодня" → Показался список ✓
   - Нажать "🔄 Обновить" → Обновилось ✓

4. Статистика
   - "📊 Статистика" → Показался выбор периода ✓
   - Выбрать "За неделю" → Показалась статистика ✓
   - Нажать "📈 Графики" → Получил 3 графика ✓

5. Обычные сообщения
   - Написать "уснул" → Записалось ✓
   - Меню осталось видимым ✓
```

---

## 🔧 8. ПОЛНЫЙ КОД ДЛЯ ВНЕДРЕНИЯ

### Добавить в начало bot.py:

```python
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters.callback_data import CallbackData

# Callback data
class QuickAction(CallbackData, prefix="quick"):
    action: str

# Константы
ACTIVITY_EMOJIS = {
    "sleep_start": "😴",
    "sleep_end": "👁️",
    "feed": "🍼",
    "walk": "🚶",
    "diaper_poop": "💩",
    "diaper_pee": "💧",
}

# Функции клавиатур
def get_main_menu():
    keyboard = [
        [KeyboardButton(text="📝 Сегодня"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="⚡ Быстрые действия"), KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Напишите что происходит..."
    )

def get_quick_actions_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="😴 Уснул", callback_data=QuickAction(action="sleep_start").pack()),
            InlineKeyboardButton(text="👁️ Проснулся", callback_data=QuickAction(action="sleep_end").pack()),
            InlineKeyboardButton(text="🍼 Покормила", callback_data=QuickAction(action="feed").pack())
        ],
        [
            InlineKeyboardButton(text="🚶 Прогулка", callback_data=QuickAction(action="walk").pack()),
            InlineKeyboardButton(text="💩 Покакал", callback_data=QuickAction(action="diaper_poop").pack()),
            InlineKeyboardButton(text="💧 Пописал", callback_data=QuickAction(action="diaper_pee").pack())
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_stats_period_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="📅 За неделю", callback_data="stats_week"),
            InlineKeyboardButton(text="📅 За месяц", callback_data="stats_month")
        ],
        [InlineKeyboardButton(text="📈 Графики", callback_data="stats_charts")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
```

### Обновить start_handler:

```python
@dp.message(CommandStart())
async def start_handler(message: Message):
    # ... существующий код ...

    # В конце, вместо простого message.answer:
    await message.answer(
        text,  # Ваш текст приветствия
        reply_markup=get_main_menu()  # ← ДОБАВИТЬ ЭТО
    )
```

### Добавить новые обработчики:

```python
# Обработчики кнопок меню
@dp.message(lambda m: m.text == "📝 Сегодня")
async def menu_today(m: Message):
    await today_handler(m)

@dp.message(lambda m: m.text == "📊 Статистика")
async def menu_stats(m: Message):
    await m.answer("📊 Выберите период:", reply_markup=get_stats_period_keyboard())

@dp.message(lambda m: m.text == "⚡ Быстрые действия")
async def menu_quick(m: Message):
    await m.answer("⚡ Выберите действие:", reply_markup=get_quick_actions_keyboard())

@dp.message(lambda m: m.text == "❓ Помощь")
async def menu_help(m: Message):
    await help_handler(m)

# Обработчик быстрых действий
@dp.callback_query(QuickAction.filter())
async def quick_action_handler(callback: CallbackQuery, callback_data: QuickAction):
    telegram_id = callback.from_user.id

    if telegram_id not in user_mapping:
        await callback.answer("Сначала выполните /start", show_alert=True)
        return

    child_id = user_mapping[telegram_id]["child_id"]

    action_messages = {
        "sleep_start": "уснул сейчас",
        "sleep_end": "проснулся сейчас",
        "feed": "покормила сейчас",
        "walk": "начали прогулку",
        "diaper_poop": "покакал сейчас",
        "diaper_pee": "пописал сейчас"
    }

    message_text = action_messages.get(callback_data.action, "")

    try:
        nlp_data = {
            "message": message_text,
            "child_id": child_id,
            "user_id": user_mapping[telegram_id]["user_id"],
            "telegram_chat_id": callback.message.chat.id
        }

        response = requests.post(f"{NLP_SERVICE_URL}/process", json=nlp_data)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                await callback.message.answer(result["response"])
                await callback.answer("✅ Записано!")
            else:
                await callback.answer("Ошибка", show_alert=True)
        else:
            await callback.answer("Сервис недоступен", show_alert=True)

    except Exception as e:
        logger.error(f"Error in quick_action: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

# Обработчик статистики
@dp.callback_query(lambda c: c.data.startswith("stats_"))
async def stats_period_handler(callback: CallbackQuery):
    telegram_id = callback.from_user.id

    if telegram_id not in user_mapping:
        await callback.answer("Сначала добавьте малыша", show_alert=True)
        return

    child_id = user_mapping[telegram_id]["child_id"]

    if callback.data == "stats_week":
        days = 7
    elif callback.data == "stats_month":
        days = 30
    elif callback.data == "stats_charts":
        await chart_handler(callback.message)
        await callback.answer("📈 Генерирую графики...")
        return
    else:
        return

    try:
        response = requests.get(
            f"{ACTIVITY_SERVICE_URL}/analytics/child/{child_id}/stats?days={days}"
        )
        if response.status_code != 200:
            await callback.answer("Ошибка получения данных", show_alert=True)
            return

        data = response.json()
        period_text = "неделю" if days == 7 else "месяц"
        text = f"📊 *Статистика за {period_text}:*\n\n"

        # ... форматирование (копировать из stats_handler) ...

        await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in stats_period: {e}")
        await callback.answer("Ошибка", show_alert=True)
```

---

## ✅ ЧЕКЛИСТ ВНЕДРЕНИЯ

- [ ] Скопировать импорты в начало bot.py
- [ ] Добавить классы и константы
- [ ] Добавить функции клавиатур
- [ ] Обновить start_handler с меню
- [ ] Добавить обработчики кнопок меню
- [ ] Добавить обработчик быстрых действий
- [ ] Добавить обработчик статистики
- [ ] Протестировать все сценарии
- [ ] Закоммитить изменения

**После внедрения бот станет в 3-5 раз удобнее!** 🚀
