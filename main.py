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
emotion_step = {}
diary_step = {}
feedback_data = {}
daily_reminders = {}

def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times, user_timezones, patient_memory, interview_step, behavior_journal, last_activity, user_consent, stage_of_change, emotion_step, diary_step, feedback_data, daily_reminders
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
                feedback_data = data.get("feedback_data", {})
                daily_reminders = data.get("daily_reminders", {})
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
        "diary_step": diary_step,
        "feedback_data": feedback_data,
        "daily_reminders": daily_reminders
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def empty_profile():
    return {"name": "", "gender": "", "addiction": "", "stage": "", "triggers": "", "goals": "", "last_relapse": "", "notes": ""}

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
    if len(text) < 10:
        patterns.append("короткое сообщение")
    if "!" in text and text.count("!") > 2:
        patterns.append("повышенная эмоциональность")
    if "..." in text:
        patterns.append("неуверенность")
    if any(w in text_lower for w in ["устал", "устала", "нет сил", "вымотан"]):
        patterns.append("усталость")
    if any(w in text_lower for w in ["один", "одна", "одинок", "никому"]):
        patterns.append("одиночество")
    if any(w in text_lower for w in ["не сплю", "бессонница", "не могу спать"]):
        patterns.append("нарушение сна")
    if any(w in text_lower for w in ["ненавижу", "отвратителен", "ужасен"]):
        patterns.append("самокритика")
    if any(w in text_lower for w in ["боюсь", "страшно", "тревог", "паник"]):
        patterns.append("тревога")
    if any(w in text_lower for w in ["сорвался", "сорвалась", "выпил", "употребил"]):
        patterns.append("срыв")
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

ANNA_PROMPT_TEMPLATE = """
Ты — Анна Соколова, виртуальный психотерапевт, специализирующийся на помощи при зависимостях. Ты не человек, а программа, действующая на основе клинических протоколов. Твоя цель — поддержать пациента, помочь ему измениться, оставаясь прозрачным инструментом.

## ГЛАВНОЕ ПРАВИЛО ПОЛА (КРИТИЧЕСКИ ВАЖНО)
Пол пациента: {gender}
Если пол пациента «мужской» — ВСЕГДА обращайся к нему в мужском роде: «ты мог», «ты справился», «ты сделал», «ты сам».
Если пол пациента «женский» — ВСЕГДА обращайся к нему в женском роде: «ты могла», «ты справилась», «ты сделала», «ты сама».
НИКОГДА не путай род пациента. Проверяй каждое обращение к нему. Если сомневаешься — используй нейтральные формулировки без рода.
Ты сама (Анна) — женщина, говори о себе в женском роде всегда.

## ПРОФЕССИОНАЛЬНЫЙ ТОН
- Будь эмпатичной, но не имитируй личность с биографией или слабостями.
- Используй стандартные поддерживающие фразы: «Я понимаю, это тяжело», «Давай разберёмся вместе».
- Сохраняй нейтральность и не давай ложных надежд.

## ЕСТЕСТВЕННЫЙ РАЗГОВОРНЫЙ СТИЛЬ
- Активно слушай: задавай уточняющие вопросы, переспрашивай, если что-то неясно.
- Отражай эмоции пациента: «Я слышу, что ты злишься. Что происходит?»
- Реагируй на сопротивление мягко, исследуя причину, а не конфликтуя.
- Избегай излишних смайликов, сохраняй профессиональную дистанцию.

## АДАПТАЦИЯ ПОД ТИП ПАЦИЕНТА
- Для тревожных: давай больше структуры, дыхательных техник, успокаивающих формулировок.
- Для рациональных: используй логику, анализ, дневники.
- Для зависимых: оказывай тёплую поддержку, но с чёткими границами.
- Для импульсивных: предлагай короткие, конкретные шаги.
- Определяй тип по ответам первичного интервью и явным запросам, не по скрытым метрикам.

## МОТИВАЦИОННОЕ ИНТЕРВЬЮ
- Исследуй амбивалентность: «С одной стороны ты хочешь бросить, с другой — это помогает расслабиться. Как это сочетается?»
- Используй открытые вопросы, рефлексию, резюмирование.
- Помоги пациенту самому проговорить причины изменений.

## ВТОРИЧНЫЕ ВЫГОДЫ
- Исследуй, что даёт зависимость: «Что хорошего даёт тебе употребление? Как ещё ты можешь это получить?»
- Не осуждай, а помогай найти здоровые альтернативы.

## ПСИХООБРАЗОВАНИЕ
- Простыми словами объясняй, как работает зависимость на уровне мозга: дофамин, толерантность, тяга как биологический процесс.
- Подчёркивай, что тяга — не слабость, а нейробиологическое явление.

## ИНТЕРАКТИВНЫЕ ТЕХНИКИ
- Предлагай мини-упражнения прямо в диалоге: дыхание 4-4-4-4, заземление 5-4-3-2-1, оспаривание мыслей.
- Давай домашние задания с последующим обсуждением.
- Челленджи предлагай только в рамках согласованного плана.

## МОДЕЛЬ СТАДИЙ ИЗМЕНЕНИЯ (ПРОХАЗКА И ДИКЛЕМЕНТЕ)
Определяй стадию и действуй соответственно:
1. Предразмышление — задавай вопросы о последствиях, не спорь.
2. Размышление — взвешивай за и против.
3. Подготовка — помоги составить план.
4. Действие — обучай навыкам.
5. Поддержание — профилактика срыва.
6. Рецидив — не осуждай, анализируй, возвращайся к плану.

## КРИЗИСНЫЙ ПРОТОКОЛ
При суицидальных мыслях:
1. Спроси: «Есть ли у тебя план?», «Есть ли доступ к средствам?», «Когда в последний раз думал(а) об этом?»
2. Если план и средства есть — НЕМЕДЛЕННО: «Позвони 112 или 8-800-2000-122. Я не могу продолжать терапию. Сделай это прямо сейчас».
3. Если только мысли — поддержи и предложи обратиться к живому специалисту.

## АНКЕТА ПАЦИЕНТА
Имя: {name}
Пол: {gender}
Зависимость: {addiction}
Триггеры: {triggers}
Цели: {goals}

## ПАМЯТЬ
Первый контакт: {first_contact}
Сессий: {sessions}
Техники: {techniques}
События: {events}
Прогресс: {progress}

## ПРАВИЛА ОТВЕТОВ
1. Одна мысль = одно сообщение.
2. 3–10 предложений. Отвечай развёрнуто, но не перегружай.
3. Обращайся к пациенту в его роде (см. главное правило выше).
4. НЕ зацикливайся.

## СИГНАЛЫ ДЛЯ КНОПОК
[MOOD] — только когда прямо спрашиваешь оценку от 1 до 10.
[CRAVING] — только когда прямо спрашиваешь силу тяги.
В обычном разговоре теги не добавляй.

## ЗАПРЕТЫ
Не осуждай, не давай медсоветов. Не ставь диагнозы.
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
        gender=p.get("gender", "") or "не указан",
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

def fix_gender_in_reply(user_id, text):
    """Заменяет ошибочные женские формы на мужские, если пациент мужчина, и наоборот."""
    if user_id not in patient_profiles:
        return text
    gender = patient_profiles[user_id].get("gender", "")
    if gender == "мужской":
        replacements = {
            "ты могла": "ты мог", "ты справилась": "ты справился",
            "ты сделала": "ты сделал", "ты сама": "ты сам",
            "обратила": "обратил", "поняла": "понял",
            "сказала": "сказал", "пришла": "пришёл",
            "хотела": "хотел", "была": "был", "стала": "стал"
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
    elif gender == "женский":
        replacements = {
            "ты мог": "ты могла", "ты справился": "ты справилась",
            "ты сделал": "ты сделала", "ты сам": "ты сама",
            "обратил": "обратила", "понял": "поняла",
            "сказал": "сказала", "пришёл": "пришла",
            "хотел": "хотела", "был": "была", "стал": "стала"
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
    return text

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
    record_behavior(user_id, user_text)
    system_prompt = build_prompt(user_id)
    messages = [{"role": "system", "content": system_prompt}] + history
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {"model": OPENROUTER_MODEL, "messages": messages}
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    result = response.json()
    anna_reply = result["choices"][0]["message"]["content"]
    anna_reply = fix_gender_in_reply(user_id, anna_reply)
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

def gender_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")],
        [KeyboardButton(text="Не важно")]
    ], resize_keyboard=True)

def main_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚨 Мне плохо сейчас"), KeyboardButton(text="🆘 Я на грани")],
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

def feedback_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="fb_1"), InlineKeyboardButton(text="2", callback_data="fb_2"),
         InlineKeyboardButton(text="3", callback_data="fb_3"), InlineKeyboardButton(text="4", callback_data="fb_4"),
         InlineKeyboardButton(text="5", callback_data="fb_5")]
    ])

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
    await message.answer(
        "Я — виртуальный помощник Анна, а не врач. Я не ставлю диагнозы, не назначаю лечение, не заменяю очную психотерапию.\n\n"
        "Ваши данные хранятся конфиденциально и не передаются третьим лицам, за исключением случаев угрозы жизни.\n\n"
        "Продолжая, вы соглашаетесь на обработку данных. Для удаления всех данных используйте /reset.\n\n"
        "Нажмите «Согласен(а)», чтобы начать.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Согласен(а)", callback_data="consent_yes")],
            [InlineKeyboardButton(text="Не согласен(а)", callback_data="consent_no")]
        ])
    )

@dp.callback_query()
async def handle_consent(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    if callback.data == "consent_yes":
        user_consent[user_id] = True
        save_data()
        interview_step[user_id] = "name"
        await callback.message.answer("Спасибо! Давай познакомимся. Как тебя зовут?")
        await callback.answer()
    elif callback.data == "consent_no":
        await callback.message.answer("Хорошо. Если передумаешь, напиши /start.")
        await callback.answer()
    else:
        await handle_callback(callback)

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
        "/export — экспорт данных\n"
        "/feedback — оценить полезность\n"
        "/reset — удалить все данные\n\n"
        "Если ты близкий человек зависимого и тебе нужна поддержка, напиши «Как помочь близкому»."
    )

@dp.message(Command("export"))
async def export_command(message: types.Message):
    user_id = str(message.from_user.id)
    report = "📋 Отчёт Анны Соколовой\n\n"
    report += f"Имя: {patient_profiles.get(user_id, {}).get('name', '—')}\n"
    report += f"Пол: {patient_profiles.get(user_id, {}).get('gender', '—')}\n"
    report += f"Зависимость: {patient_profiles.get(user_id, {}).get('addiction', '—')}\n"
    report += f"Цели: {user_goals.get(user_id, '—')}\n"
    days = 0
    if user_id in sober_tracker:
        days = (datetime.now() - datetime.strptime(sober_tracker[user_id], "%Y-%m-%d")).days
    report += f"Дней чистоты: {days}\n\n"
    report += "Оценки состояния:\n"
    if user_id in mood_journal and mood_journal[user_id]:
        for entry in mood_journal[user_id][-20:]:
            report += f"• {entry}\n"
    else:
        report += "Нет записей\n"
    report += "\nДневник:\n"
    diary_entries = [e for e in mood_journal.get(user_id, [])