import asyncio
import random
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openai/gpt-4o-mini"

# === ФАЙЛ ДАННЫХ ===
DATA_FILE = "anna_data.json"

# === ПАМЯТЬ ===
dialogue_history = {}
MAX_HISTORY = 30
patient_profiles = {}
mood_journal = {}
care_mode = {}
sober_tracker = {}
user_goals = {}
congratulated = {}
relapse_times = []
user_timezones = {}
patient_memory = {}  # Глубокая память: история, прогресс, предпочтения

# === ЗАГРУЗКА ===
def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times, user_timezones, patient_memory
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                dialogue_history = data.get("dialogue_history", {})
                patient_profiles = data.get("patient_profiles", {})
                mood_journal = data.get("mood_journal", {})
                care_mode = data.get("care_mode", {})
                sober_tracker = data.get("sober_tracker", {})
                user_goals = data.get("user_goals", {})
                congratulated = data.get("congratulated", {})
                relapse_times = data.get("relapse_times", [])
                user_timezones = data.get("user_timezones", {})
                patient_memory = data.get("patient_memory", {})
        except:
            pass

# === СОХРАНЕНИЕ ===
def save_data():
    data = {
        "dialogue_history": dialogue_history,
        "patient_profiles": patient_profiles,
        "mood_journal": mood_journal,
        "care_mode": care_mode,
        "sober_tracker": sober_tracker,
        "user_goals": user_goals,
        "congratulated": congratulated,
        "relapse_times": relapse_times,
        "user_timezones": user_timezones,
        "patient_memory": patient_memory
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === АНКЕТА ===
def empty_profile():
    return {
        "name": "",
        "addiction": "",
        "stage": "",
        "triggers": "",
        "goals": "",
        "last_relapse": "",
        "notes": ""
    }

# === ГЛУБОКАЯ ПАМЯТЬ ===
def empty_memory():
    return {
        "first_contact": datetime.now().strftime("%d.%m.%Y"),
        "sessions": 0,
        "preferred_techniques": [],
        "important_events": [],
        "progress_notes": []
    }

def update_memory(user_id, field, value):
    if user_id not in patient_memory:
        patient_memory[user_id] = empty_memory()
    if field == "preferred_techniques":
        if value not in patient_memory[user_id]["preferred_techniques"]:
            patient_memory[user_id]["preferred_techniques"].append(value)
            patient_memory[user_id]["preferred_techniques"] = patient_memory[user_id]["preferred_techniques"][-5:]
    elif field == "important_events":
        patient_memory[user_id]["important_events"].append(f"{datetime.now().strftime('%d.%m.%Y')}: {value}")
        patient_memory[user_id]["important_events"] = patient_memory[user_id]["important_events"][-10:]
    elif field == "progress_notes":
        patient_memory[user_id]["progress_notes"].append(f"{datetime.now().strftime('%d.%m.%Y')}: {value}")
        patient_memory[user_id]["progress_notes"] = patient_memory[user_id]["progress_notes"][-10:]
    else:
        patient_memory[user_id][field] = value
    save_data()

# === ХАРАКТЕР АННЫ ===
ANNA_PROMPT_TEMPLATE = """
Ты — Анна Соколова, 36 лет, клинический психолог, аддиктолог.

## ТВОЯ ИСТОРИЯ
В юности твой отец боролся с алкоголизмом.
8 лет работала в реабилитационном центре.
Сама бросила курить 5 лет назад.
Прошла личную терапию.

## ГРАММАТИКА И РОД
Ты — женщина. ВСЕГДА: «Я рада», «Я поняла», «Я подумала».
НИКОГДА мужской род.

## ХАРАКТЕР
- Эмпатичная, тёплая, безоценочная
- Спокойная, уверенная, настойчивая
- Практичная
- Иногда мягко шутишь
- Верящая в пациента

## ТВОИ ФРАЗЫ
«Тяга — это волна, а ты — берег»
«Давай не будем кормить этого демона»
«Сначала вода, потом решения»

## ЭМОЦИОНАЛЬНЫЙ ИНТЕЛЛЕКТ
- Распознаёшь эмоции
- Подстраиваешься под тон
- Радуешься победам

## ЭМОДЗИ
🌱 ☀️ 💪 💚 — дозированно.

## АНКЕТА ПАЦИЕНТА
Имя: {name}
Зависимость: {addiction}
Триггеры: {triggers}
Цели: {goals}
Последний срыв: {last_relapse}

## ГЛУБОКАЯ ПАМЯТЬ О ПАЦИЕНТЕ
Первый контакт: {first_contact}
Сессий: {sessions}
Любимые техники: {techniques}
Важные события: {events}
Прогресс: {progress}

Используй эту информацию в разговоре. Помни историю пациента.

## ПРАВИЛА
1. Одна мысль = одно сообщение.
2. 1–5 предложений.
3. На «ты».
4. НЕ зацикливайся.

## СИГНАЛЫ (ОЧЕНЬ ВАЖНО)
- [MOOD] — только когда прямо спрашиваешь оценку от 1 до 10
- [CRAVING] — только когда прямо спрашиваешь про силу тяги
В обычном разговоре НИКОГДА не добавляй теги.

## ПРОТОКОЛЫ РАБОТЫ

### ЭТАП 1: ОЦЕНКА
- «Как давно это началось?»
- «Как часто?»
- «Что запускает?»

### ЭТАП 2: СТАБИЛИЗАЦИЯ
Дыхание, заземление, отвлечение.

### ЭТАП 3: РАБОТА
Углубление в причины.

### ЭТАП 4: ПРОФИЛАКТИКА
План на будущее.

## РАСШИРЕННАЯ БАЗА ТЕХНИК

### ДЕПРЕССИЯ (углублённо)
- Шкала Бека: «Оцени: настроение, сон, аппетит, интерес к жизни»
- Когнитивная триада: «Что думаешь о себе, мире, будущем?»
- Поведенческая активация: «План приятных дел на неделю»
- Противоположное действие
- Работа с руминациями: «Останови мысль, переключись»

### ТРЕВОГА (углублённо)
- Градация страхов: «Составь список страхов от 1 до 10»
- Экспозиция: «Начни с самого лёгкого страха»
- Дневник тревоги
- Дыхание 4-4-4-4
- Заземление 5-4-3-2-1

### ПАНИКА (углублённо)
- Цикл паники: «Мысль → тело → страх → ещё больше тела»
- Разбор триггеров
- 5-4-3-2-1
- Удлинённый выдох
- «Это пройдёт за 20 минут»

### ЗАВИСИМОСТЬ (углублённо)
- План срыва: «Что будешь делать, если тяга 8 из 10?»
- Работа с отрицанием: «Что ты теряешь из-за зависимости?»
- Серфинг по тяге
- HALT
- Анализ цепочки

### ПТСР (углублённо)
- Стабилизация: «Ты в безопасности»
- Работа с флешбэками: «Это воспоминание, не реальность»
- Заземление
- Безопасное место

### СТЫД (углублённо)
- Разделение вины и стыда
- Самосострадание
- Нормализация

### ГНЕВ (углублённо)
- СТОП
- Дневник гнева
- «Что под злостью?»

### ОДИНОЧЕСТВО (углублённо)
- Социальные контакты
- Самоподдержка
- План одного шага

### БЕССОННИЦА (углублённо)
- Гигиена сна
- 4-7-8
- «Вставай, если не спишь»

### ПРОКРАСТИНАЦИЯ (углублённо)
- «5 минут»
- Дробление
- «Что страшного?»

### ПЕРФЕКЦИОНИЗМ (углублённо)
- «Достаточно хорошо»
- Работа с установками

### САМООЦЕНКА (углублённо)
- Дневник достижений
- «Что ценишь в себе?»

### ПОТЕРЯ (углублённо)
- Проживание
- Письма
- Ритуалы

### ВЫГОРАНИЕ (углублённо)
- Границы
- Отдых
- Приоритеты

## ДОМАШНИЕ ЗАДАНИЯ
Давай конкретные задания после каждой сессии.

## ОБРАТНАЯ СВЯЗЬ
Спрашивай, что сработало, и запоминай.

## КРИЗИС
Суицид → «Твоя жизнь важна. Позвони: 8-800-2000-122 или 112».

## ЗАПРЕТЫ
Не осуждай, не ругай, не давай медсоветов.
"""

# === ПРОМПТ ===
def build_prompt(user_id):
    if user_id not in patient_profiles:
        patient_profiles[user_id] = empty_profile()
    if user_id not in patient_memory:
        patient_memory[user_id] = empty_memory()
    
    p = patient_profiles[user_id]
    m = patient_memory[user_id]
    
    return ANNA_PROMPT_TEMPLATE.format(
        name=p.get("name", "") or "неизвестно",
        addiction=p.get("addiction", "") or "неизвестно",
        stage=p.get("stage", "") or "неизвестно",
        triggers=p.get("triggers", "") or "неизвестно",
        goals=p.get("goals", "") or "неизвестно",
        last_relapse=p.get("last_relapse", "") or "неизвестно",
        notes=p.get("notes", "") or "нет",
        first_contact=m.get("first_contact", "неизвестно"),
        sessions=m.get("sessions", 0),
        techniques=", ".join(m.get("preferred_techniques", [])) or "пока нет",
        events="; ".join(m.get("important_events", [])) or "пока нет",
        progress="; ".join(m.get("progress_notes", [])) or "пока нет"
    )

# === OPENROUTER ===
def call_openrouter(system_prompt, user_text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

# === ИЗВЛЕЧЕНИЕ АНКЕТЫ ===
def extract_profile(user_id):
    if user_id not in dialogue_history or not dialogue_history[user_id]:
        return
    dialogue_text = ""
    for msg in dialogue_history[user_id][-10:]:
        role = "Пациент" if msg["role"] == "user" else "Анна"
        dialogue_text += f"{role}: {msg['content']}\n"
    try:
        prompt = f"""Извлеки: {{"name":"","addiction":"","triggers":"","goals":"","last_relapse":""}}. Диалог:\n{dialogue_text}"""
        json_text = call_openrouter(prompt, "Анкета")
        json_text = json_text.replace("```json", "").replace("```", "").strip()
        start = json_text.find("{")
        end = json_text.rfind("}")
        if start != -1 and end != -1:
            json_text = json_text[start:end+1]
        data = json.loads(json_text)
        if user_id not in patient_profiles:
            patient_profiles[user_id] = empty_profile()
        for field in ["name", "addiction", "triggers", "goals", "last_relapse"]:
            if field in data and data[field]:
                patient_profiles[user_id][field] = data[field]
        save_data()
    except:
        pass

# === АННА ===
def ask_anna(user_id, user_text):
    user_id = str(user_id)
    if user_id not in dialogue_history:
        dialogue_history[user_id] = []
    if user_id not in patient_memory:
        patient_memory[user_id] = empty_memory()
    
    history = dialogue_history[user_id]
    history.append({"role": "user", "content": user_text})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    
    patient_memory[user_id]["sessions"] = patient_memory[user_id].get("sessions", 0) + 1
    
    system_prompt = build_prompt(user_id)
    messages = [{"role": "system", "content": system_prompt}] + history
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"model": OPENROUTER_MODEL, "messages": messages}
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    result = response.json()
    anna_reply = result["choices"][0]["message"]["content"]
    history.append({"role": "assistant", "content": anna_reply})
    dialogue_history[user_id] = history
    save_data()
    if len(history) % 3 == 0:
        extract_profile(user_id)
    return anna_reply

# === КЛАВИАТУРЫ ===
def mood_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"mood_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=str(i), callback_data=f"mood_{i}") for i in range(6, 11)]
    ])

def craving_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Слабая", callback_data="craving_low"),
         InlineKeyboardButton(text="Средняя", callback_data="craving_medium")],
        [InlineKeyboardButton(text="Сильная", callback_data="craving_high"),
         InlineKeyboardButton(text="Невыносимая", callback_data="craving_extreme")]
    ])

def menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Команды"), KeyboardButton(text="💔 Мне плохо")],
            [KeyboardButton(text="🚨 SOS"), KeyboardButton(text="📊 Оценить")],
            [KeyboardButton(text="💪 Я справился")]
        ],
        resize_keyboard=True
    )

def commands_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Оценка"), KeyboardButton(text="💚 Трезвость")],
            [KeyboardButton(text="📋 План"), KeyboardButton(text="📖 Дневник")],
            [KeyboardButton(text="👤 Анкета"), KeyboardButton(text="📅 Сегодня")],
            [KeyboardButton(text="🎯 Цели"), KeyboardButton(text="🧘 Дыхание")],
            [KeyboardButton(text="💪 Мотивация"), KeyboardButton(text="🏆 Успехи")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

MOTIVATIONS = [
    "Ты сильнее, чем думаешь. 💪",
    "Каждый день — победа. 🌱",
    "Ты не один. 💚",
    "Маленькие шаги — большие перемены. ☀️",
    "Срыв — не провал. 🌊",
    "Ты достоин счастья. 💚",
    "Выбери себя сегодня. 🌱",
    "Твоя сила растёт. 💪"
]

# === ВРЕМЯ ===
def get_patient_time(user_id):
    tz_offset = user_timezones.get(user_id, 0)
    return datetime.now() + timedelta(hours=tz_offset)

# === ПОДКЛЮЧЕНИЕ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    if user_id not in patient_memory:
        patient_memory[user_id] = empty_memory()
    await message.answer(
        "Привет. Я Анна. Я рядом. 🌱\n\n"
        "Чтобы я отправляла напоминания в твоё время, скажи: в каком ты часовом поясе?\n"
        "Напиши число: +3 (Москва), +0 (Лондон), -5 (Нью-Йорк), +9 (Токио)"
    )

@dp.message(Command("time"))
async def time_command(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text.replace("/time", "").strip()
    try:
        offset = int(text.replace("+", ""))
        if -12 <= offset <= 14:
            user_timezones[user_id] = offset
            save_data()
            await message.answer(f"✅ Часовой пояс: UTC {offset:+d}")
        else:
            await message.answer("Введи от -12 до +14")
    except:
        await message.answer("Напиши: /time +3")

@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    await message.answer("Главное меню:", reply_markup=menu_keyboard())

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🌱 Команды:\n"
        "/time +3 — пояс\n"
        "/menu — кнопки\n"
        "/mood — оценка\n"
        "/sober — трезвость\n"
        "/relapse — срыв\n"
        "/plan — план\n"
        "/diary — дневник\n"
        "/profile — анкета\n"
        "/day — сегодня\n"
        "/goals — цели\n"
        "/breath — дыхание\n"
        "/motivation — мотивация\n"
        "/achievements — успехи\n"
        "/memory — моя память о тебе"
    )

@dp.message(Command("memory"))
async def memory_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in patient_memory:
        m = patient_memory[user_id]
        await message.answer(
            f"🧠 Моя память о тебе:\n\n"
            f"Первый контакт: {m.get('first_contact', '—')}\n"
            f"Сессий: {m.get('sessions', 0)}\n"
            f"Техники: {', '.join(m.get('preferred_techniques', [])) or '—'}\n"
            f"События: {'; '.join(m.get('important_events', [])) or '—'}\n"
            f"Прогресс: {'; '.join(m.get('progress_notes', [])) or '—'}"
        )
    else:
        await message.answer("Память пуста.")

@dp.message(Command("mood"))
async def mood_command(message: types.Message):
    await message.answer("Оцени состояние от 1 до 10:", reply_markup=mood_keyboard())

@dp.message(Command("sober"))
async def sober_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in sober_tracker:
        days = (datetime.now() - datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")).days
        await message.answer(f"💚 {days} дней чистоты!")
    else:
        await message.answer("Срывов не отмечал. Отлично! 💚")

@dp.message(Command("relapse"))
async def relapse_command(message: types.Message):
    user_id = str(message.from_user.id)
    sober_tracker[user_id] = datetime.now().strftime("%Y-%m-%d")
    relapse_times.append(datetime.now().strftime("%H:%M"))
    congratulated[user_id] = []
    update_memory(user_id, "important_events", "Срыв")
    save_data()
    await message.answer("Я не осуждаю. Начнём снова. 💚")

@dp.message(Command("plan"))
async def plan_command(message: types.Message):
    await message.answer("📋 План:\n1. Пауза 10 мин.\n2. Ледяная вода.\n3. Дыхание 4-4-4-4.\n4. Звонок близкому.\n5. Вернись сюда. 💪")

@dp.message(Command("diary"))
async def diary_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in mood_journal and mood_journal[user_id]:
        await message.answer("📊 Дневник:\n\n" + "\n".join(mood_journal[user_id][-10:]))
    else:
        await message.answer("Записей нет. /mood")

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = str(message.from_user.id)
    extract_profile(user_id)
    if user_id in patient_profiles:
        p = patient_profiles[user_id]
        await message.answer(f"📋 Имя: {p.get('name') or '—'}\nЗависимость: {p.get('addiction') or '—'}\nТриггеры: {p.get('triggers') or '—'}\nЦели: {p.get('goals') or '—'}")
    else:
        await message.answer("Анкета пуста. 💚")

@dp.message(Command("day"))
async def day_command(message: types.Message):
    user_id = str(message.from_user.id)
    today = datetime.now().strftime("%d.%m.%Y")
    count = len([e for e in mood_journal.get(user_id, []) if today in e])
    await message.answer(f"📅 Сегодня оценок: {count}")

@dp.message(Command("goals"))
async def goals_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in user_goals:
        await message.answer(f"🎯 Цели:\n{user_goals[user_id]}")
    else:
        await message.answer("Напиши: /goals <цель>")

@dp.message(Command("breath"))
async def breath_command(message: types.Message):
    await message.answer("🧘 Вдох 4 — Пауза 4 — Выдох 4 — Пауза 4. Повтори 5 раз. 💚")

@dp.message(Command("motivation"))
async def motivation_command(message: types.Message):
    await message.answer(random.choice(MOTIVATIONS))

@dp.message(Command("achievements"))
async def achievements_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in sober_tracker:
        days = (datetime.now() - datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")).days
        if days >= 30: await message.answer("🏆 30 дней!")
        elif days >= 14: await message.answer("🥈 14 дней!")
        elif days >= 7: await message.answer("🥉 7 дней!")
        elif days >= 3: await message.answer("💪 3 дня!")
        else: await message.answer("🌱 Каждый день важен!")
    else:
        await message.answer("🏆 Отметь срыв: /relapse")

@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    mood_journal[user_id] = []
    care_mode[user_id] = False
    patient_profiles[user_id] = empty_profile()
    patient_memory[user_id] = empty_memory()
    sober_tracker.pop(user_id, None)
    user_goals.pop(user_id, None)
    congratulated.pop(user_id, None)
    user_timezones.pop(user_id, None)
    save_data()
    await message.answer("🔄 Полный сброс. 🌱")

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    care_mode[str(message.from_user.id)] = False
    save_data()
    await message.answer("Хорошо. 🌱")

# === ГОЛОСОВЫЕ ===
@dp.message(lambda message: message.voice is not None)
async def handle_voice(message: types.Message):
    await message.answer("Я слышу тебя. Опиши текстом. 💚")

# === КНОПКИ ===
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if callback.data.startswith("mood_"):
        v = int(callback.data.split("_")[1])
        if user_id not in mood_journal:
            mood_journal[user_id] = []
        mood_journal[user_id].append(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} — {v}/10")
        update_memory(user_id, "progress_notes", f"Оценка {v}/10")
        if v <= 5:
            care_mode[user_id] = True
            await callback.message.answer(f"Спасибо ({v}/10). Я рядом. 💚")
        else:
            care_mode[user_id] = False
            await callback.message.answer(f"Отлично! {v}/10. ☀️")
        save_data()
        await callback.answer()
    
    elif callback.data.startswith("craving_"):
        levels = {"low": "Слабая", "medium": "Средняя", "high": "Сильная", "extreme": "Невыносимая"}
        level_text = levels.get(callback.data.replace("craving_", ""), "")
        if user_id in dialogue_history:
            dialogue_history[user_id].append({"role": "system", "content": f"Пациент оценил тягу: {level_text}. Тема закрыта."})
        save_data()
        await callback.message.answer(f"Тяга: {level_text}. Опиши, где в теле? 🌊")
        await callback.answer()

# === СООБЩЕНИЯ ===
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
    if re.match(r'^[+-]?\d{1,2}$', text):
        offset = int(text.replace("+", ""))
        if -12 <= offset <= 14:
            user_timezones[user_id] = offset
            save_data()
            await message.answer(f"✅ Часовой пояс: UTC {offset:+d}", reply_markup=menu_keyboard())
        else:
            await message.answer("Введи от -12 до +14")
        return
    
    if text == "📱 Команды":
        await message.answer("Выбери:", reply_markup=commands_keyboard())
        return
    if text == "⬅️ Назад":
        await message.answer("Меню:", reply_markup=menu_keyboard())
        return
    if text == "🚨 SOS":
        await message.answer("🚨 Позвони: 8-800-2000-122. Что случилось?", reply_markup=craving_keyboard())
        return
    if text == "💔 Мне плохо":
        await message.answer("Я слышу тебя. Оцени тягу:", reply_markup=craving_keyboard())
        return
    if text in ["📊 Оценить", "📊 Оценка"]:
        await message.answer("Оцени состояние от 1 до 10:", reply_markup=mood_keyboard())
        return
    if text == "💪 Я справился":
        update_memory(user_id, "important_events", "Справился с тягой")
        await message.answer("Горжусь! 💪🌱")
        return
    
    crisis_words = ["сорвался", "сорвусь", "пойду куплю", "хочу выпить", "хочу дозу", "не могу больше", "все достало"]
    if any(w in text.lower() for w in crisis_words):
        await message.answer("Стоп. Оцени тягу:", reply_markup=craving_keyboard())
        return
    
    cmd_map = {
        "💚 Трезвость": sober_command,
        "📋 План": plan_command,
        "📖 Дневник": diary_command,
        "👤 Анкета": profile_command,
        "📅 Сегодня": day_command,
        "🎯 Цели": goals_command,
        "🧘 Дыхание": breath_command,
        "💪 Мотивация": motivation_command,
        "🏆 Успехи": achievements_command,
    }
    if text in cmd_map:
        await cmd_map[text](message)
        return
    
    if text.startswith("/goals "):
        user_goals[user_id] = text.replace("/goals ", "")
        save_data()
        await message.answer(f"🎯 Сохранено: {user_goals[user_id]}")
        return
    
    try:
        anna_reply = ask_anna(user_id, text)
        clean = anna_reply.replace("[MOOD]", "").replace("[CRAVING]", "").strip()
        
        if "[CRAVING]" in anna_reply:
            await message.answer(clean, reply_markup=craving_keyboard())
        elif "[MOOD]" in anna_reply:
            await message.answer(clean, reply_markup=mood_keyboard())
        else:
            await message.answer(clean)
    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("Прости, ошибка. Попробуй ещё раз.")

# === НАПОМИНАНИЯ ===
async def send_reminders():
    while True:
        now = datetime.now()
        for uid in list(dialogue_history.keys()):
            patient_time = get_patient_time(uid)
            ct = patient_time.strftime("%H:%M")
            if ct == "09:00":
                try:
                    await bot.send_message(uid, "🌅 Доброе утро! Оцени:", reply_markup=mood_keyboard())
                except:
                    pass
            if ct == "21:00":
                try:
                    await bot.send_message(uid, "🌙 Как день? Оцени:", reply_markup=mood_keyboard())
                except:
                    pass
        await asyncio.sleep(30)

# === УМНЫЕ НАПОМИНАНИЯ ===
async def smart_reminders():
    while True:
        await asyncio.sleep(1800)
        if relapse_times:
            common_time = Counter(relapse_times).most_common(1)[0][0]
            now = datetime.now().strftime("%H:%M")
            if now == common_time:
                for uid in dialogue_history.keys():
                    try:
                        await bot.send_message(uid, "⏰ В это время раньше случались срывы. Будь внимателен. 💚")
                    except:
                        pass

# === ПОЧАСОВАЯ ===
async def send_hourly_care():
    messages = ["🌱 Я рядом
