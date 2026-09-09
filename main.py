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
behavior_journal = {}
last_activity = {}
user_consent = {}
stage_of_change = {}
emotion_step = {}  # для опроса эмоций
diary_step = {}    # для пошагового дневника

def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times, user_timezones, patient_memory, interview_step, behavior_journal, last_activity, user_consent, stage_of_change, emotion_step, diary_step
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
                behavior_journal = data.get("behavior_journal", {})
                last_activity = data.get("last_activity", {})
                user_consent = data.get("user_consent", {})
                stage_of_change = data.get("stage_of_change", {})
                emotion_step = data.get("emotion_step", {})
                diary_step = data.get("diary_step", {})
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
        "interview_step": interview_step,
        "behavior_journal": behavior_journal,
        "last_activity": last_activity,
        "user_consent": user_consent,
        "stage_of_change": stage_of_change,
        "emotion_step": emotion_step,
        "diary_step": diary_step
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Остальные функции (empty_profile, empty_memory, empty_behavior, update_memory, analyze_text_patterns, record_behavior, get_behavior_summary) остаются как в предыдущей версии
def empty_profile():
    return {"name": "", "addiction": "", "stage": "", "triggers": "", "goals": "", "last_relapse": "", "notes": ""}

def empty_memory():
    return {"first_contact": datetime.now().strftime("%d.%m.%Y"), "sessions": 0, "preferred_techniques": [], "important_events": [], "progress_notes": []}

def empty_behavior():
    return {"messages": [], "mood_scores": [], "patterns": [], "avg_length": 0, "total_messages": 0}

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

def analyze_text_patterns(text):
    patterns = []
    text_lower = text.lower()
    if len(text) < 10: patterns.append("короткое сообщение")
    if "!" in text and text.count("!") > 2: patterns.append("повышенная эмоциональность")
    if "..." in text: patterns.append("неуверенность")
    if any(w in text_lower for w in ["устал", "устала", "нет сил", "вымотан"]): patterns.append("усталость")
    if any(w in text_lower for w in ["один", "одна", "одинок", "никому"]): patterns.append("одиночество")
    if any(w in text_lower for w in ["не сплю", "бессонница", "не могу спать"]): patterns.append("нарушение сна")
    if any(w in text_lower for w in ["ненавижу", "отвратителен", "ужасен"]): patterns.append("самокритика")
    if any(w in text_lower for w in ["боюсь", "страшно", "тревог", "паник"]): patterns.append("тревога")
    if any(w in text_lower for w in ["сорвался", "сорвалась", "выпил", "употребил"]): patterns.append("срыв")
    return patterns

def record_behavior(user_id, text, mood_score=None):
    if user_id not in behavior_journal:
        behavior_journal[user_id] = empty_behavior()
    bj = behavior_journal[user_id]
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    bj["messages"].append({"time": timestamp, "text": text[:100], "length": len(text)})
    bj["messages"] = bj["messages"][-50:]
    if mood_score is not None:
        bj["mood_scores"].append({"time": timestamp, "score": mood_score})
        bj["mood_scores"] = bj["mood_scores"][-30:]
    patterns = analyze_text_patterns(text)
    for p in patterns:
        bj["patterns"].append({"time": timestamp, "pattern": p})
    bj["patterns"] = bj["patterns"][-30:]
    bj["total_messages"] = bj.get("total_messages", 0) + 1
    lengths = [m["length"] for m in bj["messages"]]
    bj["avg_length"] = sum(lengths) / len(lengths) if lengths else 0
    last_activity[user_id] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data()

def get_behavior_summary(user_id):
    if user_id not in behavior_journal:
        return "Нет данных о поведении."
    bj = behavior_journal[user_id]
    summary = []
    if bj["mood_scores"]:
        scores = [m["score"] for m in bj["mood_scores"][-7:]]
        avg = sum(scores) / len(scores)
        trend = "стабильно" if len(scores) < 2 else ("растёт" if scores[-1] > scores[0] else "снижается")
        summary.append(f"Средняя оценка за последние 7: {avg:.1f}/10, динамика: {trend}")
    if bj["patterns"]:
        recent_patterns = [p["pattern"] for p in bj["patterns"][-10:]]
        most_common = Counter(recent_patterns).most_common(3)
        summary.append("Частые паттерны: " + ", ".join(f"{p[0]} ({p[1]})" for p in most_common))
    summary.append(f"Всего сообщений: {bj['total_messages']}, средняя длина: {bj['avg_length']:.0f} символов")
    return "\n".join(summary)

# Промпт Анны
ANNA_PROMPT_TEMPLATE = """
Ты — Анна Соколова, 36 лет, клинический психолог, аддиктолог.
... (без изменений, как в предыдущей версии, но с учётом модели стадий)
"""

# Функции клавиатур
def main_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚨 Мне плохо сейчас")],
        [KeyboardButton(text="📊 Моё состояние"), KeyboardButton(text="🧠 Что я чувствую?")],
        [KeyboardButton(text="📝 Дневник"), KeyboardButton(text="🎯 Мои цели")],
        [KeyboardButton(text="ℹ️ Помощь и контакты"), KeyboardButton(text="⚙️ Настройки")]
    ], resize_keyboard=True)

def crisis_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔥 У меня тяга")],
        [KeyboardButton(text="😰 Паника/тревога")],
        [KeyboardButton(text="😢 Очень грустно, нет сил")],
        [KeyboardButton(text="💔 Я сорвался")],
        [KeyboardButton(text="📞 Позвонить в службу поддержки")],
        [KeyboardButton(text="⬅️ Назад в главное меню")]
    ], resize_keyboard=True)

def settings_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⏰ Указать время")],
        [KeyboardButton(text="🔕 Приостановить поддержку")],
        [KeyboardButton(text="🗑 Удалить все данные")],
        [KeyboardButton(text="⬅️ Назад в главное меню")]
    ], resize_keyboard=True)

def emotion_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Грусть"), KeyboardButton(text="Тревога")],
        [KeyboardButton(text="Злость"), KeyboardButton(text="Одиночество")],
        [KeyboardButton(text="Стыд"), KeyboardButton(text="Страх")],
        [KeyboardButton(text="Радость"), KeyboardButton(text="Усталость")],
        [KeyboardButton(text="⬅️ Назад")]
    ], resize_keyboard=True)

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

MOTIVATIONS = [ ... ]  # оставить как есть

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

# Обработчики команд
@dp.message(Command("start"))
async def start_command(message: types.Message):
    # дисклеймер и согласие
    ...

@dp.callback_query()
async def handle_consent(callback: types.CallbackQuery):
    ...

@dp.message(Command("menu"))
async def menu_command(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())

@dp.message(Command("crisis"))
async def crisis_command(message: types.Message):
    await message.answer("Кризисное меню. Выбери, что тебе нужно:", reply_markup=crisis_menu_keyboard())

@dp.message(Command("mood"))
async def mood_command(message: types.Message):
    await message.answer("Оцени своё состояние от 1 до 10:", reply_markup=mood_keyboard())

@dp.message(Command("sober"))
async def sober_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in sober_tracker:
        days = (datetime.now() - datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")).days
        await message.answer(f"💚 Ты чист(а) уже {days} дней!")
    else:
        await message.answer("Срывов пока не отмечалось. Это отлично! 💚")

@dp.message(Command("relapse"))
async def relapse_command(message: types.Message):
    user_id = str(message.from_user.id)
    sober_tracker[user_id] = datetime.now().strftime("%Y-%m-%d")
    relapse_times.append(datetime.now().strftime("%H:%M"))
    congratulated[user_id] = []
    update_memory(user_id, "important_events", "Срыв")
    save_data()
    stage_of_change[user_id] = "рецидив"
    save_data()
    await message.answer(
        "Я не осуждаю. Спасибо, что поделился(ась). Срыв — это часть процесса, и мы можем извлечь из него урок.\n"
        "Давай разберём, что произошло, и скорректируем план. Что случилось перед срывом?",
        reply_markup=crisis_menu_keyboard()
    )

@dp.message(Command("plan"))
async def plan_command(message: types.Message):
    await message.answer(
        "📋 Твой план действий при тяге:\n"
        "1. Остановись и сделай паузу на 10 минут.\n"
        "2. Умойся ледяной водой или подыши по квадрату (4-4-4-4).\n"
        "3. Позвони близкому человеку или напиши мне.\n"
        "4. Если тяга выше 7/10, используй технику «Сёрфинг по тяге».\n"
        "5. Вернись сюда и расскажи, как прошло.",
        reply_markup=main_menu_keyboard()
    )

@dp.message(Command("goals"))
async def goals_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in user_goals:
        await message.answer(f"🎯 Твои цели:\n{user_goals[user_id]}")
    else:
        await message.answer("Цели пока не заданы. Напиши /goals <цель> или используй кнопку «🎯 Мои цели» в меню.")

@dp.message(Command("diary"))
async def diary_command(message: types.Message):
    user_id = str(message.from_user.id)
    diary_step[user_id] = "situation"
    await message.answer("Давай сделаем запись в дневнике.\n\nШаг 1/4: Опиши ситуацию, которая произошла.")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "ℹ️ Помощь и контакты:\n\n"
        "• 112 — экстренная помощь\n"
        "• 8-800-2000-122 — телефон доверия (бесплатно, круглосуточно)\n"
        "• Я — виртуальный помощник, а не врач. Я не ставлю диагнозы и не назначаю лечение.\n"
        "• В кризисной ситуации обратись к специалисту лично или вызови скорую.\n\n"
        "Доступные команды:\n"
        "/menu — главное меню\n"
        "/crisis — кризисное меню\n"
        "/mood — оценка состояния\n"
        "/sober — дни чистоты\n"
        "/relapse — отметить срыв\n"
        "/plan — план действий\n"
        "/goals — цели\n"
        "/diary — дневник\n"
        "/reset — удалить все данные"
    )

@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    user_id = str(message.from_user.id)
    # запрашиваем подтверждение
    await message.answer(
        "Вы уверены, что хотите удалить все данные? Это действие необратимо.\n"
        "Напишите «Да, удалить» для подтверждения."
    )
    # устанавливаем флаг ожидания подтверждения
    interview_step[user_id] = "confirm_reset"

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    care_mode[str(message.from_user.id)] = False
    save_data()
    await message.answer("Поддержка приостановлена. Ты можешь включить её снова в настройках.")

# Обработка кнопок (reply-клавиатуры)
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text

    # Проверка согласия
    if user_id not in user_consent or not user_consent[user_id]:
        if text == "Согласен(а)":
            user_consent[user_id] = True
            save_data()
            interview_step[user_id] = "name"
            await message.answer("Спасибо! Как тебя зовут?")
            return
        elif text == "Не согласен(а)":
            await message.answer("Хорошо. Если передумаешь, напиши /start.")
            return
        else:
            await message.answer("Пожалуйста, дай согласие или напиши /start.")
            return

    # Обработка подтверждения сброса
    if interview_step.get(user_id) == "confirm_reset":
        if text.lower() == "да, удалить":
            # полная очистка
            dialogue_history.pop(user_id, None)
            mood_journal.pop(user_id, None)
            care_mode.pop(user_id, None)
            patient_profiles.pop(user_id, None)
            patient_memory.pop(user_id, None)
            behavior_journal.pop(user_id, None)
            sober_tracker.pop(user_id, None)
            user_goals.pop(user_id, None)
            congratulated.pop(user_id, None)
            user_timezones.pop(user_id, None)
            interview_step.pop(user_id, None)
            last_activity.pop(user_id, None)
            user_consent.pop(user_id, None)
            stage_of_change.pop(user_id, None)
            emotion_step.pop(user_id, None)
            diary_step.pop(user_id, None)
            save_data()
            await message.answer("Все данные удалены. Чтобы начать заново, напиши /start.")
            return
        else:
            interview_step.pop(user_id, None)
            await message.answer("Сброс отменён.")
            return

    # Обработка главного меню
    if text == "🚨 Мне плохо сейчас":
        await message.answer("Выбери, что происходит:", reply_markup=crisis_menu_keyboard())
        return

    elif text == "📊 Моё состояние":
        # показываем сводку
        user_id = str(message.from_user.id)
        days = 0
        if user_id in sober_tracker:
            days = (datetime.now() - datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")).days
        last_moods = mood_journal.get(user_id, [])[-5:]
        mood_str = "\n".join(last_moods) if last_moods else "нет записей"
        await message.answer(f"📊 Твоё состояние:\n\nДней чистоты: {days}\n\nПоследние оценки:\n{mood_str}", reply_markup=main_menu_keyboard())
        return

    elif text == "🧠 Что я чувствую?":
        emotion_step[user_id] = "choose"
        await message.answer("Какое чувство ты испытываешь прямо сейчас?", reply_markup=emotion_keyboard())
        return

    elif text == "📝 Дневник":
        diary_step[user_id] = "situation"
        await message.answer("Давай сделаем запись.\n\nШаг 1/4: Опиши ситуацию.")
        return

    elif text == "🎯 Мои цели":
        user_id = str(message.from_user.id)
        goals = user_goals.get(user_id, "")
        if goals:
            await message.answer(f"Твои цели:\n{goals}\n\nЧтобы добавить новую, напиши: /goals <цель>", reply_markup=main_menu_keyboard())
        else:
            await message.answer("Цели пока не заданы. Напиши: /goals <цель>", reply_markup=main_menu_keyboard())
        return

    elif text == "ℹ️ Помощь и контакты":
        await message.answer(
            "ℹ️ Контакты:\n\n"
            "• 112 — экстренная помощь\n"
            "• 8-800-2000-122 — телефон доверия\n\n"
            "Я — виртуальный помощник, а не врач. При необходимости обратись к очному специалисту.",
            reply_markup=main_menu_keyboard()
        )
        return

    elif text == "⚙️ Настройки":
        await message.answer("Настройки:", reply_markup=settings_menu_keyboard())
        return

    # Обработка кризисного меню
    elif text == "🔥 У меня тяга":
        await message.answer("Оцени силу тяги от 1 до 10:", reply_markup=craving_keyboard())
        return
    elif text == "😰 Паника/тревога":
        await message.answer(
            "Сделай следующее:\n"
            "1. Назови 5 вещей, которые видишь.\n"
            "2. Назови 4 вещи, которые слышишь.\n"
            "3. Назови 3 вещи, которые чувствуешь.\n"
            "4. Медленно вдохни и выдохни 5 раз.\n\n"
            "Если паника не проходит, позвони доверенному лицу или 112.",
            reply_markup=crisis_menu_keyboard()
        )
        return
    elif text == "😢 Очень грустно, нет сил":
        # Оценка суицидального риска
        await message.answer(
            "Мне жаль, что тебе так тяжело. Я хочу помочь.\n\n"
            "Есть ли у тебя мысли о том, чтобы навредить себе? (да/нет)"
        )
        emotion_step[user_id] = "suicide_risk_1"
        return
    elif text == "💔 Я сорвался":
        # сразу запускаем анализ
        sober_tracker[user_id] = datetime.now().strftime("%Y-%m-%d")
        relapse_times.append(datetime.now().strftime("%H:%M"))
        congratulated[user_id] = []
        update_memory(user_id, "important_events", "Срыв")
        save_data()
        stage_of_change[user_id] = "рецидив"
        save_data()
        await message.answer(
            "Спасибо за честность. Срыв — это не поражение, а информация.\n"
            "Что произошло перед срывом? Опиши ситуацию.",
            reply_markup=crisis_menu_keyboard()
        )
        return
    elif text == "📞 Позвонить в службу поддержки":
        await message.answer(
            "📞 Номера:\n\n"
            "• 112 — экстренная помощь\n"
            "• 8-800-2000-122 — телефон доверия (бесплатно)\n\n"
            "Позвони прямо сейчас, если тебе плохо.",
            reply_markup=crisis_menu_keyboard()
        )
        return
    elif text == "⬅️ Назад в главное меню":
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
        return

    # Обработка настроек
    elif text == "⏰ Указать время":
        await message.answer("Напиши текущее время в формате ЧЧ:ММ, например 14:30")
        interview_step[user_id] = "time"
        return
    elif text == "🔕 Приостановить поддержку":
        care_mode[user_id] = False
        save_data()
        await message.answer("Поддержка приостановлена. Ты можешь включить её снова в настройках.", reply_markup=main_menu_keyboard())
        return
    elif text == "🗑 Удалить все данные":
        await message.answer(
            "Вы уверены? Это действие необратимо.\n"
            "Напишите «Да, удалить» для подтверждения."
        )
        interview_step[user_id] = "confirm_reset"
        return

    # Обработка эмоций
    if emotion_step.get(user_id) == "choose":
        valid_emotions = ["Грусть", "Тревога", "Злость", "Одиночество", "Стыд", "Страх", "Радость", "Усталость"]
        if text in valid_emotions:
            emotion_step[user_id] = "intensity"
            # сохраняем выбранную эмоцию во временную переменную (можно в patient_memory)
            patient_memory[user_id]["last_emotion"] = text
            save_data()
            await message.answer(f"Ты выбрал(а) {text}. Оцени интенсивность от 1 до 10:", reply_markup=mood_keyboard())
        else:
            await message.answer("Пожалуйста, выбери эмоцию из кнопок.", reply_markup=emotion_keyboard())
        return

    # Обработка интенсивности эмоции (через callback позже)
    # Дневник
    if diary_step.get(user_id):
        step = diary_step[user_id]
        if step == "situation":
            # сохраняем ситуацию
            patient_memory[user_id]["diary_situation"] = text
            diary_step[user_id] = "thought"
            await message.answer("Шаг 2/4: Какая мысль возникла в этой ситуации?")
            return
        elif step == "thought":
            patient_memory[user_id]["diary_thought"] = text
            diary_step[user_id] = "emotion"
            await message.answer("Шаг 3/4: Что ты почувствовал(а)? (одно слово, например, грусть, злость)")
            return
        elif step == "emotion":
            patient_memory[user_id]["diary_emotion"] = text
            diary_step[user_id] = "action"
            await message.answer("Шаг 4/4: Что ты сделал(а) в этой ситуации?")
            return
        elif step == "action":
            # записываем в дневник
            situation = patient_memory[user_id].get("diary_situation", "")
            thought = patient_memory[user_id].get("diary_thought", "")
            emotion = patient_memory[user_id].get("diary_emotion", "")
            action = text
            entry = f"Ситуация: {situation}\nМысль: {thought}\nЭмоция: {emotion}\nДействие: {action}"
            if user_id not in mood_journal:
                mood_journal[user_id] = []
            mood_journal[user_id].append(f"[Дневник] {entry}")
            save_data()
            diary_step.pop(user_id, None)
            # очищаем временные поля
            for k in ["diary_situation", "diary_thought", "diary_emotion"]:
                patient_memory[user_id].pop(k, None)
            save_data()
            await message.answer("Запись сохранена. Спасибо, что поделился(ась). 💚", reply_markup=main_menu_keyboard())
            return

    # Обработка оценки суицидального риска
    if emotion_step.get(user_id) == "suicide_risk_1":
        if text.lower() in ["да", "yes", "есть"]:
            await message.answer("Есть ли у тебя конкретный план, как это сделать?")
            emotion_step[user_id] = "suicide_risk_2"
        else:
            await message.answer("Хорошо, что ты сказал(а). Ты не один(а). Давай попробуем вместе найти выход.", reply_markup=crisis_menu_keyboard())
            emotion_step.pop(user_id, None)
        return
    elif emotion_step.get(user_id) == "suicide_risk_2":
        if text.lower() in ["да", "yes", "есть"]:
            await message.answer("Есть ли у тебя доступ к средствам?")
            emotion_step[user_id] = "suicide_risk_3"
        else:
            await message.answer("Пожалуйста, позвони 8-800-2000-122 или 112, чтобы получить помощь. Я не могу заменить специалиста.", reply_markup=crisis_menu_keyboard())
            emotion_step.pop(user_id, None)
        return
    elif emotion_step.get(user_id) == "suicide_risk_3":
        if text.lower() in ["да", "yes", "есть"]:
            await message.answer(
                "Сейчас очень важно, чтобы ты позвонил(а) 112 или попросил(а) кого-то быть рядом.\n"
                "Я не могу продолжать терапию в таком состоянии.\n"
                "Пожалуйста, набери номер экстренной службы.",
                reply_markup=crisis_menu_keyboard()
            )
        else:
            await message.answer("Пожалуйста, обратись к близким или позвони на горячую линию 8-800-2000-122.", reply_markup=crisis_menu_keyboard())
        emotion_step.pop(user_id, None)
        return

    # Обработка времени
    offset = parse_patient_time(text)
    if offset is not None:
        user_timezones[user_id] = offset
        save_data()
        if interview_step.get(user_id) == "time":
            interview_step[user_id] = "done"
            await message.answer("✅ Время сохранено. Напоминания будут приходить в твоё время.", reply_markup=main_menu_keyboard())
        else:
            await message.answer("✅ Время сохранено.", reply_markup=main_menu_keyboard())
        return

    # Обычное общение с Анной
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

# Callback-обработчик для inline-кнопок (оценки, тяга, интенсивность эмоций)
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    data = callback.data

    if data.startswith("mood_"):
        v = int(data.split("_")[1])
        if user_id not in mood_journal:
            mood_journal[user_id] = []
        mood_journal[user_id].append(f"{datetime.now().strftime('%d.%m.%Y %H:%M')} — {v}/10")
        update_memory(user_id, "progress_notes", f"Оценка {v}/10")
        record_behavior(user_id, f"[Оценка: {v}/10]", mood_score=v)

        # Проверяем, был ли это опрос эмоций
        if emotion_step.get(user_id) == "intensity":
            emotion = patient_memory[user_id].get("last_emotion", "")
            if emotion:
                # Сохраняем эмоцию и интенсивность
                if user_id not in mood_journal:
                    mood_journal[user_id] = []
                mood_journal[user_id].append(f"[Эмоция] {emotion}: {v}/10")
                save_data()
                await callback.message.answer(f"Записал: {emotion} ({v}/10). Спасибо, что поделился(ась).", reply_markup=main_menu_keyboard())
                emotion_step.pop(user_id, None)
            else:
                await callback.message.answer("Произошла ошибка, попробуй ещё раз.", reply_markup=emotion_keyboard())
        else:
            # Обычная оценка состояния
            if v <= 5:
                care_mode[user_id] = True
                await callback.message.answer(f"Спасибо ({v}/10). Я рядом. 💚")
            else:
                care_mode[user_id] = False
                await callback.message.answer(f"Отлично! {v}/10. ☀️")
        save_data()
        await callback.answer()

    elif data.startswith("craving_"):
        levels = {"low": "Слабая", "medium": "Средняя", "high": "Сильная", "extreme": "Невыносимая"}
        level = levels.get(data.replace("craving_", ""), "")
        if user_id in dialogue_history:
            dialogue_history[user_id].append({"role": "system", "content": f"Тяга оценена: {level}. Тема закрыта."})
        save_data()
        await callback.message.answer(f"Тяга: {level}. Опиши, где в теле ты её чувствуешь? 🌊")
        await callback.answer()

    else:
        await callback.answer()

# Фоновые задачи (напоминания, умные напоминания, почасовая поддержка, поздравления)
async def send_reminders():
    while True:
        for uid in list(dialogue_history.keys()):
            ct = get_patient_time(uid).strftime("%H:%M")
            if ct == "09:00":
                try:
                    await bot.send_message(uid, "🌅 Доброе утро! Оцени своё состояние:", reply_markup=mood_keyboard())
                except:
                    pass
            if ct == "21:00":
                try:
                    await bot.send_message(uid, "🌙 Как прошёл день? Оцени:", reply_markup=mood_keyboard())
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
                        await bot.send_message(uid, "⏰ В это время раньше случались срывы. Будь внимателен. 💚")
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

# HTTP сервер для Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
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