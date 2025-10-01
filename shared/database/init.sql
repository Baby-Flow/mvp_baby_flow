-- Создаем таблицы для BabyFlow

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    language VARCHAR(10) DEFAULT 'ru',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Дети
CREATE TABLE IF NOT EXISTS children (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- История диалогов
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
    message_type VARCHAR(10) NOT NULL CHECK (message_type IN ('user', 'bot')),
    raw_text TEXT NOT NULL,
    processed_data JSONB,
    telegram_message_id BIGINT,
    telegram_chat_id BIGINT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Активности: Сон
CREATE TABLE IF NOT EXISTS sleep_activities (
    id SERIAL PRIMARY KEY,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    quality VARCHAR(50),
    location VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Активности: Кормление
CREATE TABLE IF NOT EXISTS feeding_activities (
    id SERIAL PRIMARY KEY,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id),
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    type VARCHAR(50) NOT NULL, -- грудь, смесь, прикорм
    duration_minutes INTEGER,
    amount_ml INTEGER,
    food_name VARCHAR(255),
    side VARCHAR(20), -- левая/правая для ГВ
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Активности: Прогулки
CREATE TABLE IF NOT EXISTS walk_activities (
    id SERIAL PRIMARY KEY,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    weather VARCHAR(100),
    location VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Активности: Подгузники
CREATE TABLE IF NOT EXISTS diaper_activities (
    id SERIAL PRIMARY KEY,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id),
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    type VARCHAR(50) NOT NULL, -- pee, poop, both
    consistency VARCHAR(50), -- для стула: жидкий, нормальный, твердый
    color VARCHAR(50), -- цвет
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Активности: Температура
CREATE TABLE IF NOT EXISTS temperature_activities (
    id SERIAL PRIMARY KEY,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id),
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    temperature DECIMAL(3,1) NOT NULL, -- 36.6
    measurement_type VARCHAR(50), -- подмышка, лоб, ректально
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Активности: Лекарства
CREATE TABLE IF NOT EXISTS medication_activities (
    id SERIAL PRIMARY KEY,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES conversations(id),
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    medication_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100), -- 5мл, 1 таблетка, 2 капли
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группы (для семейных чатов)
CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    telegram_chat_id BIGINT UNIQUE NOT NULL,
    child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Связь пользователей с группами
CREATE TABLE IF NOT EXISTS user_groups (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    PRIMARY KEY (user_id, group_id)
);

-- Индексы для производительности
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_child_id ON conversations(child_id);
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp);

CREATE INDEX idx_sleep_child_id ON sleep_activities(child_id);
CREATE INDEX idx_sleep_start_time ON sleep_activities(start_time);

CREATE INDEX idx_feeding_child_id ON feeding_activities(child_id);
CREATE INDEX idx_feeding_time ON feeding_activities(time);

CREATE INDEX idx_walk_child_id ON walk_activities(child_id);
CREATE INDEX idx_walk_start_time ON walk_activities(start_time);

CREATE INDEX idx_diaper_child_id ON diaper_activities(child_id);
CREATE INDEX idx_diaper_time ON diaper_activities(time);

CREATE INDEX idx_temperature_child_id ON temperature_activities(child_id);
CREATE INDEX idx_temperature_time ON temperature_activities(time);

CREATE INDEX idx_medication_child_id ON medication_activities(child_id);
CREATE INDEX idx_medication_time ON medication_activities(time);

-- Функция для автообновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_children_updated_at BEFORE UPDATE ON children
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sleep_updated_at BEFORE UPDATE ON sleep_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feeding_updated_at BEFORE UPDATE ON feeding_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_walk_updated_at BEFORE UPDATE ON walk_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_diaper_updated_at BEFORE UPDATE ON diaper_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_temperature_updated_at BEFORE UPDATE ON temperature_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medication_updated_at BEFORE UPDATE ON medication_activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();