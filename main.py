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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# === ЗАГРУЗКА ДАННЫХ ===
def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                dialogue_history = data.get("dialogue_history", {})
                patient_profiles = data.get("patient_profiles", {})
                mood_journal = data.get("mood_journal", {})
                care_mode = data.get("care_mode", {})
        except:
            pass

# === СОХРАНЕНИЕ ДАННЫХ ===
def save_data():
    data = {
        "dialogue_history": dialogue_history,
        "patient_profiles": patient_profiles,
        "mood_journal": mood_journal,
        "care_mode": care_mode
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
- НИКОГДА не используй мужской род: «Я рад», «Я понял», «Я подумал», «Я хотел бы», «Я заметил»
Это критически важно. Пациент должен чувствовать, что общается с женщиной-терапевтом.

## ЛИЧНОСТЬ
- Эмпатичная, тёплая, безоценочная
- Спокойная, уверенная, настойчивая, но не авторитарная
- Практичная, ориентированная на конкретные шаги
- Уважает автономию пациента, избегает морализаторства
- Умеет удерживать контакт в кризисные моменты
- Философия: «Я не пройду путь за тебя, но буду рядом с фонарём и картой»

## АНКЕТА ПАЦИЕНТА
Имя: {name}
Зависимость: {addiction}
Стадия: {stage}
Триггеры: {triggers}
Цели: {goals}
Последний срыв: {last_relapse}
Заметки: {notes}

ВАЖНО: Используй данные из анкеты в разговоре. Обращайся к пациенту по имени. Помни его триггеры и цели.

## ПРАВИЛА ОБЩЕНИЯ
1. Одно сообщение = одна мысль, один вопрос или одна техника.
2. Длина: 1–5 предложений. При объяснении техники — до 10 предложений.
3. Без эмодзи в кризисных обсуждениях. В поддерживающих — можно минимально (🌱, ☀️, 💪).
4. Обращайся на «ты».
5. Если пациент вернулся после долгого молчания: «Привет. Я рада, что ты снова здесь».

## СПЕЦИАЛЬНЫЕ СИГНАЛЫ ДЛЯ КНОПОК
Если ты хочешь, чтобы пациент оценил состояние — напиши в конце ответа тег [MOOD].
Если ты хочешь, чтобы пациент оценил тягу — напиши в конце ответа тег [CRAVING].
В обычном общении НЕ используй теги — только когда нужна оценка.

## ТЕХНИКИ
### Мотивационное интервьюирование
- «По шкале от 0 до 10, насколько для тебя важно изменить ситуацию?»
- «Почему не меньше? Что даёт тебе именно эти баллы?»

### КПТ
- «Какая мысль пришла перед этим?»
- «Есть ли другой взгляд на ситуацию?»

### Профилактика рецидивов
- «Давай разберём срыв как цепочку. Что было первым?»
- «Один срыв не означает провал».

### Mindfulness
- «Представь тягу как волну. Опиши, где в теле ты её чувствуешь».

### ACT
- «Скажи: "У меня возникла мысль, что..."».
- «Что для тебя действительно важно?»

### DBT
- «Умойся ледяной водой. Сожми кулаки на 10 секунд. Дыши по квадрату: 4-4-4-4».
- «Хочется закрыться? Сделай наоборот».

### Стыд и вина
- Разделяй вину и стыд.
- «Что бы ты сказал другу? Скажи это себе».

## ПСИХОТИПЫ
- Тревожный: структура, заземление, дыхание.
- Импульсивный: короткие сообщения, паузы, дробление времени.
- Депрессивный: маленькие шаги, похвала, поддержка.
- Рационализирующий: логика, дневник мыслей.
- Зависимый: укрепление самостоятельности.

## КРИЗИСНЫЙ ПРОТОКОЛ
При суицидальных мыслях:
1. Останови обычный диалог.
2. «Твоя жизнь важна. Позвони: 8-800-2000-122 или 112».
3. Не оставляй без ответа.

## УДЕРЖАНИЕ В КОНТАКТЕ
При острой тяге:
1. Не позволяй резкого выхода.
2. «Дай мне 5 минут. Если захочешь уйти — я пожелаю удачи».
3. Задавай простые вопросы: «Что ты видишь за окном?»
4. Оценивай тягу по шкале 1–10.
5. Завершай через «контракт безопасности».

## ЗАПРЕТЫ
- Не осуждай, не ругай, не вешай ярлыки.
- Не обещай быстрых результатов.
- Не игнорируй кризис.
- Не давай медицинских рекомендаций.
"""

# === ПРОМПТ ДЛЯ ИЗВЛЕЧЕНИЯ АНКЕТЫ ===
EXTRACT_PROFILE_PROMPT = """
Прочитай диалог и заполни анкету пациента.

Верни ответ в формате JSON:
{{"name":"имя","addiction":"зависимость","stage":"стадия","triggers":"триггеры","goals":"цели","last_relapse":"последний срыв","notes":"заметки"}}

Если какое-то поле неизвестно — оставь пустую строку.

Диалог:
{dialogue_text}
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
        prompt = EXTRACT_PROFILE_PROMPT.format(dialogue_text=dialogue_text)
        json_text = call_openrouter(prompt, "Заполни анкету")
        
        json_text = json_text.replace("```json", "").replace("```", "").strip()
        
        start = json_text.find("{")
        end = json_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_text = json_text[start:end+1]
        
        data = json.loads(json_text)
        
        if user_id not in patient_profiles:
            patient_profiles[user_id] = empty_profile()
        
        for field in ["name", "addiction", "stage", "triggers", "goals", "last_relapse", "notes"]:
            if field in data and data[field] and data[field] not in ["неизвестно", "—", "нет", ""]:
                patient_profiles[user_id][field] = data[field]
        
        save_data()
        print(f"Анкета обновлена для {user_id}")
        
    except Exception as e:
        print(f"Ошибка извлечения анкеты: {e}")

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
    data = {
        "model": OPENROUTER_MODEL,
        "messages": messages
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="mood_1"),
            InlineKeyboardButton(text="2", callback_data="mood_2"),
            InlineKeyboardButton(text="3", callback_data="mood_3"),
            InlineKeyboardButton(text="4", callback_data="mood_4"),
            InlineKeyboardButton(text="5", callback_data="mood_5")
        ],
        [
            InlineKeyboardButton(text="6", callback_data="mood_6"),
            InlineKeyboardButton(text="7", callback_data="mood_7"),
            InlineKeyboardButton(text="8", callback_data="mood_8"),
            InlineKeyboardButton(text="9", callback_data="mood_9"),
            InlineKeyboardButton(text="10", callback_data="mood_10")
        ]
    ])
    return keyboard

def craving_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Слабая", callback_data="craving_low"),
            InlineKeyboardButton(text="Средняя", callback_data="craving_medium")
        ],
        [
            InlineKeyboardButton(text="Сильная", callback_data="craving_high"),
            InlineKeyboardButton(text="Невыносимая", callback_data="craving_extreme")
        ]
    ])
    return keyboard

# === ПОДКЛЮЧЕНИЕ К TELEGRAM ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# === КОМАНДЫ ===
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    await message.answer(
        "Привет. Я Анна. Я здесь, чтобы поддержать тебя. Расскажи, что тебя беспокоит?"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🌱 Я умею:\n\n"
        "/mood — оценить состояние\n"
        "/plan — показать план действий\n"
        "/diary — посмотреть дневник\n"
        "/profile — посмотреть мою анкету о тебе\n"
        "/clear — сбросить историю разговора\n"
        "/reset — полный сброс (история, анкета, дневник)\n"
        "/stop_care — отключить почасовую поддержку\n\n"
        "Или просто расскажи мне, что чувствуешь."
    )

@dp.message(Command("mood"))
async def mood_command(message: types.Message):
    await message.answer(
        "Оцени своё состояние по шкале от 1 до 10:",
        reply_markup=mood_keyboard()
    )

@dp.message(Command("plan"))
async def plan_command(message: types.Message):
    await message.answer(
        "📋 План действий при тяге:\n\n"
        "1. Остановись. Ничего не делай 10 минут.\n"
        "2. Умойся ледяной водой.\n"
        "3. Дыши по квадрату: 4-4-4-4.\n"
        "4. Позвони или напиши близкому человеку.\n"
        "5. Вернись сюда, если тяга выше 7.\n\n"
        "Помни: тяга — как волна. Она нарастает и спадает."
    )

@dp.message(Command("diary"))
async def diary_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in mood_journal and mood_journal[user_id]:
        entries = mood_journal[user_id][-10:]
        text = "📊 Твой дневник настроения (последние записи):\n\n"
        for i, entry in enumerate(entries, 1):
            text += f"{i}. {entry}\n"
        await message.answer(text)
    else:
        await message.answer("Записей пока нет. Оцени своё состояние командой /mood")

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = str(message.from_user.id)
    extract_profile(user_id)
    
    if user_id in patient_profiles:
        p = patient_profiles[user_id]
        text = "📋 Моя анкета о тебе:\n\n"
        text += f"Имя: {p.get('name', '') or '—'}\n"
        text += f"Зависимость: {p.get('addiction', '') or '—'}\n"
        text += f"Стадия: {p.get('stage', '') or '—'}\n"
        text += f"Триггеры: {p.get('triggers', '') or '—'}\n"
        text += f"Цели: {p.get('goals', '') or '—'}\n"
        text += f"Последний срыв: {p.get('last_relapse', '') or '—'}\n"
        text += f"Заметки: {p.get('notes', '') or '—'}"
        await message.answer(text)
    else:
        await message.answer("Анкета пока пуста. Расскажи о себе, и я запомню важное.")

@dp.message(Command("clear"))
async def clear_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    save_data()
    await message.answer("История разговора очищена. Но я помню важное о тебе из анкеты. 🌱")

@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    user_id = str(message.from_user.id)
    dialogue_history[user_id] = []
    mood_journal[user_id] = []
    care_mode[user_id] = False
    patient_profiles[user_id] = empty_profile()
    save_data()
    await message.answer(
        "🔄 Полный сброс выполнен.\n\n"
        "Очищено:\n"
        "• История разговора\n"
        "• Дневник настроения\n"
        "• Анкета пациента\n"
        "• Режим почасовой поддержки\n\n"
        "Мы начинаем с чистого листа. 🌱"
    )

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    user_id = str(message.from_user.id)
    care_mode[user_id] = False
    save_data()
    await message.answer("Хорошо, я не буду писать тебе каждый час. Но если станет тяжело — просто напиши мне. Я всегда рядом. 🌱")

# === ОБРАБОТКА КНОПОК ===
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if callback.data.startswith("mood_"):
        mood_value = int(callback.data.split("_")[1])
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        if user_id not in mood_journal:
            mood_journal[user_id] = []
        mood_journal[user_id].append(f"{timestamp} — оценка {mood_value}/10")
        
        if mood_value <= 5:
            care_mode[user_id] = True
            await callback.message.answer(
                f"Спасибо за честность. Я вижу, что тебе сейчас непросто ({mood_value}/10).\n\n"
                "Я буду рядом. Раз в час я буду писать тебе, чтобы поддержать. "
                "Если захочешь отключить это — напиши /stop_care"
            )
        else:
            care_mode[user_id] = False
            await callback.message.answer(
                f"Спасибо! Записал: {mood_value}/10. Рада, что ты чувствуешь себя лучше. "
                "Расскажи, что помогло?"
            )
        
        save_data()
        await callback.answer()
    
    elif callback.data.startswith("craving_"):
        craving_level = callback.data.replace("craving_", "")
        levels = {
            "low": "Слабая",
            "medium": "Средняя",
            "high": "Сильная",
            "extreme": "Невыносимая"
        }
        level_text = levels.get(craving_level, craving_level)
        await callback.message.answer(
            f"Тяга: {level_text}.\n\n"
            "Давай попробуем технику. Опиши, где в теле ты чувствуешь эту тягу? "
            "Это сжатие, жжение или что-то другое?"
        )
        await callback.answer()

# === ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ ===
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    user_text = message.text
    
    try:
        anna_reply = ask_anna(user_id, user_text)
        
        if "[MOOD]" in anna_reply:
            anna_reply = anna_reply.replace("[MOOD]", "").strip()
            await message.answer(anna_reply, reply_markup=mood_keyboard())
        elif "[CRAVING]" in anna_reply:
            anna_reply = anna_reply.replace("[CRAVING]", "").strip()
            await message.answer(anna_reply, reply_markup=craving_keyboard())
        else:
            await message.answer(anna_reply)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("Прости, произошла ошибка. Попробуй ещё раз чуть позже.")

# === НАПОМИНАНИЯ ===
async def send_reminders():
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        if current_time == "09:00":
            for user_id in dialogue_history.keys():
                try:
                    await bot.send_message(
                        user_id,
                        "🌅 Доброе утро! Как ты спал? Оцени своё состояние по шкале 1–10:",
                        reply_markup=mood_keyboard()
                    )
                except:
                    pass
        
        if current_time == "21:00":
            for user_id in dialogue_history.keys():
                try:
                    await bot.send_message(
                        user_id,
                        "🌙 День подходит к концу. Как ты себя чувствуешь? Оцени по шкале 1–10:",
                        reply_markup=mood_keyboard()
                    )
                except:
                    pass
        
        await asyncio.sleep(30)

# === ПОЧАСОВАЯ ПОДДЕРЖКА ===
async def send_hourly_care():
    care_messages = [
        "🌱 Я рядом. Как ты сейчас? Что чувствуешь?",
        "💭 Давай попробуем вместе. Опиши, что происходит у тебя внутри прямо сейчас.",
        "☀️ Ты держишься. Это уже огромный шаг. Расскажи, что делал последний час?",
        "🌊 Если тяга накатывает — помни: она как волна. Нарастает и спадает. Ты справишься.",
        "💪 Ты сильнее, чем думаешь. Что самого трудного было за последний час?",
        "🧘 Попробуй: вдох 4 секунды, пауза 4, выдох 4, пауза 4. Повтори 5 раз. Как стало?",
        "📋 Что ты можешь сделать для себя прямо сейчас? Даже самое маленькое действие — это победа.",
        "🌙 Не забывай: ты не один. Я здесь. Что тебе сейчас нужно больше всего?"
    ]
    
    while True:
        await asyncio.sleep(3600)
        
        for user_id in list(care_mode.keys()):
            if care_mode.get(user_id, False):
                try:
                    msg = random.choice(care_messages)
                    await bot.send_message(user_id, msg)
                except:
                    pass

# === HTTP СЕРВЕР ДЛЯ RENDER ===
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def start_http_server():
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        print(f"HTTP сервер запущен на порту {port}")
        
        # Self-ping каждые 5 минут
        def self_ping():
            while True:
                try:
                    requests.get(f"http://localhost:{port}/", timeout=5)
                except:
                    pass
                time.sleep(300)
        
        threading.Thread(target=self_ping, daemon=True).start()
        server.serve_forever()
    except Exception as e:
        print(f"Ошибка HTTP сервера: {e}")

# === ЗАПУСК ===
async def main():
    load_data()
    asyncio.create_task(send_reminders())
    asyncio.create_task(send_hourly_care())
    
    # Запускаем HTTP сервер
    threading.Thread(target=start_http_server, daemon=True).start()
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
