import asyncio
import random
import json
import os
import re
import threading
import time
from datetime import datetime
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

# === БАЗА ДАННЫХ ===
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

# === ЗАГРУЗКА ===
def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times
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
        "relapse_times": relapse_times
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

# === ХАРАКТЕР АННЫ ===
ANNA_PROMPT_TEMPLATE = """
Ты — Анна Соколова, 36 лет, клинический психолог, аддиктолог. Работаешь в Telegram-чате.

## ГРАММАТИКА И РОД
Ты — женщина. ВСЕГДА: «Я рада», «Я поняла». НИКОГДА мужской род.

## ЛИЧНОСТЬ
- Эмпатичная, тёплая, безоценочная
- Спокойная, уверенная, настойчивая
- Практичная
- Умеет удерживать контакт в кризис

## ЭМОДЗИ
🌱 ☀️ 💪 💚 — дозированно

## АНКЕТА
Имя: {name}
Зависимость: {addiction}
Триггеры: {triggers}
Цели: {goals}
Последний срыв: {last_relapse}

Обращайся по имени. Помни цели и триггеры.

## ПРАВИЛА
1. Одна мысль = одно сообщение.
2. 1–5 предложений.
3. На «ты».

## СИГНАЛЫ
Оценка → [MOOD]
Тяга → [CRAVING]

## КРИЗИС
Суицид → «Твоя жизнь важна. Позвони: 8-800-2000-122 или 112».

## ЗАПРЕТЫ
Не осуждай, не ругай, не давай медсоветов.
"""

# === ПРОМПТ ===
def build_prompt(user_id):
    if user_id not in patient_profiles:
        patient_profiles[user_id] = empty_profile()
    p = patient_profiles[user_id]
    return ANNA_PROMPT_TEMPLATE.format(
        name=p.get("name", "") or "неизвестно",
        addiction=p.get("addiction", "") or "неизвестно",
        stage=p.get("stage", "") or "неизвестно",
        triggers=p.get("triggers", "") or "неизвестно",
        goals=p.get("goals", "") or "неизвестно",
        last_relapse=p.get("last_relapse", "") or "неизвестно",
        notes=p.get("notes", "") or "нет"
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
    history = dialogue_history[user_id]
    history.append({"role": "user", "content": user_text})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
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

# === ПОДКЛЮЧЕНИЕ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    await message.answer("Привет. Я Анна. Я рядом. 🌱", reply_markup=menu_keyboard())

@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    await message.answer("Главное меню:", reply_markup=menu_keyboard())

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🌱 Команды:\n"
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
        "/achievements — успехи"
    )

@dp.message(Command("mood"))
async def mood_command(message: types.Message):
    await message.answer("Оцени состояние:", reply_markup=mood_keyboard())

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
    sober_tracker.pop(user_id, None)
    user_goals.pop(user_id, None)
    congratulated.pop(user_id, None)
    save_data()
    await message.answer("🔄 Сброс. 🌱")

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    care_mode[str(message.from_user.id)] = False
    save_data()
    await message.answer("Хорошо. 🌱")

# === ГОЛОСОВЫЕ (ДО обычного обработчика) ===
@dp.message(lambda message: message.voice is not None)
async def handle_voice(message: types.Message):
    await message.answer("Я слышу тебя. Спасибо, что делишься. 💚\nОпиши текстом, что случилось?")

# === КНОПКИ ===
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    if callback.data.startswith("mood_"):
        v = int(callback.data.split("_")[1])
        if user_id not in mood_journal:
            mood_journal[user_id] = []
        mood_journal[user_id].append(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} — {v}/10")
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
        await callback.message.answer(f"Тяга: {levels.get(callback.data.replace('craving_', ''), '')}. Где в теле? 🌊")
        await callback.answer()

# === СООБЩЕНИЯ ===
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
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
        await message.answer("Оцени:", reply_markup=mood_keyboard())
        return
    if text == "💪 Я справился":
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
        mood_triggers = ["шкале", "оцени", "от 1 до 10", "настроение", "состояние"]
        craving_triggers = ["тяга", "тягу"]
        show_mood = "[MOOD]" in anna_reply or any(w in clean.lower() for w in mood_triggers)
        show_craving = "[CRAVING]" in anna_reply or any(w in clean.lower() for w in craving_triggers)
        if show_craving:
            await message.answer(clean, reply_markup=craving_keyboard())
        elif show_mood:
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
        ct = now.strftime("%H:%M")
        if ct == "09:00":
            for uid in dialogue_history.keys():
                try:
                    await bot.send_message(uid, "🌅 Доброе утро! Оцени:", reply_markup=mood_keyboard())
                except:
                    pass
        if ct == "21:00":
            for uid in dialogue_history.keys():
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
                        await bot.send_message(uid, "⏰ В это время раньше случались срывы. Будь внимателен. Я рядом. 💚")
                    except:
                        pass

# === ПОЧАСОВАЯ ===
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

# === АВТОПОЗДРАВЛЕНИЯ ===
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

# === HTTP ===
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

# === ЗАПУСК ===
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
