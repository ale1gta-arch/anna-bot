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

# ============ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ============
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
education_step = {}

# ============ ГОРЯЧИЕ ЛИНИИ ============
HOTLINES = """
📞 Телефоны помощи (Россия, круглосуточно, бесплатно):

🚨 Экстренная помощь: 112
🧠 Психологическая помощь (всероссийская): 8-800-2000-122
💚 Телефон неотложной психологической помощи (Москва): 8-495-989-50-50
🆘 Помощь при зависимостях: 8-800-2000-122
👨‍👩‍👧 Детский телефон доверия: 8-800-2000-122
🎓 Студенческая линия: 8-800-2000-122

🌍 Международные:
• США (SAMHSA): 1-800-662-4357
• Великобритания (Mind): 0300 123 3393
• Германия (Telefonseelsorge): 0800 111 0 111
"""

# ============ ПСИХООБРАЗОВАНИЕ ============
PSYCHOEDUCATION = {
    "neuro": """🧠 *Нейробиология зависимости*

Зависимость — это не слабость воли, а изменение работы мозга.

1️⃣ *Дофамин.* В норме дофамин выделяется при еде, общении, спорте. Вещество вызывает выброс в 2–10 раз больше — мозг запоминает этот «лёгкий» путь удовольствия.

2️⃣ *Толерантность.* Рецепторы привыкают. Чтобы получить тот же эффект, нужно больше вещества. Так растёт доза.

3️⃣ *Абстиненция.* Когда вещества нет, дофамин падает ниже нормы. Появляется тревога, апатия, «тяга» — мозг требует вернуть источник.

4️⃣ *Тяга (craving).* Это биологический сигнал, а не признак слабости. Тяга приходит волнами: нарастает 10–20 минут и спадает. Если её переждать, не подкрепляя, — она ослабевает.

5️⃣ *Нейропластичность.* Мозг восстанавливается. Через 3–6 месяцев трезвости рецепторы возвращаются к норме. Психотерапия и новые привычки ускоряют этот процесс.""",

    "cbt": """🧩 *Основы КПТ (когнитивно-поведенческой терапии)*

КПТ учит, что наши эмоции зависят не от событий, а от того, *как мы их интерпретируем*.

🔗 *Схема: Ситуация → Мысль → Эмоция → Поведение*

Пример при тяге:
• *Ситуация:* увидел бар.
• *Мысль:* «Одна рюмка не повредит».
• *Эмоция:* предвкушение, тревога.
• *Поведение:* зашёл, выпил → срыв.

Что делает КПТ:
1️⃣ Учимся *замечать* автоматические мысли.
2️⃣ *Проверяем* их на реальность: «Какие доказательства за и против?»
3️⃣ *Заменяем* на более точные: «Одна рюмка запустит цикл — я это уже проходил».
4️⃣ *Меняем поведение:* избегаем триггеров, тренируем навыки.

📝 Домашнее задание: ведите дневник мыслей — ситуация → мысль → эмоция → что сделали.""",

    "dbt": """🧘 *Основы ДБТ (диалектико-поведенческой терапии)*

ДБТ разработана Маршей Линехан для людей с сильными эмоциями. Она учит *балансу* между принятием себя и изменениями.

4 модуля навыков:

1️⃣ *Осознанность (mindfulness).*
Наблюдать мысли и чувства без осуждения. Техника 5-4-3-2-1: назови 5 вещей, которые видишь, 4 — слышишь, 3 — чувствуешь, 2 — ощущаешь запах, 1 — вкус.

2️⃣ *Стрессоустойчивость.*
Пережить кризис, не ухудшив ситуацию. Техника TIP: температура (умойся ледяной водой), интенсивная нагрузка (20 приседаний), дыхание (4-7-8), прогрессивная релаксация.

3️⃣ *Эмоциональная регуляция.*
Замечать и называть эмоции. «Противоположное действие»: если тянет изолироваться — позвони другу. Если тянет к веществу — сделай что-то приятное без него.

4️⃣ *Межличностная эффективность.*
Учиться говорить «нет» без вины. Формула DEAR MAN: опиши, вырази, попроси, подкрепи, будь уверен, договорись.

💡 Главный принцип ДБТ: «Я принимаю себя таким, какой я есть, и одновременно я меняюсь». Это и есть диалектика."""
}

# ============ ЗАГРУЗКА / СОХРАНЕНИЕ ============
def load_data():
    global dialogue_history, patient_profiles, mood_journal, care_mode, sober_tracker, user_goals, congratulated, relapse_times, user_timezones, patient_memory, interview_step, behavior_journal, last_activity, user_consent, stage_of_change, emotion_step, diary_step, feedback_data, daily_reminders, education_step
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
                education_step = data.get("education_step", {})
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
        "daily_reminders": daily_reminders,
        "education_step": education_step
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

# ============ ПРОМПТ АННЫ ============
ANNA_PROMPT_TEMPLATE = """
Ты — Анна Соколова, виртуальный психотерапевт, специализирующийся на помощи при зависимостях. Ты не человек, а программа, действующая на основе клинических протоколов. Твоя цель — поддержать пациента, помочь ему измениться, оставаясь прозрачным инструментом.

## ГЛАВНОЕ ПРАВИЛО ПОЛА (КРИТИЧЕСКИ ВАЖНО)
Пол пациента: {gender}
Если пол пациента «мужской» — ВСЕГДА обращайся к нему в мужском роде: «ты мог», «ты справился», «ты сделал», «ты сам».
Если пол пациента «женский» — ВСЕГДА обращайся к нему в женском роде: «ты могла», «ты справилась», «ты сделала», «ты сама».
НИКОГДА не путай род пациента. Проверяй каждое обращение. Если сомневаешься — используй нейтральные формулировки без рода.
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

## МОТИВАЦИОННОЕ ИНТЕРВЬЮ
- Исследуй амбивалентность: «С одной стороны ты хочешь бросить, с другой — это помогает расслабиться. Как это сочетается?»
- Используй открытые вопросы, рефлексию, резюмирование.
- Помоги пациенту самому проговорить причины изменений.

## ВТОРИЧНЫЕ ВЫГОДЫ
- Исследуй, что даёт зависимость: «Что хорошего даёт тебе употребление? Как ещё ты можешь это получить?»
- Не осуждай, а помогай найти здоровые альтернативы.

## ПСИХООБРАЗОВАНИЕ (важно объяснять простыми словами)

### Нейробиология зависимости
- Дофамин: вещество даёт выброс в 2–10 раз больше естественного.
- Толерантность: рецепторы привыкают, нужна большая доза.
- Абстиненция: падение дофамина ниже нормы → тревога, апатия, тяга.
- Тяга — биологический сигнал, приходит волнами (10–20 минут), спадает.
- Нейропластичность: мозг восстанавливается за 3–6 месяцев трезвости.

### КПТ (схема: Ситуация → Мысль → Эмоция → Поведение)
- Учи пациента замечать автоматические мысли.
- Проверять их на реальность: «Какие доказательства за и против?»
- Заменять на более точные.
- Менять поведение через избегание триггеров и навыки.

### ДБТ (4 модуля)
1. Осознанность: наблюдение без осуждения, техника 5-4-3-2-1.
2. Стрессоустойчивость: TIP (температура, интенсивная нагрузка, дыхание 4-7-8, релаксация), ACCEPTS.
3. Эмоциональная регуляция: называние эмоций, противоположное действие.
4. Межличностная эффективность: DEAR MAN, GIVE, FAST.
Принцип диалектики: «Я принимаю себя и одновременно меняюсь».

## ИНТЕРАКТИВНЫЕ ТЕХНИКИ
- Предлагай мини-упражнения прямо в диалоге: дыхание 4-4-4-4, заземление 5-4-3-2-1, оспаривание мыслей.
- Давай домашние задания с последующим обсуждением.

## МОДЕЛЬ СТАДИЙ ИЗМЕНЕНИЯ
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
3. Обращайся к пациенту в его роде.
4. НЕ зацикливайся.

## СИГНАЛЫ ДЛЯ КНОПОК
[MOOD] — только когда прямо спрашиваешь оценку от 1 до 10.
[CRAVING] — только когда прямо спрашиваешь силу тяги.
В обычном разговоре теги не добавляй.

## ЗАПРЕТЫ
Не осуждай, не давай медсоветов. Не ставь диагнозы. Не назначай препараты. При необходимости рекомендовать очную помощь — используй фразу: «Я не врач, это нужно обсудить с живым специалистом».
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
    data = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}], "max_tokens": 800}
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
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
    if user_id not in patient_profiles:
        return text
    gender = patient_profiles[user_id].get("gender", "")
    if gender == "мужской":
        replacements = {
            "ты могла": "ты мог", "ты справилась": "ты справился",
            "ты сделала": "ты сделал", "ты сама": "ты сам",
            "обратила": "обратил", "поняла": "понял",
            "сказала": "сказал", "пришла": "пришёл",
            "хотела": "хотел", "была": "был", "стала": "стал",
            "могла бы": "мог бы", "смотрела": "смотрел"
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
    elif gender == "женский":
        replacements = {
            "ты мог": "ты могла", "ты справился": "ты справилась",
            "ты сделал": "ты сделала", "ты сам": "ты сама",
            "обратил": "обратила", "понял": "поняла",
            "сказал": "сказала", "пришёл": "пришла",
            "хотел": "хотела", "был": "была", "стал": "стала",
            "мог бы": "могла бы", "смотрел": "смотрела"
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
    data = {"model": OPENROUTER_MODEL, "messages": messages, "max_tokens": 800}
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
    result = response.json()
    anna_reply = result["choices"][0]["message"]["content"]
    anna_reply = fix_gender_in_reply(user_id, anna_reply)
    history.append({"role": "assistant", "content": anna_reply})
    dialogue_history[user_id] = history
    save_data()
    if len(history) % 3 == 0:
        extract_profile(user_id)
    return anna_reply

# ============ КЛАВИАТУРЫ ============
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
        [KeyboardButton(text="📚 Знания"), KeyboardButton(text="🧘 Дыхание")],
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

def education_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🧠 Нейробиология"), KeyboardButton(text="🧩 КПТ")],
        [KeyboardButton(text="🧘 ДБТ"), KeyboardButton(text="⬅️ Назад")]
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

# ============ КОМАНДЫ ============
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
        "Я не осуждаю. Спасибо, что поделился(ась). Срыв — это часть процесса.\n"
        "Давай разберём, что произошло, и скорректируем план. Что случилось перед срывом?",
        reply_markup=crisis_menu_keyboard()
    )

@dp.message(Command("plan"))
async def plan_command(message: types.Message):
    await message.answer(
        "📋 Твой план действий при тяге:\n"
        "1. Остановись и сделай паузу на 10 минут.\n"
        "2. Умойся ледяной водой или подыши 4-4-4-4.\n"
        "3. Позвони близкому или напиши мне.\n"
        "4. Если тяга выше 7/10 — «Сёрфинг по тяге».\n"
        "5. Вернись и расскажи, как прошло.",
        reply_markup=main_menu_keyboard()
    )

@dp.message(Command("goals"))
async def goals_command(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in user_goals:
        await message.answer(f"🎯 Твои цели:\n{user_goals[user_id]}")
    else:
        await message.answer("Цели пока не заданы. Напиши /goals <цель>.")

@dp.message(Command("diary"))
async def diary_command(message: types.Message):
    user_id = str(message.from_user.id)
    diary_step[user_id] = "situation"
    await message.answer("Давай сделаем запись в дневнике.\n\nШаг 1/4: Опиши ситуацию.")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "ℹ️ Помощь и контакты:\n\n" + HOTLINES +
        "\n\nДоступные команды:\n"
        "/menu — главное меню\n"
        "/crisis — кризисное меню\n"
        "/mood — оценка состояния\n"
        "/sober — дни чистоты\n"
        "/relapse — отметить срыв\n"
        "/plan — план действий\n"
        "/goals — цели\n"
        "/diary — дневник\n"
        "/education — психообразование\n"
        "/export — экспорт данных\n"
        "/feedback — обратная связь\n"
        "/reset — удалить все данные"
    )

@dp.message(Command("education"))
async def education_command(message: types.Message):
    await message.answer("📚 Что хочешь узнать?", reply_markup=education_keyboard())

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
    await message.answer(report)

@dp.message(Command("feedback"))
async def feedback_command(message: types.Message):
    await message.answer(
        "Насколько полезной была наша последняя техника или разговор?\n"
        "Оцени от 1 до 5:",
        reply_markup=feedback_keyboard()
    )

@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    user_id = str(message.from_user.id)
    await message.answer(
        "Вы уверены, что хотите удалить все данные? Это действие необратимо.\n"
        "Напишите «Да, удалить» (или просто «Удалить») для подтверждения."
    )
    interview_step[user_id] = "confirm_reset"

@dp.message(Command("stop_care"))
async def stop_care_command(message: types.Message):
    care_mode[str(message.from_user.id)] = False
    save_data()
    await message.answer("Поддержка приостановлена. Ты можешь включить её снова в настройках.")

@dp.message(lambda message: message.voice is not None)
async def handle_voice(message: types.Message):
    await message.answer("Я слышу тебя. Опиши текстом. 💚")

# ============ ОСНОВНОЙ ОБРАБОТЧИК ============
@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text

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

    if interview_step.get(user_id) == "confirm_reset":
        text_lower = text.lower().strip()
        if text_lower in ["да, удалить", "да удалить", "удалить", "да", "подтверждаю", "yes", "delete"]:
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
            feedback_data.pop(user_id, None)
            daily_reminders.pop(user_id, None)
            education_step.pop(user_id, None)
            save_data()
            await message.answer("Все данные удалены. Чтобы начать заново, напиши /start.")
            return
        else:
            interview_step.pop(user_id, None)
            await message.answer("Сброс отменён.")
            return

    if interview_step.get(user_id) == "gender":
        if text in ["Мужской", "Женский", "Не важно"]:
            if text == "Мужской":
                patient_profiles[user_id]["gender"] = "мужской"
            elif text == "Женский":
                patient_profiles[user_id]["gender"] = "женский"
            else:
                patient_profiles[user_id]["gender"] = "не указан"
            save_data()
            interview_step[user_id] = "problem"
            await message.answer("Спасибо. С чем ты хочешь работать? Например: зависимость, тревога, депрессия, стресс...")
        else:
            await message.answer("Пожалуйста, выбери один из вариантов на кнопках.", reply_markup=gender_keyboard())
        return

    if text == "🚨 Мне плохо сейчас":
        await message.answer("Выбери, что происходит:", reply_markup=crisis_menu_keyboard())
        return
    elif text == "🆘 Я на грани":
        await message.answer(
            "Ты на грани? Давай продержимся вместе.\n"
            "1. Умойся ледяной водой.\n"
            "2. Дыши 4-4-4-4.\n"
            "3. Позвони близкому или напиши мне.\n\n"
            "Если тяга выше 7/10 — «Сёрфинг по тяге»: тяга нарастает, достигает пика и спадает. Наблюдай за ней.",
            reply_markup=craving_keyboard()
        )
        return
    elif text == "📊 Моё состояние":
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
        goals = user_goals.get(user_id, "")
        if goals:
            await message.answer(f"Твои цели:\n{goals}\n\nЧтобы добавить новую, напиши: /goals <цель>", reply_markup=main_menu_keyboard())
        else:
            await message.answer("Цели пока не заданы. Напиши: /goals <цель>", reply_markup=main_menu_keyboard())
        return
    elif text == "📚 Знания":
        await message.answer("📚 Что хочешь узнать?", reply_markup=education_keyboard())
        return
    elif text == "🧠 Нейробиология":
        await message.answer(PSYCHOEDUCATION["neuro"], reply_markup=education_keyboard())
        return
    elif text == "🧩 КПТ":
        await message.answer(PSYCHOEDUCATION["cbt"], reply_markup=education_keyboard())
        return
    elif text == "🧘 ДБТ":
        await message.answer(PSYCHOEDUCATION["dbt"], reply_markup=education_keyboard())
        return
    elif text == "🧘 Дыхание":
        await message.answer(
            "🧘 *Дыхание по квадрату (4-4-4-4)*\n\n"
            "1. Вдох — 4 секунды\n"
            "2. Пауза — 4 секунды\n"
            "3. Выдох — 4 секунды\n"
            "4. Пауза — 4 секунды\n\n"
            "Повтори 5 раз. Это снижает тревогу за 1–2 минуты.",
            reply_markup=main_menu_keyboard()
        )
        return
    elif text == "ℹ️ Помощь и контакты":
        await message.answer(HOTLINES, reply_markup=main_menu_keyboard())
        return
    elif text == "⚙️ Настройки":
        await message.answer("Настройки:", reply_markup=settings_menu_keyboard())
        return
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
            "Если паника не проходит, позвони 112 или доверенному лицу.",
            reply_markup=crisis_menu_keyboard()
        )
        return
    elif text == "😢 Очень грустно, нет сил":
        await message.answer(
            "Мне жаль, что тебе так тяжело. Я хочу помочь.\n\n"
            "Есть ли у тебя мысли о том, чтобы навредить себе? (да/нет)"
        )
        emotion_step[user_id] = "suicide_risk_1"
        return
    elif text == "💔 Я сорвался":
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
        await message.answer(HOTLINES, reply_markup=crisis_menu_keyboard())
        return
    elif text == "⬅️ Назад в главное меню":
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
        return
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
            "Напишите «Да, удалить» (или просто «Удалить») для подтверждения."
        )
        interview_step[user_id] = "confirm_reset"
        return
    elif text.lower() == "как помочь близкому":
        await message.answer(
            "Если ты близкий человек зависимого:\n"
            "1. Заботься о себе — ты не можешь помочь, если выгорел(а).\n"
            "2. Устанавливай границы: не потакай употреблению, не покрывай.\n"
            "3. Не вини себя — зависимость это болезнь.\n"
            "4. Поддерживай, но не контролируй.\n"
            "5. Обратись за поддержкой к специалистам или в группы для созависимых.",
            reply_markup=main_menu_keyboard()
        )
        return

    if emotion_step.get(user_id) == "choose":
        valid_emotions = ["Грусть", "Тревога", "Злость", "Одиночество", "Стыд", "Страх", "Радость", "Усталость"]
        if text in valid_emotions:
            emotion_step[user_id] = "intensity"
            patient_memory[user_id]["last_emotion"] = text
            save_data()
            await message.answer(f"Ты выбрал(а) {text}. Оцени интенсивность от 1 до 10:", reply_markup=mood_keyboard())
        else:
            await message.answer("Пожалуйста, выбери эмоцию из кнопок.", reply_markup=emotion_keyboard())
        return

    if diary_step.get(user_id):
        step = diary_step[user_id]
        if step == "situation":
            patient_memory[user_id]["diary_situation"] = text
            diary_step[user_id] = "thought"
            await message.answer("Шаг 2/4: Какая мысль возникла в этой ситуации?")
            return
        elif step == "thought":
            patient_memory[user_id]["diary_thought"] = text
            diary_step[user_id] = "emotion"
            await message.answer("Шаг 3/4: Что ты почувствовал(а)? (одно слово)")
            return
        elif step == "emotion":
            patient_memory[user_id]["diary_emotion"] = text
            diary_step[user_id] = "action"
            await message.answer("Шаг 4/4: Что ты сделал(а) в этой ситуации?")
            return
        elif step == "action":
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
            for k in ["diary_situation", "diary_thought", "diary_emotion"]:
                patient_memory[user_id].pop(k, None)
            save_data()
            await message.answer("Запись сохранена. Спасибо, что поделился(ась). 💚", reply_markup=main_menu_keyboard())
            return

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
            await message.answer("Пожалуйста, позвони 8-800-2000-122 или 112. Я не могу заменить специалиста.", reply_markup=crisis_menu_keyboard())
            emotion_step.pop(user_id, None)
        return
    elif emotion_step.get(user_id) == "suicide_risk_3":
        if text.lower() in ["да", "yes", "есть"]:
            await message.answer(
                "Сейчас очень важно, чтобы ты позвонил(а) 112 или попросил(а) кого-то быть рядом.\n"
                "Я не могу продолжать терапию в таком состоянии. Набери номер экстренной службы.",
                reply_markup=crisis_menu_keyboard()
            )
        else:
            await message.answer("Пожалуйста, обратись к близким или позвони на горячую линию 8-800-2000-122.", reply_markup=crisis_menu_keyboard())
        emotion_step.pop(user_id, None)
        return

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

        if emotion_step.get(user_id) == "intensity":
            emotion = patient_memory[user_id].get("last_emotion", "")
            if emotion:
                mood_journal[user_id].append(f"[Эмоция] {emotion}: {v}/10")
                save_data()
                await callback.message.answer(f"Записал: {emotion} ({v}/10). Спасибо, что поделился(ась).", reply_markup=main_menu_keyboard())
                emotion_step.pop(user_id, None)
            else:
                await callback.message.answer("Произошла ошибка, попробуй ещё раз.", reply_markup=emotion_keyboard())
        else:
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
    elif data.startswith("fb_"):
        fb_val = int(data.split("_")[1])
        if user_id not in feedback_data:
            feedback_data[user_id] = []
        feedback_data[user_id].append(fb_val)
        save_data()
        await callback.message.answer("Спасибо за обратную связь! Это помогает мне стать лучше. 💚")
        await callback.answer()
    else:
        await callback.answer()

# ============ ФОНОВЫЕ ЗАДАЧИ ============
async def send_reminders():
    while True:
        for uid in list(dialogue_history.keys()):
            patient_now = get_patient_time(uid)
            patient_time_str = patient_now.strftime("%H:%M")
            patient_date_str = patient_now.strftime("%Y-%m-%d")

            if patient_time_str == "09:00":
                last_date = daily_reminders.get(uid, {}).get("morning")
                if last_date != patient_date_str:
                    try:
                        await bot.send_message(uid, "🌅 Доброе утро! Оцени своё состояние:", reply_markup=mood_keyboard())
                        daily_reminders.setdefault(uid, {})["morning"] = patient_date_str
                        save_data()
                    except:
                        pass

            if patient_time_str == "21:00":
                last_date = daily_reminders.get(uid, {}).get("evening")
                if last_date != patient_date_str:
                    try:
                        await bot.send_message(uid, "🌙 Как прошёл день? Оцени своё состояние:", reply_markup=mood_keyboard())
                        daily_reminders.setdefault(uid, {})["evening"] = patient_date_str
                        save_data()
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

# ============ HTTP-СЕРВЕР ДЛЯ RENDER ============
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

# ============ ЗАПУСК ============
async def main():
    load_data()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(send_reminders())
    asyncio.create_task(send_hourly_care())
    asyncio.create_task(send_congratulations())
    asyncio.create_task(smart_reminders())
    threading.Thread(target=start_http_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())