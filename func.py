import re
from database import create_all_tables,drop_all_tables,engine,get_async_db,create_all_schools
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from models import UserORM,ClassORM,HomeworkORM
from datetime import datetime, timedelta
import difflib
import asyncio
import requests
import json
import aiohttp
import os

home_work_hash_table = {
    "алгебра":"algebra",
    "геометрия":"geometry",
    "английский язык":"english_language",
    "русский язык":"russian_language",
    "литература":"literature",
    "история":"history",
    "физика":"physics",
    "химия":"chemistry",
    "биология":"biology",
    "география":"geography",
    "обществознание":"social_science",
    "информатика":"informatics",
}

def validate_class_name(class_name: str) -> bool:
    """
    Проверяет, что класс соответствует формату:
    - Число от 1 до 11 (включительно)
    - Одна русская буква (заглавная или строчная)
    Например: 11Б, 9А, 10в
    
    Возвращает True, если валидно, иначе False.
    """
    pattern = r"^(?:[1-9]|10|11)[А-Яа-я]$"
    return bool(re.match(pattern, class_name.strip()))

def validate_school_name(school_name: str) -> bool:
    if int(school_name) < 0 or int(school_name) > 34:
        return False
    return True

async def is_admin(user_id: str) -> bool:
    async with get_async_db() as session:  
        result = await session.execute(select(UserORM).where(UserORM.tg_id == user_id))
        user = result.scalars().one_or_none()

        if not user:
            return False
        else:
            if user.possibility_to_add:
                return True
            else:
                return False
            
def get_subject_english(subject: str, cutoff=0.8) -> str | None:
    subject = subject.strip().lower()
    subjects = list(home_work_hash_table.keys())
    
    # Точное совпадение
    if subject in subjects:
        return home_work_hash_table[subject]
    
    # Похожее совпадение
    matches = difflib.get_close_matches(subject, subjects, n=1, cutoff=cutoff)
    if matches:
        return home_work_hash_table[matches[0]]

async def ask_apifreellm(user_message: str) -> str | None:
    url = "https://apifreellm.com/api/chat"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "message": user_message
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            # ApiFreeLLM всегда возвращает HTTP 200, даже при ошибках (см. docs) :contentReference[oaicite:1]{index=1}
            if resp.status == 200:
                resp_json = await resp.json()
                # Проверяем статус поля "status"
                status = resp_json.get("status")
                if status == "success":
                    return resp_json.get("response")
                else:
                    # При ошибке (например, превышен rate limit) придёт что-то вроде:
                    # {"error": "Rate limit exceeded. Please wait 5 seconds.", "status": "error"} :contentReference[oaicite:2]{index=2}
                    err = resp_json.get("error")
                    print(f"Ошибка API: {err}")
                    return None
            else:
                # Вдруг статус не 200 — выводим отладочные данные
                text = await resp.text()
                print(f"HTTP ошибка: {resp.status}, тело ответа: {text}")
                return None
            
def find_file_by_partial_name(folder_path, partial_name):
    search_name = partial_name.lower().replace(' ', '_')
    for filename in os.listdir(folder_path):
        if search_name in filename.lower():
            return os.path.join(folder_path, filename)
    return None