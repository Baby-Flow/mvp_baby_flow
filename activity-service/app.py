from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel
import pytz
import logging
from models import get_db, User, Child, SleepActivity, FeedingActivity, WalkActivity, DiaperActivity, \
    TemperatureActivity, MedicationActivity, MoodActivity, Conversation

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="BabyFlow Activity Service")


# Pydantic модели для API
class SleepCreate(BaseModel):
    child_id: int
    start_time: Union[datetime, str]
    end_time: Optional[Union[datetime, str]] = None
    duration_minutes: Optional[int] = None
    quality: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class FeedingCreate(BaseModel):
    child_id: int
    time: Union[datetime, str]
    type: str
    duration_minutes: Optional[int] = None
    amount_ml: Optional[int] = None
    food_name: Optional[str] = None
    side: Optional[str] = None
    notes: Optional[str] = None


class WalkCreate(BaseModel):
    child_id: int
    start_time: Union[datetime, str]
    end_time: Optional[Union[datetime, str]] = None
    duration_minutes: Optional[int] = None
    weather: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class DiaperCreate(BaseModel):
    child_id: int
    time: Union[datetime, str]
    type: str  # pee, poop, both
    consistency: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


class TemperatureCreate(BaseModel):
    child_id: int
    time: Union[datetime, str]
    temperature: float
    measurement_type: Optional[str] = None
    notes: Optional[str] = None


class MedicationCreate(BaseModel):
    child_id: int
    time: Union[datetime, str]
    medication_name: str
    dosage: Optional[str] = None
    notes: Optional[str] = None


class MoodCreate(BaseModel):
    child_id: int
    time: Union[datetime, str]
    mood: str
    intensity: Optional[int] = None
    notes: Optional[str] = None


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class ChildCreate(BaseModel):
    user_id: int
    name: str
    birth_date: str
    gender: Optional[str] = None


@app.get("/")
def root():
    return {"service": "Activity Service", "status": "running"}


# User endpoints
@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating user with telegram_id={user.telegram_id}")
    db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if db_user:
        logger.info(f"User with telegram_id={user.telegram_id} already exists")
        return db_user

    new_user = User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Successfully created user id={new_user.id}, telegram_id={new_user.telegram_id}")
    return new_user


@app.get("/users/telegram/{telegram_id}")
def get_user_by_telegram(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Child endpoints
@app.post("/children/")
def create_child(child: ChildCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating child: name={child.name}, user_id={child.user_id}")
    new_child = Child(
        user_id=child.user_id,
        name=child.name,
        birth_date=datetime.strptime(child.birth_date, "%Y-%m-%d").date(),
        gender=child.gender
    )
    db.add(new_child)
    db.commit()
    db.refresh(new_child)
    logger.info(f"Successfully created child id={new_child.id}, name={new_child.name}")
    return new_child


@app.get("/children/user/{user_id}")
def get_children_by_user(user_id: int, db: Session = Depends(get_db)):
    children = db.query(Child).filter(Child.user_id == user_id).all()
    return children


# Sleep endpoints
@app.post("/activities/sleep/")
def create_sleep(sleep: SleepCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating sleep activity for child_id={sleep.child_id}")
    # Если есть end_time, вычисляем duration
    if sleep.end_time and sleep.start_time:
        duration = int((sleep.end_time - sleep.start_time).total_seconds() / 60)
        sleep.duration_minutes = duration

    # Создаем объект для БД
    sleep_data = sleep.dict()

    # Обрабатываем datetime если они строки
    if isinstance(sleep_data.get('start_time'), str):
        sleep_data['start_time'] = datetime.fromisoformat(sleep_data['start_time'].replace('Z', '+00:00'))
    if isinstance(sleep_data.get('end_time'), str):
        sleep_data['end_time'] = datetime.fromisoformat(sleep_data['end_time'].replace('Z', '+00:00'))

    new_sleep = SleepActivity(**sleep_data)
    db.add(new_sleep)
    db.commit()
    db.refresh(new_sleep)
    logger.info(f"Created sleep activity id={new_sleep.id} for child_id={new_sleep.child_id}")
    return new_sleep


@app.get("/activities/sleep/{child_id}/open")
def get_open_sleep(child_id: int, db: Session = Depends(get_db)):
    sleep = db.query(SleepActivity).filter(
        SleepActivity.child_id == child_id,
        SleepActivity.end_time == None
    ).first()
    return sleep


@app.put("/activities/sleep/{sleep_id}/end")
def end_sleep(sleep_id: int, end_time: str, db: Session = Depends(get_db)):
    logger.info(f"Ending sleep activity id={sleep_id}")
    sleep = db.query(SleepActivity).filter(SleepActivity.id == sleep_id).first()
    if not sleep:
        logger.warning(f"Sleep activity id={sleep_id} not found")
        raise HTTPException(status_code=404, detail="Sleep not found")

    # Парсим строку времени в datetime
    try:
        end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00').replace(' ', 'T'))
    except:
        end_datetime = datetime.now()

    sleep.end_time = end_datetime

    # Вычисляем длительность
    if hasattr(sleep.start_time, 'timestamp'):
        duration = int((end_datetime.timestamp() - sleep.start_time.timestamp()) / 60)
    else:
        duration = int((end_datetime - sleep.start_time).total_seconds() / 60)

    sleep.duration_minutes = duration

    db.commit()
    db.refresh(sleep)
    logger.info(f"Ended sleep activity id={sleep_id}, duration={duration} minutes")
    return sleep


# Feeding endpoints
@app.post("/activities/feeding/")
def create_feeding(feeding: FeedingCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating feeding activity for child_id={feeding.child_id}, type={feeding.type}")
    feeding_data = feeding.dict()

    # Обрабатываем datetime если строка
    if isinstance(feeding_data.get('time'), str):
        feeding_data['time'] = datetime.fromisoformat(feeding_data['time'].replace('Z', '+00:00'))

    new_feeding = FeedingActivity(**feeding_data)
    db.add(new_feeding)
    db.commit()
    db.refresh(new_feeding)
    logger.info(f"Created feeding activity id={new_feeding.id} for child_id={new_feeding.child_id}")
    return new_feeding


# Walk endpoints
@app.post("/activities/walk/")
def create_walk(walk: WalkCreate, db: Session = Depends(get_db)):
    walk_data = walk.dict()

    # Обрабатываем datetime если строки
    if isinstance(walk_data.get('start_time'), str):
        walk_data['start_time'] = datetime.fromisoformat(walk_data['start_time'].replace('Z', '+00:00'))
    if isinstance(walk_data.get('end_time'), str):
        walk_data['end_time'] = datetime.fromisoformat(walk_data['end_time'].replace('Z', '+00:00'))

    if walk_data.get('end_time') and walk_data.get('start_time'):
        duration = int((walk_data['end_time'] - walk_data['start_time']).total_seconds() / 60)
        walk_data['duration_minutes'] = duration

    new_walk = WalkActivity(**walk_data)
    db.add(new_walk)
    db.commit()
    db.refresh(new_walk)
    return new_walk


# Diaper endpoints
@app.post("/activities/diaper/")
def create_diaper(diaper: DiaperCreate, db: Session = Depends(get_db)):
    diaper_data = diaper.dict()

    # Обрабатываем datetime если строка
    if isinstance(diaper_data.get('time'), str):
        diaper_data['time'] = datetime.fromisoformat(diaper_data['time'].replace('Z', '+00:00'))

    new_diaper = DiaperActivity(**diaper_data)
    db.add(new_diaper)
    db.commit()
    db.refresh(new_diaper)
    return new_diaper


# Temperature endpoints
@app.post("/activities/temperature/")
def create_temperature(temp: TemperatureCreate, db: Session = Depends(get_db)):
    temp_data = temp.dict()

    # Обрабатываем datetime если строка
    if isinstance(temp_data.get('time'), str):
        temp_data['time'] = datetime.fromisoformat(temp_data['time'].replace('Z', '+00:00'))

    new_temp = TemperatureActivity(**temp_data)
    db.add(new_temp)
    db.commit()
    db.refresh(new_temp)
    return new_temp


# Medication endpoints
@app.post("/activities/medication/")
def create_medication(med: MedicationCreate, db: Session = Depends(get_db)):
    med_data = med.dict()

    # Обрабатываем datetime если строка
    if isinstance(med_data.get('time'), str):
        med_data['time'] = datetime.fromisoformat(med_data['time'].replace('Z', '+00:00'))

    new_med = MedicationActivity(**med_data)
    db.add(new_med)
    db.commit()
    db.refresh(new_med)
    return new_med


# Mood endpoints
@app.post("/activities/mood/")
def create_mood(mood: MoodCreate, db: Session = Depends(get_db)):
    mood_data = mood.dict()

    # Обрабатываем datetime если строка
    if isinstance(mood_data.get('time'), str):
        mood_data['time'] = datetime.fromisoformat(mood_data['time'].replace('Z', '+00:00'))

    new_mood = MoodActivity(**mood_data)
    db.add(new_mood)
    db.commit()
    db.refresh(new_mood)
    return new_mood


# Get all activities for a child
@app.get("/activities/child/{child_id}")
def get_child_activities(child_id: int, db: Session = Depends(get_db)):
    sleep = db.query(SleepActivity).filter(SleepActivity.child_id == child_id).all()
    feeding = db.query(FeedingActivity).filter(FeedingActivity.child_id == child_id).all()
    walks = db.query(WalkActivity).filter(WalkActivity.child_id == child_id).all()
    diapers = db.query(DiaperActivity).filter(DiaperActivity.child_id == child_id).all()
    temperatures = db.query(TemperatureActivity).filter(TemperatureActivity.child_id == child_id).all()
    medications = db.query(MedicationActivity).filter(MedicationActivity.child_id == child_id).all()
    moods = db.query(MoodActivity).filter(MoodActivity.child_id == child_id).all()

    return {
        "sleep": sleep,
        "feeding": feeding,
        "walks": walks,
        "diapers": diapers,
        "temperatures": temperatures,
        "medications": medications,
        "moods": moods
    }


@app.get("/activities/child/{child_id}/today")
def get_today_activities(child_id: int, db: Session = Depends(get_db)):
    from datetime import timezone
    import pytz

    moscow_tz = pytz.timezone('Europe/Moscow')
    today_moscow = datetime.now(moscow_tz).date()
    today_start = moscow_tz.localize(datetime.combine(today_moscow, datetime.min.time()))

    sleep = db.query(SleepActivity).filter(
        SleepActivity.child_id == child_id,
        SleepActivity.start_time >= today_start
    ).all()

    feeding = db.query(FeedingActivity).filter(
        FeedingActivity.child_id == child_id,
        FeedingActivity.time >= today_start
    ).all()

    walks = db.query(WalkActivity).filter(
        WalkActivity.child_id == child_id,
        WalkActivity.start_time >= today_start
    ).all()

    diapers = db.query(DiaperActivity).filter(
        DiaperActivity.child_id == child_id,
        DiaperActivity.time >= today_start
    ).all()

    temperatures = db.query(TemperatureActivity).filter(
        TemperatureActivity.child_id == child_id,
        TemperatureActivity.time >= today_start
    ).all()

    medications = db.query(MedicationActivity).filter(
        MedicationActivity.child_id == child_id,
        MedicationActivity.time >= today_start
    ).all()

    moods = db.query(MoodActivity).filter(
        MoodActivity.child_id == child_id,
        MoodActivity.time >= today_start
    ).all()

    return {
        "sleep": sleep,
        "feeding": feeding,
        "walks": walks,
        "diapers": diapers,
        "temperatures": temperatures,
        "medications": medications,
        "moods": moods
    }


# Analytics endpoints
@app.get("/analytics/child/{child_id}/stats")
def get_child_stats(child_id: int, days: int = 7, db: Session = Depends(get_db)):
    """Получить статистику за период"""
    from datetime import timedelta
    from sqlalchemy import func

    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.now(moscow_tz)
    start_date = end_date - timedelta(days=days)

    # Статистика сна
    sleep_stats = db.query(
        func.count(SleepActivity.id).label('count'),
        func.avg(SleepActivity.duration_minutes).label('avg_duration'),
        func.sum(SleepActivity.duration_minutes).label('total_duration')
    ).filter(
        SleepActivity.child_id == child_id,
        SleepActivity.start_time >= start_date,
        SleepActivity.duration_minutes.isnot(None)
    ).first()

    # Статистика кормлений
    feeding_stats = db.query(
        func.count(FeedingActivity.id).label('count'),
        func.avg(FeedingActivity.amount_ml).label('avg_amount'),
        func.sum(FeedingActivity.amount_ml).label('total_amount')
    ).filter(
        FeedingActivity.child_id == child_id,
        FeedingActivity.time >= start_date
    ).first()

    # Подсчет по типам кормления
    feeding_by_type = db.query(
        FeedingActivity.type,
        func.count(FeedingActivity.id).label('count')
    ).filter(
        FeedingActivity.child_id == child_id,
        FeedingActivity.time >= start_date
    ).group_by(FeedingActivity.type).all()

    # Статистика прогулок
    walk_stats = db.query(
        func.count(WalkActivity.id).label('count'),
        func.avg(WalkActivity.duration_minutes).label('avg_duration'),
        func.sum(WalkActivity.duration_minutes).label('total_duration')
    ).filter(
        WalkActivity.child_id == child_id,
        WalkActivity.start_time >= start_date,
        WalkActivity.duration_minutes.isnot(None)
    ).first()

    # Статистика подгузников
    diaper_stats = db.query(
        func.count(DiaperActivity.id).label('count')
    ).filter(
        DiaperActivity.child_id == child_id,
        DiaperActivity.time >= start_date
    ).first()

    # Подсчет по типам подгузников
    diaper_by_type = db.query(
        DiaperActivity.type,
        func.count(DiaperActivity.id).label('count')
    ).filter(
        DiaperActivity.child_id == child_id,
        DiaperActivity.time >= start_date
    ).group_by(DiaperActivity.type).all()

    # Статистика температуры
    temp_stats = db.query(
        func.count(TemperatureActivity.id).label('count'),
        func.avg(TemperatureActivity.temperature).label('avg_temp'),
        func.max(TemperatureActivity.temperature).label('max_temp'),
        func.min(TemperatureActivity.temperature).label('min_temp')
    ).filter(
        TemperatureActivity.child_id == child_id,
        TemperatureActivity.time >= start_date
    ).first()

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "sleep": {
            "count": sleep_stats.count or 0,
            "avg_duration_minutes": float(sleep_stats.avg_duration) if sleep_stats.avg_duration else 0,
            "total_duration_minutes": sleep_stats.total_duration or 0,
            "avg_duration_hours": round(float(sleep_stats.avg_duration) / 60, 1) if sleep_stats.avg_duration else 0,
            "total_duration_hours": round(float(sleep_stats.total_duration or 0) / 60, 1)
        },
        "feeding": {
            "count": feeding_stats.count or 0,
            "avg_amount_ml": float(feeding_stats.avg_amount) if feeding_stats.avg_amount else 0,
            "total_amount_ml": feeding_stats.total_amount or 0,
            "by_type": {item.type: item.count for item in feeding_by_type}
        },
        "walks": {
            "count": walk_stats.count or 0,
            "avg_duration_minutes": float(walk_stats.avg_duration) if walk_stats.avg_duration else 0,
            "total_duration_minutes": walk_stats.total_duration or 0,
            "avg_duration_hours": round(float(walk_stats.avg_duration) / 60, 1) if walk_stats.avg_duration else 0
        },
        "diapers": {
            "count": diaper_stats.count or 0,
            "by_type": {item.type: item.count for item in diaper_by_type}
        },
        "temperature": {
            "count": temp_stats.count or 0,
            "avg": float(temp_stats.avg_temp) if temp_stats.avg_temp else 0,
            "max": float(temp_stats.max_temp) if temp_stats.max_temp else 0,
            "min": float(temp_stats.min_temp) if temp_stats.min_temp else 0
        }
    }


@app.get("/analytics/child/{child_id}/daily")
def get_daily_stats(child_id: int, days: int = 7, db: Session = Depends(get_db)):
    """Получить ежедневную статистику для графиков"""
    from datetime import timedelta, date
    from sqlalchemy import func, cast, Date

    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.now(moscow_tz).date()
    start_date = end_date - timedelta(days=days - 1)

    # Статистика сна по дням
    sleep_by_day = db.query(
        cast(SleepActivity.start_time, Date).label('date'),
        func.count(SleepActivity.id).label('count'),
        func.sum(SleepActivity.duration_minutes).label('total_minutes')
    ).filter(
        SleepActivity.child_id == child_id,
        cast(SleepActivity.start_time, Date) >= start_date,
        SleepActivity.duration_minutes.isnot(None)
    ).group_by(cast(SleepActivity.start_time, Date)).all()

    # Кормления по дням
    feeding_by_day = db.query(
        cast(FeedingActivity.time, Date).label('date'),
        func.count(FeedingActivity.id).label('count'),
        func.sum(FeedingActivity.amount_ml).label('total_ml')
    ).filter(
        FeedingActivity.child_id == child_id,
        cast(FeedingActivity.time, Date) >= start_date
    ).group_by(cast(FeedingActivity.time, Date)).all()

    # Подгузники по дням
    diaper_by_day = db.query(
        cast(DiaperActivity.time, Date).label('date'),
        func.count(DiaperActivity.id).label('count')
    ).filter(
        DiaperActivity.child_id == child_id,
        cast(DiaperActivity.time, Date) >= start_date
    ).group_by(cast(DiaperActivity.time, Date)).all()

    # Формируем результат для каждого дня
    result = []
    current_date = start_date
    while current_date <= end_date:
        sleep_data = next((s for s in sleep_by_day if s.date == current_date), None)
        feeding_data = next((f for f in feeding_by_day if f.date == current_date), None)
        diaper_data = next((d for d in diaper_by_day if d.date == current_date), None)

        result.append({
            "date": current_date.isoformat(),
            "sleep": {
                "count": sleep_data.count if sleep_data else 0,
                "total_hours": round(float(sleep_data.total_minutes or 0) / 60, 1) if sleep_data else 0
            },
            "feeding": {
                "count": feeding_data.count if feeding_data else 0,
                "total_ml": feeding_data.total_ml if feeding_data else 0
            },
            "diapers": {
                "count": diaper_data.count if diaper_data else 0
            }
        })
        current_date += timedelta(days=1)

    return result