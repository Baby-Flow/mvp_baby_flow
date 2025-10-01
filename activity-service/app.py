from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel
import pytz
from models import get_db, User, Child, SleepActivity, FeedingActivity, WalkActivity, DiaperActivity, \
    TemperatureActivity, Conversation

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
    db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if db_user:
        return db_user

    new_user = User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
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
    new_child = Child(
        user_id=child.user_id,
        name=child.name,
        birth_date=datetime.strptime(child.birth_date, "%Y-%m-%d").date(),
        gender=child.gender
    )
    db.add(new_child)
    db.commit()
    db.refresh(new_child)
    return new_child


@app.get("/children/user/{user_id}")
def get_children_by_user(user_id: int, db: Session = Depends(get_db)):
    children = db.query(Child).filter(Child.user_id == user_id).all()
    return children


# Sleep endpoints
@app.post("/activities/sleep/")
def create_sleep(sleep: SleepCreate, db: Session = Depends(get_db)):
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
    sleep = db.query(SleepActivity).filter(SleepActivity.id == sleep_id).first()
    if not sleep:
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
    return sleep


# Feeding endpoints
@app.post("/activities/feeding/")
def create_feeding(feeding: FeedingCreate, db: Session = Depends(get_db)):
    feeding_data = feeding.dict()

    # Обрабатываем datetime если строка
    if isinstance(feeding_data.get('time'), str):
        feeding_data['time'] = datetime.fromisoformat(feeding_data['time'].replace('Z', '+00:00'))

    new_feeding = FeedingActivity(**feeding_data)
    db.add(new_feeding)
    db.commit()
    db.refresh(new_feeding)
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


# Get all activities for a child
@app.get("/activities/child/{child_id}")
def get_child_activities(child_id: int, db: Session = Depends(get_db)):
    sleep = db.query(SleepActivity).filter(SleepActivity.child_id == child_id).all()
    feeding = db.query(FeedingActivity).filter(FeedingActivity.child_id == child_id).all()
    walks = db.query(WalkActivity).filter(WalkActivity.child_id == child_id).all()
    diapers = db.query(DiaperActivity).filter(DiaperActivity.child_id == child_id).all()
    temperatures = db.query(TemperatureActivity).filter(TemperatureActivity.child_id == child_id).all()

    return {
        "sleep": sleep,
        "feeding": feeding,
        "walks": walks,
        "diapers": diapers,
        "temperatures": temperatures
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

    return {
        "sleep": sleep,
        "feeding": feeding,
        "walks": walks,
        "diapers": diapers,
        "temperatures": temperatures
    }