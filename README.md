# BabyFlow - AI дневник развития ребенка

AI-бот в Telegram для автоматического ведения дневника развития ребенка через текстовые сообщения.

## Возможности

- 📝 Запись активностей простыми сообщениями ("уснул", "проснулся", "покормила")
- 🤖 Умная обработка естественного языка на Claude 3.5 Sonnet
- 📊 Статистика за день
- 👨‍👩‍👧 Синхронизация между родителями

## Быстрый старт

### 1. Требования

- Docker Desktop
- Telegram Bot Token (получить у [@BotFather](https://t.me/botfather))
- Anthropic API Key ([получить тут](https://console.anthropic.com/))

### 2. Установка

```bash
# Клонируем репозиторий
git clone https://github.com/yourusername/babyflow.git
cd babyflow

# Создаем .env файл
cp .env.example .env
# Редактируем .env и добавляем свои ключи
```

### 3. Запуск

```bash
# Запускаем все сервисы
docker-compose up

# Или в фоне
docker-compose up -d
```

### 4. Использование

1. Найдите своего бота в Telegram
2. Отправьте `/start`
3. Добавьте ребенка: `/add_child Имя 2024-01-01`
4. Начните записывать: "малыш уснул", "проснулся", "покормила 200мл"

## Архитектура

- **telegram-service** - Telegram бот на aiogram
- **nlp-service** - Мультиагентная система на LangChain + Claude
- **activity-service** - CRUD API для активностей
- **postgres** - База данных

## Команды бота

- `/start` - начать работу
- `/add_child` - добавить ребенка
- `/today` - показать активности за день
- `/help` - справка

## Примеры сообщений

- "уснул в 14:30"
- "проснулся"
- "покормила грудью"
- "выпил 200мл смеси"
- "гуляем в парке"

## Разработка

```bash
# Пересобрать сервис
docker-compose build <service-name>

# Логи
docker-compose logs -f <service-name>

# Остановить
docker-compose down
```

## Лицензия

MIT