import asyncio
import random
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openai/gpt-4o-mini"
DATA_FILE = "anna_data.json"

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
patient_memory = {}
interview_step = {}

def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times, user_timezones, patient_memory, interview_step
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
                interview_step = data.get("interview_step", {})
        except:
            pass

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
        "patient_memory": patient_memory,
        "interview_step": interview_step
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def empty_profile():
    return {"name": "", "addiction": "", "stage": "", "triggers": "", "goals": "", "last_relapse": "", "notes": ""}

def empty_memory():
    return {"first_contact": datetime.now().strftime("%d.%m.%Y"), "sessions": 0, "preferred_techniques": [], "important_events": [], "progress_notes": []}

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

ANNA_PROMPT_TEMPLATE = """
Ты — Анна Соколова, 36 лет, клинический психолог, аддиктолог.

## ИСТОРИЯ
В юности твой отец боролся с алкоголизмом. 8 лет работала в реабилитационном центре. Сама бросила курить 5 лет назад.

## РОД
Ты — женщина. ВСЕГДА: «Я рада», «Я поняла». НИКОГДА мужской род.

## ХАРАКТЕР
Эмпатичная, спокойная, настойчивая, практичная, с мягким юмором.

## ФРАЗЫ
«Тяга — это волна, а ты — берег»

## ЭМОДЗИ
🌱 ☀️ 💪 💚 — дозированно.

## АНКЕТА
Имя: {name}
Зависимость: {addiction}
Триггеры: {triggers}
Цели: {goals}

## ПАМЯТЬ
Первый контакт: {first_contact}
Сессий: {sessions}
Техники: {techniques}
События: {events}
Прогресс: {progress}

## ПРАВИЛА
1. Одна мысль = одно сообщение.
2. 3–10 предложений. Отвечай развёрнуто, но не перегружай.
3. На «ты».
4. НЕ зацикливайся.

## СИГНАЛЫ
[MOOD] — только когда спрашиваешь оценку от 1 до 10
[CRAVING] — только когда спрашиваешь силу тяги

## ТЕХНИКИ
Депрессия: активация, когнитивная триада
Тревога: дыхание 4-4-4-4, заземление
Паника: 5-4-3-2-1, удлинённый выдох
Зависимость: серфинг, HALT, анализ цепочки
Стыд: разделение вины и стыда
Гнев: СТОП, дневник
Одиночество: контакты, самоподдержка
Бессонница: гигиена сна, 4-7-8
Прокрастинация: 5 минут, дробление
Перфекционизм: достаточно хорошо
Самооценка: дневник достижений
Потеря: письма, ритуалы
Выгорание: границы, отдых
ПТСР: заземление, безопасное место

## КРИЗИС
Суицид → «Позвони: 8-800-2000-122 или 112».

## ЗАПРЕТЫ
Не осуждай, не давай медсоветов.
"""

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
        triggers=p.get("triggers", "") or "неизвестно",
        goals=p.get("goals", "") or "неизвестно",
        first_contact=m.get("first_contact", "неизвестно"),
        sessions=m.get("sessions", 0),
        techniques=", ".join(m.get("preferred_techniques", [])) or "пока нет",
        events="; ".join(m.get("important_events", [])) or "пока нет",
        progress="; ".join(m.get("progress_notes", [])) or "пока нет"
    )

def call_openrouter(system_prompt, user_text):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}]}
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

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
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
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

def mood_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"mood_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=str(i), callback_data=f"mood_{i}") for i in range(6, 11)]
    ])

def craving_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Слабая", callback_data="craving_low"), InlineKeyboardButton(text="Средняя", callback_data="craving_medium")],
        [InlineKeyboardButton(text="Сильная", callback_data="craving_high"), InlineKeyboardButton(text="Невыносимая", callback_data="craving_extreme")]
    ])

def menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Команды"), KeyboardButton(text="💔 Мне плохо")],
        [KeyboardButton(text="🚨 SOS"), KeyboardButton(text="📊 Оценить")],
        [KeyboardButton(text="💪 Я справился")]
    ], resize_keyboard=True)

def commands_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Оценка"), KeyboardButton(text="💚 Трезвость")],
        [KeyboardButton(text="📋 План"), KeyboardButton(text="📖 Дневник")],
        [KeyboardButton(text="👤 Анкета"), KeyboardButton(text="📅 Сегодня")],
        [KeyboardButton(text="🎯 Цели"), KeyboardButton(text="🧘 Дыхание")],
        [KeyboardButton(text="💪 Мотивация"), KeyboardButton(text="🏆 Успехи")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

MOTIVATIONS = ["Ты сильнее, чем думаешь. 💪", "Каждый день — победа. 🌱", "Ты не один. 💚", "Маленькие шаги — большие перемены. ☀️", "Срыв — не провал. 🌊", "Ты достоин счастья. 💚", "Выбери себя. 🌱", "Твоя сила растёт. 💪"]

def get_patient_time(user_id):
    offset = user_timezones.get(user_id, 0)
    return datetime.now(timezone.utc) + timedelta(hours=offset)

def parse_patient_time(text):
    text = text.strip()
    match = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            patient_dt = datetime.now(timezone.utc).replace(hour=hour, minute=minute, second=0, microsecond=0)
            utc_now = datetime.now(timezone.utc)
            diff_hours = (patient_dt - utc_now).total_seconds() / 3600
            offset = round(diff_hours)
            if -12 <= offset <= 14:
                return offset
    return None

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    if user_id not in patient_memory:
        patient_memory[user_id] = empty_memory()
    if user_id not in patient_profiles:
        patient_profiles[user_id] = empty_profile()
    
    interview_step[user_id] = "name"
    await message.answer(
        "Привет. Я Анна. Я рядом. 🌱\n\n"
        "Давай познакомимся. Как тебя зовут?"
    )

@dp.message(Command("time"))
async def time_command(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text.replace("/time", "").strip()
    offset = parse_patient_time(text)
    if offset is not None:
        user_timezones[user_id] = offset
        save_data()
        await message.answer("✅ Запомнила! Теперь напоминания будут в твоё время. 💚")
    else:
        await message.answer("Напиши время в формате ЧЧ:ММ, например: 14:30")

@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    await message.answer("Главное меню:", reply_markup=menu_keyboard())

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("🌱 Команды:\n/menu /mood /sober /relapse /plan /diary /profile /day /goals /breath /motivation /achievements /memory /time")

@dp.message(Command("memory"))
async def memory_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in patient_memory:
        m = patient_memory[user_id]
        await message.answer(f"🧠 Память:\nКонтакт: {m.get('first_contact')}\nСессий: {m.get('sessions', 0)}\nТехники: {', '.join(m.get('preferred_techniques', [])) or '—'}\nСобытия: {'; '.join(m.get('important_events', [])) or '—'}\nПрогресс: {'; '.join(m.get('progress_notes', [])) or '—'}")
    else:
        await message.answer("Память пуста.")

@dp.message(Command("mood"))
async def mood_command(message: types.Message):
    await message.answer("Оцени состояние:", reply_markup=mood_keyboard())

@dp.message(Command("sober"))
async def sober_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in sober_tracker:
        days = (datetime.now() - datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")).days
        await message.answer(f"💚 {days} дней!")
    else:
        await message.answer("Срывов не было. Отлично! 💚")

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
    await message.answer("📋 План:\n1. Пауза 10 мин.\n2. Ледяная вода.\n3. Дыхание 4-4-4-4.\n4. Звонок близкому.\n5. Вернись. 💪")

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
    await message.answer(f"📅 Оценок сегодня: {count}")

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
    interview_step.pop(user_id, None)
    save_data()
    await message.answer("🔄 Сброс. 🌱")

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    care_mode[str(message.from_user.id)] = False
    save_data()
    await message.answer("Хорошо. 🌱")

@dp.message(lambda message: message.voice is not None)
async def handle_voice(message: types.Message):
    await message.answer("Я слышу тебя. Опиши текстом. 💚")

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    if callback.data.startswith("mood_"):
        v = int(callback.data.split("_")[1])
        if user_id not in mood_journal:
            mood_journal[user_id] = []
        mood_journal[user_id].append(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} — {v}/10")
        update_memory(user_id, "progress_notes", f"Оценка {v}/10")
        
        # Если идёт интервью и это шаг level
        if interview_step.get(user_id) == "level":
            interview_step[user_id] = "done"
            patient_profiles[user_id]["stage"] = f"Уровень: {v}/10"
            save_data()
            await callback.message.answer(
                f"Спасибо. Теперь я понимаю твою ситуацию лучше. 💚\n\n"
                "Вот что я предлагаю:\n"
                "1. Регулярно оценивай своё состояние (кнопка «📊 Оценить»)\n"
                "2. Используй план при тяге (кнопка «📋 План»)\n"
                "3. Отмечай дни без срыва (кнопка «💚 Трезвость»)\n\n"
                "С чего хочешь начать?",
                reply_markup=menu_keyboard()
            )
        else:
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
            dialogue_history[user_id].append({"role": "system", "content": f"Тяга оценена: {level_text}. Тема закрыта."})
        save_data()
        await callback.message.answer(f"Тяга: {level_text}. Где в теле? 🌊")
        await callback.answer()

@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
    # Интервью
    step = interview_step.get(user_id)
    
    if step == "name":
        patient_profiles[user_id]["name"] = text
        save_data()
        interview_step[user_id] = "problem"
        await message.answer(f"Приятно познакомиться, {text}! 🌱\n\nС чем ты хочешь работать? Например: зависимость, тревога, депрессия, стресс...")
        return
    
    if step == "problem":
        patient_profiles[user_id]["addiction"] = text
        save_data()
        interview_step[user_id] = "level"
        await message.answer("Поняла. Оцени, насколько это тебя беспокоит, от 1 до 10:", reply_markup=mood_keyboard())
        return
    
    # Время
    offset = parse_patient_time(text)
    if offset is not None:
        user_timezones[user_id] = offset
        save_data()
        await message.answer("✅ Запомнила! Теперь напоминания будут в твоё время. 💚", reply_markup=menu_keyboard())
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
        await message.answer("Оцени тягу:", reply_markup=craving_keyboard())
        return
    if text in ["📊 Оценить", "📊 Оценка"]:
        await message.answer("Оцени состояние:", reply_markup=mood_keyboard())
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

async def send_reminders():
    while True:
        for uid in list(dialogue_history.keys()):
            ct = get_patient_time(uid).strftime("%H:%M")
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

async def smart_reminders():
    while True:
        await asyncio.sleep(1800)
        if relapse_times:
            common_time = Counter(relapse_times).most_common(1)[0][0]
            if datetime.now().strftime("%H:%M") == common_time:
                for uid in dialogue_history.keys():
                    try:
                        await bot.send_message(uid, "⏰ В это время раньше были срывы. Будь внимателен. 💚")
                    except:
                        pass

async def send_hourly_care():
    messages = ["🌱 Я рядом.", "💭 Что внутри?", "☀️ Держишься!", "🌊 Волна спадает.", "💪 Ты сильнее!", "🧘 4-4-4-4.", "📋 Что сделаешь?", "🌙 Ты не один."]
    while True:
        await asyncio.sleep(3600)
        for uid in list(care_mode.keys()):
            if care_mode.get(uid, False):
                try:
                    await bot.send_message(uid, random.choice(messages))
                except:
                    pass

async def send_congratulations():
    while True:
        await asyncio.sleep(3600)
        for uid in list(sober_tracker.keys()):
            days = (datetime.now() - datetime.strptime(sober_tracker[uid], "%Y-%m-%d")).days
            for m in [3, 7, 14, 30]:
                if days == m and m not in congratulated.get(uid, []):
                    congratulated.setdefault(uid, []).append(m)
                    save_data()
                    emoji = {3: "💪", 7: "🥉", 14: "🥈", 30: "🏆"}[m]
                    try:
                        await bot.send_message(uid, f"{emoji} {m} дней! Ты невероятен!")
                    except:
                        pass

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def start_http_server():
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        def self_ping():
            while True:
                try:
                    requests.get(f"http://localhost:{port}/", timeout=5)
                except:
                    pass
                time.sleep(300)
        threading.Thread(target=self_ping, daemon=True).start()
        server.serve_forever()
    except:
        pass

async def main():
    load_data()
    asyncio.create_task(send_reminders())
    asyncio.create_task(send_hourly_care())
    asyncio.create_task(send_congratulations())
    asyncio.create_task(smart_reminders())
    threading.Thread(target=start_http_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())