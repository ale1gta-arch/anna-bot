import asyncio, random, json, os, re, threading, time
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

# Глобальные переменные
dialogue_history = {}
MAX_HISTORY = 50
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
last_activity = {}
user_consent = {}
emotion_step = {}
diary_step = {}
daily_reminders = {}
crisis_step = {}

# КРИЗИСНЫЕ СЛОВА
CRISIS_WORDS = ["не хочу жить", "не хочу больше жить", "хочу умереть", "хочу покончить", "покончить с собой", "суицид", "самоубийств", "убить себя", "нет смысла жить", "всё закончилось", "не могу больше жить", "устал жить", "лучше бы меня не было", "хочу исчезнуть"]

# УДАЛЕНИЕ ДАННЫХ
DELETE_WORDS = ["удали данные", "удали всё", "сотри всё", "стереть данные", "удали мои данные", "забудь всё", "удали информацию"]

HOTLINES = """📞 Телефоны помощи:

🚨 Экстренная помощь: 112
🧠 Психологическая помощь: 8-800-2000-122
💚 Москва: 8-495-989-50-50

🌍 Международные:
• США: 1-800-662-4357
• Великобритания: 0300 123 3393
• Германия: 0800 111 0 111"""

PSYCHOEDUCATION = {
    "neuro": """🧠 *Нейробиология зависимости*

Зависимость — это не слабость воли, а изменение работы мозга.

1️⃣ *Дофамин.* Вещество вызывает выброс в 2–10 раз больше естественного.

2️⃣ *Толерантность.* Рецепторы привыкают, нужна большая доза.

3️⃣ *Абстиненция.* Без вещества дофамин падает → тревога, апатия, тяга.

4️⃣ *Тяга.* Биологический сигнал, волнами 10–20 минут.

5️⃣ *Нейропластичность.* Мозг восстанавливается за 3–6 месяцев трезвости.""",
    "cbt": """🧩 *Основы КПТ*

Эмоции зависят не от событий, а от их интерпретации.

🔗 Ситуация → Мысль → Эмоция → Поведение

1️⃣ Замечаем автоматические мысли.
2️⃣ Проверяем: «Доказательства за и против?»
3️⃣ Заменяем на точные.
4️⃣ Меняем поведение.""",
    "dbt": """🧘 *Основы ДБТ*

Баланс между принятием и изменениями.

4 модуля:
1️⃣ Осознанность (5-4-3-2-1).
2️⃣ Стрессоустойчивость (TIP).
3️⃣ Эмоциональная регуляция.
4️⃣ Межличностная эффективность (DEAR MAN).

💡 «Я принимаю себя и одновременно меняюсь»."""
}

def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times, user_timezones, patient_memory, interview_step, last_activity, user_consent, emotion_step, diary_step, daily_reminders, crisis_step
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                dialogue_history = d.get("dialogue_history", {})
                patient_profiles = d.get("patient_profiles", {})
                mood_journal = d.get("mood_journal", {})
                care_mode = d.get("care_mode", {})
                sober_tracker = d.get("sober_tracker", {})
                user_goals = d.get("user_goals", {})
                congratulated = d.get("congratulated", {})
                relapse_times = d.get("relapse_times", [])
                user_timezones = d.get("user_timezones", {})
                patient_memory = d.get("patient_memory", {})
                interview_step = d.get("interview_step", {})
                last_activity = d.get("last_activity", {})
                user_consent = d.get("user_consent", {})
                emotion_step = d.get("emotion_step", {})
                diary_step = d.get("diary_step", {})
                daily_reminders = d.get("daily_reminders", {})
                crisis_step = d.get("crisis_step", {})
        except: pass

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"dialogue_history": dialogue_history, "patient_profiles": patient_profiles, "mood_journal": mood_journal, "care_mode": care_mode, "sober_tracker": sober_tracker, "user_goals": user_goals, "congratulated": congratulated, "relapse_times": relapse_times, "user_timezones": user_timezones, "patient_memory": patient_memory, "interview_step": interview_step, "last_activity": last_activity, "user_consent": user_consent, "emotion_step": emotion_step, "diary_step": diary_step, "daily_reminders": daily_reminders, "crisis_step": crisis_step}, f, ensure_ascii=False, indent=2)

def empty_profile(): return {"name": "", "gender": "", "addiction": "", "stage": "", "triggers": "", "goals": "", "last_relapse": "", "notes": ""}
def empty_memory(): return {"first_contact": datetime.now().strftime("%d.%m.%Y"), "sessions": 0, "preferred_techniques": [], "important_events": [], "progress_notes": []}

def update_memory(user_id, field, value):
    if user_id not in patient_memory: patient_memory[user_id] = empty_memory()
    if field == "progress_notes":
        patient_memory[user_id]["progress_notes"].append(f"{datetime.now().strftime('%d.%m.%Y')}: {value}")
        patient_memory[user_id]["progress_notes"] = patient_memory[user_id]["progress_notes"][-10:]
    save_data()

ANNA_PROMPT = """Ты — Анна Соколова, виртуальный психотерапевт по зависимостям. Ты программа, не человек.

## ПОЛ ПАЦИЕНТА: {gender}
Если «мужской» — говори «ты мог», «ты справился». Если «женский» — «ты могла», «ты справилась». НИКОГДА не путай. Ты сама — женщина.

## СТИЛЬ
- Эмпатичная, но без имитации биографии.
- Активно слушай, задавай уточняющие вопросы.
- Отражай эмоции: «Я слышу, что ты злишься».
- 3–10 предложений.

## ПСИХООБРАЗОВАНИЕ
- Нейробиология: дофамин, толерантность, тяга как волна.
- КПТ: Ситуация → Мысль → Эмоция → Поведение.
- ДБТ: 4 модуля навыков.

## КРИЗИС
При суицидальных мыслях НЕ спрашивай оценку. Спроси: «Есть ли план? Есть ли доступ к средствам?» Если да — дай 112 и 8-800-2000-122, скажи «Я не могу продолжать терапию».

## УДАЛЕНИЕ ДАННЫХ
Если просят удалить — скажи: «Введи /reset. После подтверждения всё будет стёрто».

## ОФФТОП
На анекдоты/игры — мягко возвращай к терапии.

## ПАНИКА
Одно короткое действие: «Дыши со мной: вдох 4, задержка 4, выдох 4. Я жду».

## АНКЕТА
Имя: {name}
Зависимость: {addiction}
Триггеры: {triggers}
Цели: {goals}

## ПАМЯТЬ
Контакт: {first_contact}
Сессий: {sessions}
Прогресс: {progress}

## СИГНАЛЫ
[MOOD] — при вопросе об оценке.
[CRAVING] — при вопросе о тяге.

## ЗАПРЕТЫ
Не осуждай, не давай медсоветов, не ставь диагнозы."""

def build_prompt(user_id):
    if user_id not in patient_profiles: patient_profiles[user_id] = empty_profile()
    if user_id not in patient_memory: patient_memory[user_id] = empty_memory()
    p = patient_profiles[user_id]; m = patient_memory[user_id]
    return ANNA_PROMPT.format(
        name=p.get("name", "") or "неизвестно",
        gender=p.get("gender", "") or "не указан",
        addiction=p.get("addiction", "") or "неизвестно",
        triggers=p.get("triggers", "") or "неизвестно",
        goals=p.get("goals", "") or "неизвестно",
        first_contact=m.get("first_contact", "неизвестно"),
        sessions=m.get("sessions", 0),
        progress="; ".join(m.get("progress_notes", [])) or "пока нет")

def call_ai(system, user_text):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_text}], "max_tokens": 800}
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
    return r.json()["choices"][0]["message"]["content"]

def fix_gender(uid, text):
    if uid not in patient_profiles: return text
    g = patient_profiles[uid].get("gender", "")
    if g == "мужской":
        for k, v in {"ты могла": "ты мог", "ты справилась": "ты справился", "ты сделала": "ты сделал", "ты сама": "ты сам", "поделилась": "поделился", "обратила": "обратил", "поняла": "понял", "хотела": "хотел", "была": "был"}.items():
            text = text.replace(k, v)
    elif g == "женский":
        for k, v in {"ты мог": "ты могла", "ты справился": "ты справилась", "ты сделал": "ты сделала", "ты сам": "ты сама", "поделился": "поделилась", "обратил": "обратила", "понял": "поняла", "хотел": "хотела", "был": "была"}.items():
            text = text.replace(k, v)
    return text

def ask_anna(user_id, user_text):
    uid = str(user_id)
    if uid not in dialogue_history: dialogue_history[uid] = []
    if uid not in patient_memory: patient_memory[uid] = empty_memory()
    h = dialogue_history[uid]
    h.append({"role": "user", "content": user_text})
    if len(h) > MAX_HISTORY: h = h[-MAX_HISTORY:]
    patient_memory[uid]["sessions"] = patient_memory[uid].get("sessions", 0) + 1
    msgs = [{"role": "system", "content": build_prompt(uid)}] + h
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {"model": OPENROUTER_MODEL, "messages": msgs, "max_tokens": 800}
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
    reply = r.json()["choices"][0]["message"]["content"]
    reply = fix_gender(uid, reply)
    h.append({"role": "assistant", "content": reply})
    dialogue_history[uid] = h
    save_data()
    return reply

def mood_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i), callback_data=f"mood_{i}") for i in range(1, 6)], [InlineKeyboardButton(text=str(i), callback_data=f"mood_{i}") for i in range(6, 11)]])

def craving_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Слабая", callback_data="craving_low"), InlineKeyboardButton(text="Средняя", callback_data="craving_medium")], [InlineKeyboardButton(text="Сильная", callback_data="craving_high"), InlineKeyboardButton(text="Невыносимая", callback_data="craving_extreme")]])

def gender_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")], [KeyboardButton(text="Не важно")]], resize_keyboard=True)

def main_menu_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚨 Мне плохо"), KeyboardButton(text="🆘 Я на грани")], [KeyboardButton(text="📊 Состояние"), KeyboardButton(text="🧠 Что я чувствую?")], [KeyboardButton(text="📝 Дневник"), KeyboardButton(text="🎯 Цели")], [KeyboardButton(text="📚 Знания"), KeyboardButton(text="🧘 Дыхание")], [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="⚙️ Настройки")]], resize_keyboard=True)

def crisis_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔥 У меня тяга")], [KeyboardButton(text="😰 Паника")], [KeyboardButton(text="😢 Очень грустно")], [KeyboardButton(text="💔 Я сорвался")], [KeyboardButton(text="📞 Позвонить")], [KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)

def settings_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⏰ Время")], [KeyboardButton(text="🔕 Стоп поддержку")], [KeyboardButton(text="🗑 Удалить данные")], [KeyboardButton(text="⬅️ Назад в меню")]], resize_keyboard=True)

def emotion_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Грусть"), KeyboardButton(text="Тревога")], [KeyboardButton(text="Злость"), KeyboardButton(text="Одиночество")], [KeyboardButton(text="Стыд"), KeyboardButton(text="Страх")], [KeyboardButton(text="Радость"), KeyboardButton(text="Усталость")], [KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)

def education_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🧠 Нейробиология"), KeyboardButton(text="🧩 КПТ")], [KeyboardButton(text="🧘 ДБТ"), KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)

def get_patient_time(uid):
    return datetime.now(timezone.utc) + timedelta(hours=user_timezones.get(uid, 0))

def parse_time(text):
    m = re.match(r'^(\d{1,2}):(\d{2})$', text.strip())
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            pdt = datetime.now(timezone.utc).replace(hour=h, minute=mn, second=0, microsecond=0)
            diff = (pdt - datetime.now(timezone.utc)).total_seconds() / 3600
            off = round(diff)
            if -12 <= off <= 14: return off
    return None

def is_crisis(text):
    t = text.lower()
    return any(w in t for w in CRISIS_WORDS)

def is_delete(text):
    t = text.lower()
    return any(w in t for w in DELETE_WORDS)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    uid = str(m.from_user.id)
    dialogue_history[uid] = []
    if uid not in patient_memory: patient_memory[uid] = empty_memory()
    if uid not in patient_profiles: patient_profiles[uid] = empty_profile()
    await m.answer("Я — виртуальный помощник Анна, а не врач. Не ставлю диагнозы, не назначаю лечение.\n\nДанные конфиденциальны. Для удаления: /reset.\n\nНажмите «Согласен(а)».", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Согласен(а)", callback_data="consent_yes")], [InlineKeyboardButton(text="Не согласен(а)", callback_data="consent_no")]]))

@dp.callback_query()
async def consent_cb(c: types.CallbackQuery):
    uid = str(c.from_user.id)
    if c.data == "consent_yes":
        user_consent[uid] = True; save_data()
        interview_step[uid] = "name"
        await c.message.answer("Спасибо! Как тебя зовут?")
        await c.answer()
    elif c.data == "consent_no":
        await c.message.answer("Хорошо. Если передумаешь — /start.")
        await c.answer()
    else:
        await callback_handler(c)

@dp.message(Command("menu"))
async def menu_cmd(m: types.Message): await m.answer("Меню:", reply_markup=main_menu_kb())

@dp.message(Command("crisis"))
async def crisis_cmd(m: types.Message): await m.answer("Кризисное меню:", reply_markup=crisis_kb())

@dp.message(Command("mood"))
async def mood_cmd(m: types.Message): await m.answer("Оцени состояние:", reply_markup=mood_kb())

@dp.message(Command("help"))
async def help_cmd(m: types.Message): await m.answer("ℹ️ Контакты:\n\n" + HOTLINES + "\n\nКоманды:\n/menu /crisis /mood /reset")

@dp.message(Command("reset"))
async def reset_cmd(m: types.Message):
    uid = str(m.from_user.id)
    await m.answer("Удалить все данные? Напишите «Да, удалить» или «Удалить».")
    interview_step[uid] = "confirm_reset"

@dp.message(Command("education"))
async def edu_cmd(m: types.Message): await m.answer("📚 Что узнать?", reply_markup=education_kb())

@dp.message(lambda m: m.voice is not None)
async def voice_handler(m: types.Message): await m.answer("Я слышу тебя. Опиши текстом. 💚")

@dp.message()
async def handle(m: types.Message):
    uid = str(m.from_user.id)
    text = m.text

    # Согласие
    if uid not in user_consent or not user_consent[uid]:
        if text == "Согласен(а)":
            user_consent[uid] = True; save_data()
            interview_step[uid] = "name"
            await m.answer("Спасибо! Как тебя зовут?"); return
        elif text == "Не согласен(а)":
            await m.answer("Хорошо. Если передумаешь — /start."); return
        else:
            await m.answer("Дай согласие или /start."); return

    # КРИЗИС
    if is_crisis(text):
        crisis_step[uid] = "asked_plan"; save_data()
        await m.answer(f"Алексей, я слышу тебя. Это очень серьёзно.\n\nОтветь честно:\n1. Есть ли конкретный план?\n2. Есть ли доступ к средствам?\n\nОт этого зависит моя помощь.")
        return

    if crisis_step.get(uid) == "asked_plan":
        t = text.lower()
        if any(w in t for w in ["да", "есть", "yes", "знаю"]):
            crisis_step[uid] = "high"
            save_data()
            await m.answer("Это критично. Я не могу продолжать терапию, пока ты в опасности.\n\n🚨 Позвони прямо сейчас:\n📞 112\n📞 8-800-2000-122\n\nПопроси близкого быть рядом. Сделай это сейчас.")
        else:
            crisis_step[uid] = "low"
            save_data()
            await m.answer("Спасибо за честность. Позвони на бесплатную линию: 8-800-2000-122 (круглосуточно).\n\nРасскажи, что привело к таким мыслям?")
        return

    if crisis_step.get(uid) == "high":
        await m.answer("Алексей, я всё ещё здесь. Позвони 112 или 8-800-2000-122 прямо сейчас. Это минута, но она может спасти жизнь.\n\nЯ не могу продолжать, пока ты в опасности. Позвони.")
        return

    # УДАЛЕНИЕ ДАННЫХ
    if is_delete(text):
        await m.answer("Алексей, я уважаю твоё право. Введи /reset — после подтверждения всё будет стёрто (история, анкета, дневник).")
        return

    # Подтверждение сброса
    if interview_step.get(uid) == "confirm_reset":
        t = text.lower().strip()
        if t in ["да, удалить", "да удалить", "удалить", "да", "подтверждаю", "yes"]:
            for k in list(dialogue_history.keys()):
                if k == uid: dialogue_history.pop(uid, None)
            mood_journal.pop(uid, None); care_mode.pop(uid, None); patient_profiles.pop(uid, None)
            patient_memory.pop(uid, None); sober_tracker.pop(uid, None); user_goals.pop(uid, None)
            user_timezones.pop(uid, None); interview_step.pop(uid, None); user_consent.pop(uid, None)
            emotion_step.pop(uid, None); diary_step.pop(uid, None); crisis_step.pop(uid, None)
            daily_reminders.pop(uid, None); save_data()
            await m.answer("Все данные удалены. /start для начала."); return
        else:
            interview_step.pop(uid, None)
            await m.answer("Сброс отменён."); return

    # ИНТЕРВЬЮ
    step = interview_step.get(uid)
    if step == "name":
        patient_profiles[uid]["name"] = text.strip(); save_data()
        interview_step[uid] = "gender"
        await m.answer(f"Приятно познакомиться, {text.strip()}! 🌱\n\nКак к тебе обращаться?", reply_markup=gender_kb()); return
    if step == "gender":
        if text in ["Мужской", "Женский", "Не важно"]:
            patient_profiles[uid]["gender"] = "мужской" if text == "Мужской" else ("женский" if text == "Женский" else "не указан")
            save_data(); interview_step[uid] = "problem"
            await m.answer("Спасибо. С чем хочешь работать?")
        else:
            await m.answer("Выбери из кнопок.", reply_markup=gender_kb())
        return
    if step == "problem":
        patient_profiles[uid]["addiction"] = text.strip(); save_data()
        interview_step[uid] = "level"
        await m.answer("Оцени, насколько это беспокоит, от 1 до 10:", reply_markup=mood_kb()); return
    if step == "time":
        off = parse_time(text)
        if off is not None:
            user_timezones[uid] = off; save_data(); interview_step[uid] = "done"
            await m.answer("✅ Время сохранено. Расскажи, что беспокоит больше всего?", reply_markup=main_menu_kb())
        else:
            await m.answer("Формат ЧЧ:ММ, например 14:30")
        return

    # НАЗАД
    if text in ["⬅️ Назад", "⬅️ Назад в меню", "⬅️ Назад в главное меню"]:
        interview_step.pop(uid, None); emotion_step.pop(uid, None); diary_step.pop(uid, None)
        await m.answer("Меню:", reply_markup=main_menu_kb()); return

    # МЕНЮ
    if text == "🚨 Мне плохо": await m.answer("Что происходит?", reply_markup=crisis_kb()); return
    if text == "🆘 Я на грани":
        await m.answer("Продержимся вместе:\n1. Умойся ледяной водой.\n2. Дыши 4-4-4-4.\n3. Позвони близкому.\n\nТяга — волна, нарастает и спадает.", reply_markup=craving_kb()); return
    if text == "📊 Состояние":
        d = 0
        if uid in sober_tracker: d = (datetime.now() - datetime.strptime(sober_tracker[uid], "%Y-%m-%d")).days
        lm = mood_journal.get(uid, [])[-5:]
        await m.answer(f"📊 Состояние:\n\nДней чистоты: {d}\n\nПоследние оценки:\n" + ("\n".join(lm) if lm else "нет"), reply_markup=main_menu_kb()); return
    if text == "🧠 Что я чувствую?":
        emotion_step[uid] = "choose"
        await m.answer("Какое чувство?", reply_markup=emotion_kb()); return
    if text == "📝 Дневник":
        diary_step[uid] = "situation"
        await m.answer("Шаг 1/4: Опиши ситуацию."); return
    if text == "🎯 Цели":
        g = user_goals.get(uid, "")
        await m.answer(f"Цели:\n{g}" if g else "Напиши /goals <цель>", reply_markup=main_menu_kb()); return
    if text == "📚 Знания": await m.answer("📚 Что узнать?", reply_markup=education_kb()); return
    if text == "🧠 Нейробиология": await m.answer(PSYCHOEDUCATION["neuro"], reply_markup=education_kb()); return
    if text == "🧩 КПТ": await m.answer(PSYCHOEDUCATION["cbt"], reply_markup=education_kb()); return
    if text == "🧘 ДБТ": await m.answer(PSYCHOEDUCATION["dbt"], reply_markup=education_kb()); return
    if text == "🧘 Дыхание":
        await m.answer("🧘 Дыхание 4-4-4-4:\nВдох 4 — пауза 4 — выдох 4 — пауза 4.\nПовтори 5 раз.", reply_markup=main_menu_kb()); return
    if text == "ℹ️ Помощь": await m.answer(HOTLINES, reply_markup=main_menu_kb()); return
    if text == "⚙️ Настройки": await m.answer("Настройки:", reply_markup=settings_kb()); return
    if text == "🔥 У меня тяга": await m.answer("Оцени силу тяги:", reply_markup=craving_kb()); return
    if text == "😰 Паника":
        await m.answer("Это паника. Пройдёт за 10–20 минут. Ты в безопасности.\n\nДыши со мной: вдох 4, задержка 4, выдох 4. Повтори 3 раза. Я жду.", reply_markup=crisis_kb()); return
    if text == "😢 Очень грустно":
        crisis_step[uid] = "asked_plan"; save_data()
        await m.answer("Мне жаль. Есть ли мысли навредить себе? (да/нет)"); return
    if text == "💔 Я сорвался":
        sober_tracker[uid] = datetime.now().strftime("%Y-%m-%d")
        relapse_times.append(datetime.now().strftime("%H:%M"))
        update_memory(uid, "progress_notes", "Срыв"); save_data()
        await m.answer("Спасибо за честность. Что было перед срывом?", reply_markup=crisis_kb()); return
    if text == "📞 Позвонить": await m.answer(HOTLINES, reply_markup=crisis_kb()); return
    if text == "⏰ Время": await m.answer("Напиши время ЧЧ:ММ"); interview_step[uid] = "time"; return
    if text == "🔕 Стоп поддержку": care_mode[uid] = False; save_data(); await m.answer("Поддержка остановлена.", reply_markup=main_menu_kb()); return
    if text == "🗑 Удалить данные": await m.answer("Удалить всё? Напиши «Да, удалить»."); interview_step[uid] = "confirm_reset"; return

    # ЭМОЦИИ
    if emotion_step.get(uid) == "choose":
        if text in ["Грусть", "Тревога", "Злость", "Одиночество", "Стыд", "Страх", "Радость", "Усталость"]:
            emotion_step[uid] = "intensity"
            if uid not in patient_memory: patient_memory[uid] = empty_memory()
            patient_memory[uid]["last_emotion"] = text; save_data()
            await m.answer(f"Выбрано: {text}. Оцени интенсивность:", reply_markup=mood_kb())
        else:
            await m.answer("Выбери из кнопок.", reply_markup=emotion_kb())
        return

    # ДНЕВНИК
    if diary_step.get(uid):
        s = diary_step[uid]
        if uid not in patient_memory: patient_memory[uid] = empty_memory()
        if s == "situation": patient_memory[uid]["d_s"] = text; diary_step[uid] = "thought"; await m.answer("Шаг 2/4: Мысль?"); return
        if s == "thought": patient_memory[uid]["d_t"] = text; diary_step[uid] = "emotion"; await m.answer("Шаг 3/4: Эмоция?"); return
        if s == "emotion": patient_memory[uid]["d_e"] = text; diary_step[uid] = "action"; await m.answer("Шаг 4/4: Действие?"); return
        if s == "action":
            entry = f"Ситуация: {patient_memory[uid].get('d_s','')}\nМысль: {patient_memory[uid].get('d_t','')}\nЭмоция: {patient_memory[uid].get('d_e','')}\nДействие: {text}"
            if uid not in mood_journal: mood_journal[uid] = []
            mood_journal[uid].append(f"[Дневник] {entry}")
            diary_step.pop(uid, None)
            for k in ["d_s", "d_t", "d_e"]: patient_memory[uid].pop(k, None)
            save_data(); await m.answer("Запись сохранена. 💚", reply_markup=main_menu_kb()); return

    # Обычный диалог
    try:
        r = ask_anna(uid, text)
        clean = r.replace("[MOOD]", "").replace("[CRAVING]", "").strip()
        if "[CRAVING]" in r: await m.answer(clean, reply_markup=craving_kb())
        elif "[MOOD]" in r: await m.answer(clean, reply_markup=mood_kb())
        else: await m.answer(clean)
    except Exception as e:
        print(f"Err: {e}"); await m.answer("Ошибка. Попробуй ещё раз.")

@dp.callback_query()
async def callback_handler(c: types.CallbackQuery):
    uid = str(c.from_user.id)
    d = c.data
    if d.startswith("mood_"):
        v = int(d.split("_")[1])
        if uid not in mood_journal: mood_journal[uid] = []
        mood_journal[uid].append(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} — {v}/10")
        if interview_step.get(uid) == "level":
            if uid not in patient_profiles: patient_profiles[uid] = empty_profile()
            patient_profiles[uid]["stage"] = f"Уровень: {v}/10"; save_data()
            interview_step[uid] = "time"
            await c.message.answer("Спасибо. Сколько у тебя сейчас времени? ЧЧ:ММ")
        elif emotion_step.get(uid) == "intensity":
            e = patient_memory[uid].get("last_emotion", "")
            if e: mood_journal[uid].append(f"[Эмоция] {e}: {v}/10")
            emotion_step.pop(uid, None); save_data()
            await c.message.answer(f"Записал: {e} ({v}/10). 💚", reply_markup=main_menu_kb())
        else:
            if v <= 5: care_mode[uid] = True; await c.message.answer(f"Спасибо ({v}/10). Я рядом. 💚")
            else: care_mode[uid] = False; await c.message.answer(f"Отлично! {v}/10. ☀️")
        save_data(); await c.answer()
    elif d.startswith("craving_"):
        lv = {"low": "Слабая", "medium": "Средняя", "high": "Сильная", "extreme": "Невыносимая"}
        l = lv.get(d.replace("craving_", ""), "")
        await c.message.answer(f"Тяга: {l}. Где в теле? 🌊")
        await c.answer()
    else: await c.answer()

async def reminders():
    while True:
        for u in list(dialogue_history.keys()):
            now = get_patient_time(u)
            ts, ds = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
            if ts == "09:00" and daily_reminders.get(u, {}).get("m") != ds:
                try:
                    await bot.send_message(u, "🌅 Доброе утро! Оцени:", reply_markup=mood_kb())
                    daily_reminders.setdefault(u, {})["m"] = ds; save_data()
                except: pass
            if ts == "21:00" and daily_reminders.get(u, {}).get("e") != ds:
                try:
                    await bot.send_message(u, "🌙 Как день? Оцени:", reply_markup=mood_kb())
                    daily_reminders.setdefault(u, {})["e"] = ds; save_data()
                except: pass
        await asyncio.sleep(30)

async def care():
    msgs = ["🌱 Я рядом.", "💭 Что внутри?", "☀️ Держишься!", "🌊 Волна спадает.", "💪 Ты сильнее!"]
    while True:
        await asyncio.sleep(3600)
        for u in list(care_mode.keys()):
            if care_mode.get(u, False):
                try: await bot.send_message(u, random.choice(msgs))
                except: pass

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def do_HEAD(self): self.send_response(200); self.end_headers()
    def do_POST(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def do_OPTIONS(self): self.send_response(200); self.end_headers()
    def log_message(self, *a): pass

def start_http():
    try:
        p = int(os.environ.get("PORT", 10000))
        s = HTTPServer(("0.0.0.0", p), H)
        def ping():
            while True:
                try: requests.get(f"http://localhost:{p}/", timeout=5)
                except: pass
                time.sleep(300)
        threading.Thread(target=ping, daemon=True).start()
        s.serve_forever()
    except: pass

async def main():
    load_data()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(reminders())
    asyncio.create_task(care())
    threading.Thread(target=start_http, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())