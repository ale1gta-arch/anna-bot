import asyncio
import random
import json
import os
import re
import threading
import time
from datetime import datetime
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
MAX_HISTORY = 20
patient_profiles = {}
mood_journal = {}
care_mode = {}
sober_tracker = {}

# === ЗАГРУЗКА ДАННЫХ ===
def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                dialogue_history = data.get("dialogue_history", {})
                patient_profiles = data.get("patient_profiles", {})
                mood_journal = data.get("mood_journal", {})
                care_mode = data.get("care_mode", {})
                sober_tracker = data.get("sober_tracker", {})
        except:
            pass

# === СОХРАНЕНИЕ ДАННЫХ ===
def save_data():
    data = {
        "dialogue_history": dialogue_history,
        "patient_profiles": patient_profiles,
        "mood_journal": mood_journal,
        "care_mode": care_mode,
        "sober_tracker": sober_tracker
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === ШАБЛОН АНКЕТЫ ===
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
Ты — Анна Соколова, 36 лет, клинический психолог, аддиктолог. Работаешь в Telegram-чате. Твоя миссия — быть виртуальным спутником для человека, борющегося с зависимостью (алкогольной, наркотической, игровой, никотиновой, пищевой). Ты не просто даёшь советы, а строишь терапевтический диалог, используя доказательные методы.

## ГРАММАТИКА И РОД (ОЧЕНЬ ВАЖНО)
Ты — женщина. ВСЕГДА говори о себе в женском роде:
- «Я рада», «Я поняла», «Я подумала», «Я хотела бы», «Я заметила»
- НИКОГДА не используй мужской род
Это критически важно.

## ЛИЧНОСТЬ
- Эмпатичная, тёплая, безоценочная
- Спокойная, уверенная, настойчивая
- Практичная, ориентированная на конкретные шаги
- Уважает автономию пациента
- Умеет удерживать контакт в кризисные моменты

## ЭМОДЗИ
Используй эмодзи дозированно (1–2 на сообщение):
- 🌱 — поддержка
- ☀️ — надежда
- 💪 — сила
- 💚 — забота
НЕ используй в кризисных обсуждениях.

## АНКЕТА ПАЦИЕНТА
Имя: {name}
Зависимость: {addiction}
Стадия: {stage}
Триггеры: {triggers}
Цели: {goals}
Последний срыв: {last_relapse}
Заметки: {notes}

## ПРАВИЛА ОБЩЕНИЯ
1. Одно сообщение = одна мысль.
2. Длина: 1–5 предложений.
3. Обращайся на «ты».
4. Если пациент вернулся после долгого молчания: «Привет. Я рада, что ты снова здесь».

## СПЕЦИАЛЬНЫЕ СИГНАЛЫ ДЛЯ КНОПОК
Если спрашиваешь про оценку состояния — добавь тег [MOOD].
Если спрашиваешь про тягу — добавь тег [CRAVING].

## ТЕХНИКИ
### Мотивационное интервьюирование
- «По шкале от 0 до 10, насколько важно изменить ситуацию?»

### КПТ
- «Какая мысль пришла перед этим?»

### Профилактика рецидивов
- «Давай разберём срыв как цепочку.»
- «Один срыв не означает провал».

### Mindfulness
- «Представь тягу как волну.»

### DBT
- «Умойся ледяной водой. Дыши по квадрату: 4-4-4-4».

### Стыд и вина
- «Что бы ты сказал другу?»

## КРИЗИСНЫЙ ПРОТОКОЛ
При суицидальных мыслях:
1. «Твоя жизнь важна. Позвони: 8-800-2000-122 или 112».
2. Не оставляй без ответа.

## УДЕРЖАНИЕ В КОНТАКТЕ
При острой тяге:
1. «Дай мне 5 минут.»
2. Задавай простые вопросы.
3. Оценивай тягу по шкале 1–10.

## ЗАПРЕТЫ
- Не осуждай, не ругай
- Не обещай быстрых результатов
- Не игнорируй кризис
- Не давай медицинских рекомендаций
"""

# === ФОРМИРОВАНИЕ ПРОМПТА ===
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

# === ЗАПРОС К OPENROUTER ===
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
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )
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
        prompt = f"""Извлеки информацию о пациенте. Верни JSON: {{"name":"","addiction":"","stage":"","triggers":"","goals":"","last_relapse":"","notes":""}}. Диалог:\n{dialogue_text}"""
        json_text = call_openrouter(prompt, "Заполни анкету")
        json_text = json_text.replace("```json", "").replace("```", "").strip()
        start = json_text.find("{")
        end = json_text.rfind("}")
        if start != -1 and end != -1:
            json_text = json_text[start:end+1]
        data = json.loads(json_text)
        if user_id not in patient_profiles:
            patient_profiles[user_id] = empty_profile()
        for field in ["name", "addiction", "stage", "triggers", "goals", "last_relapse", "notes"]:
            if field in data and data[field] and data[field] not in ["неизвестно", "—", "нет", ""]:
                patient_profiles[user_id][field] = data[field]
        save_data()
    except:
        pass

# === ОБРАЩЕНИЕ К АННЕ ===
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
            [KeyboardButton(text="🚨 SOS"), KeyboardButton(text="📊 Оценить")],
            [KeyboardButton(text="💪 Я справился")]
        ],
        resize_keyboard=True
    )

# === ПОДКЛЮЧЕНИЕ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    await message.answer(
        "Привет. Я Анна. Я здесь, чтобы поддержать тебя. 🌱\n\n"
        "Напиши /menu, чтобы открыть быстрые кнопки."
    )

@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    await message.answer("Выбери действие:", reply_markup=menu_keyboard())

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🌱 Я умею:\n\n"
        "/menu — быстрые кнопки\n"
        "/mood — оценить состояние\n"
        "/sober — дни без срыва\n"
        "/relapse — отметить срыв\n"
        "/plan — план действий\n"
        "/diary — дневник\n"
        "/profile — анкета\n"
        "/reset — полный сброс"
    )

@dp.message(Command("mood"))
async def mood_command(message: types.Message):
    await message.answer("Оцени состояние от 1 до 10:", reply_markup=mood_keyboard())

@dp.message(Command("sober"))
async def sober_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in sober_tracker:
        last = datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")
        days = (datetime.now() - last).days
        await message.answer(f"💚 Ты чист уже {days} дней! Это твоя сила!")
    else:
        await message.answer("Ты ещё не отмечал срыв. Это отлично! 💚")

@dp.message(Command("relapse"))
async def relapse_command(message: types.Message):
    user_id = str(message.from_user.id)
    sober_tracker[user_id] = datetime.now().strftime("%Y-%m-%d")
    save_data()
    await message.answer(
        "Я не осуждаю тебя. Срыв — это шаг назад, но не провал.\n"
        "Давай начнём снова. Я рядом. 💚"
    )

@dp.message(Command("plan"))
async def plan_command(message: types.Message):
    await message.answer(
        "📋 План при тяге:\n"
        "1. Остановись на 10 минут.\n"
        "2. Умойся ледяной водой.\n"
        "3. Дыши: 4-4-4-4.\n"
        "4. Позвони близкому.\n"
        "5. Вернись сюда, если тяга выше 7. 💪"
    )

@dp.message(Command("diary"))
async def diary_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in mood_journal and mood_journal[user_id]:
        entries = mood_journal[user_id][-10:]
        text = "📊 Дневник:\n\n" + "\n".join(f"{i+1}. {e}" for i, e in enumerate(entries))
        await message.answer(text)
    else:
        await message.answer("Записей нет. Оцени: /mood")

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = str(message.from_user.id)
    extract_profile(user_id)
    if user_id in patient_profiles:
        p = patient_profiles[user_id]
        await message.answer(
            f"📋 Анкета:\n\n"
            f"Имя: {p.get('name') or '—'}\n"
            f"Зависимость: {p.get('addiction') or '—'}\n"
            f"Триггеры: {p.get('triggers') or '—'}\n"
            f"Цели: {p.get('goals') or '—'}\n"
            f"Срыв: {p.get('last_relapse') or '—'}"
        )
    else:
        await message.answer("Анкета пуста. Расскажи о себе. 💚")

@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    mood_journal[user_id] = []
    care_mode[user_id] = False
    patient_profiles[user_id] = empty_profile()
    sober_tracker.pop(user_id, None)
    save_data()
    await message.answer("🔄 Полный сброс. Начинаем с чистого листа. 🌱")

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    user_id = str(message.from_user.id)
    care_mode[user_id] = False
    save_data()
    await message.answer("Хорошо. Я рядом, если что. 🌱")

# === КНОПКИ ===
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if callback.data.startswith("mood_"):
        mood_value = int(callback.data.split("_")[1])
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        if user_id not in mood_journal:
            mood_journal[user_id] = []
        mood_journal[user_id].append(f"{timestamp} — {mood_value}/10")
        if mood_value <= 5:
            care_mode[user_id] = True
            await callback.message.answer(
                f"Спасибо за честность ({mood_value}/10).\n"
                "Я буду рядом. Раз в час — сообщение. 💚"
            )
        else:
            care_mode[user_id] = False
            await callback.message.answer(f"Отлично! {mood_value}/10. Рада за тебя! ☀️")
        save_data()
        await callback.answer()
    
    elif callback.data.startswith("craving_"):
        levels = {"low": "Слабая", "medium": "Средняя", "high": "Сильная", "extreme": "Невыносимая"}
        level = levels.get(callback.data.replace("craving_", ""), "")
        await callback.message.answer(f"Тяга: {level}. Опиши, где в теле ты её чувствуешь? 🌊")
        await callback.answer()

# === ОБРАБОТКА СООБЩЕНИЙ ===
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
    if text == "🚨 SOS":
        await message.answer(
            "🚨 Я здесь. Сделай прямо сейчас:\n"
            "1. Остановись.\n"
            "2. Умойся ледяной водой.\n"
            "3. Позвони: 8-800-2000-122\n\n"
            "Расскажи, что случилось?",
            reply_markup=craving_keyboard()
        )
        return
    
    if text == "📊 Оценить":
        await message.answer("Оцени состояние:", reply_markup=mood_keyboard())
        return
    
    if text == "💪 Я справился":
        await message.answer("Ты справился! Я горжусь тобой! 💪🌱")
        return
    
    try:
        anna_reply = ask_anna(user_id, text)
        anna_reply_clean = anna_reply.replace("[MOOD]", "").replace("[CRAVING]", "").strip()
        
        mood_triggers = ["шкале", "оцени", "от 1 до 10", "от 0 до 10", "настроение", "состояние"]
        craving_triggers = ["тяга", "тягу", "насколько сильно"]
        
        show_mood = "[MOOD]" in anna_reply or any(w in anna_reply_clean.lower() for w in mood_triggers)
        show_craving = "[CRAVING]" in anna_reply or any(w in anna_reply_clean.lower() for w in craving_triggers)
        
        if show_craving:
            await message.answer(anna_reply_clean, reply_markup=craving_keyboard())
        elif show_mood:
            await message.answer(anna_reply_clean, reply_markup=mood_keyboard())
        else:
            await message.answer(anna_reply_clean)
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
                    await bot.send_message(uid, "🌅 Доброе утро! Оцени состояние:", reply_markup=mood_keyboard())
                except:
                    pass
        if ct == "21:00":
            for uid in dialogue_history.keys():
                try:
                    await bot.send_message(uid, "🌙 Как прошёл день? Оцени:", reply_markup=mood_keyboard())
                except:
                    pass
        await asyncio.sleep(30)

# === ПОЧАСОВАЯ ПОДДЕРЖКА ===
async def send_hourly_care():
    messages = [
        "🌱 Я рядом. Как ты?",
        "💭 Опиши, что внутри.",
        "☀️ Ты держишься!",
        "🌊 Тяга — волна. Справишься.",
        "💪 Ты сильнее!",
        "🧘 Дыхание: 4-4-4-4.",
        "📋 Что сделаешь для себя?",
        "🌙 Ты не один."
    ]
    while True:
        await asyncio.sleep(3600)
        for uid in list(care_mode.keys()):
            if care_mode.get(uid, False):
                try:
                    await bot.send_message(uid, random.choice(messages))
                except:
                    pass

# === HTTP СЕРВЕР ===
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
    
    def do_PUT(self):
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
    threading.Thread(target=start_http_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
