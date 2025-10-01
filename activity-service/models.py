from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://babyflow:babyflow123@localhost:5432/babyflow")

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    timezone = Column(String(50), default="Europe/Moscow")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    message_type = Column(String(10), nullable=False)
    raw_text = Column(Text, nullable=False)
    telegram_message_id = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class SleepActivity(Base):
    __tablename__ = "sleep_activities"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    quality = Column(String(50))
    location = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FeedingActivity(Base):
    __tablename__ = "feeding_activities"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    time = Column(DateTime(timezone=True), nullable=False)
    type = Column(String(50), nullable=False)
    duration_minutes = Column(Integer)
    amount_ml = Column(Integer)
    food_name = Column(String(255))
    side = Column(String(20))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WalkActivity(Base):
    __tablename__ = "walk_activities"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    weather = Column(String(100))
    location = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DiaperActivity(Base):
    __tablename__ = "diaper_activities"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    time = Column(DateTime(timezone=True), nullable=False)
    type = Column(String(50), nullable=False)
    consistency = Column(String(50))
    color = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()