from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AstroEvent:
    name: str
    start_date: datetime
    end_date: Optional[datetime]
    event_type: str  # retrograde, eclipse, aspect
    planet: str
    description: str
    recommendations: List[str]
    warnings: List[str]
    emoji: str

# Ретроградные периоды 2024-2025 (примерные даты)
RETROGRADE_PERIODS = [
    # Меркурий 2024
    {"planet": "Меркурий", "start": "2024-04-01", "end": "2024-04-25", "emoji": "☿️"},
    {"planet": "Меркурий", "start": "2024-08-05", "end": "2024-08-28", "emoji": "☿️"},
    {"planet": "Меркурий", "start": "2024-11-26", "end": "2024-12-15", "emoji": "☿️"},
    # Меркурий 2025
    {"planet": "Меркурий", "start": "2025-03-15", "end": "2025-04-07", "emoji": "☿️"},
    {"planet": "Меркурий", "start": "2025-07-18", "end": "2025-08-11", "emoji": "☿️"},
    {"planet": "Меркурий", "start": "2025-11-09", "end": "2025-11-29", "emoji": "☿️"},
    # Венера
    {"planet": "Венера", "start": "2025-03-02", "end": "2025-04-13", "emoji": "♀️"},
    # Марс
    {"planet": "Марс", "start": "2024-12-06", "end": "2025-02-24", "emoji": "♂️"},
    # Юпитер
    {"planet": "Юпитер", "start": "2024-10-09", "end": "2025-02-04", "emoji": "♃"},
    # Сатурн
    {"planet": "Сатурн", "start": "2024-06-29", "end": "2024-11-15", "emoji": "♄"},
    {"planet": "Сатурн", "start": "2025-07-13", "end": "2025-11-28", "emoji": "♄"},
]

# Затмения 2024-2025
ECLIPSES = [
    {"type": "Лунное", "date": "2024-03-25", "sign": "Весы", "emoji": "🌕"},
    {"type": "Солнечное", "date": "2024-04-08", "sign": "Овен", "emoji": "🌑"},
    {"type": "Лунное", "date": "2024-09-18", "sign": "Рыбы", "emoji": "🌕"},
    {"type": "Солнечное", "date": "2024-10-02", "sign": "Весы", "emoji": "🌑"},
    {"type": "Лунное", "date": "2025-03-14", "sign": "Дева", "emoji": "🌕"},
    {"type": "Солнечное", "date": "2025-03-29", "sign": "Овен", "emoji": "🌑"},
    {"type": "Лунное", "date": "2025-09-07", "sign": "Рыбы", "emoji": "🌕"},
    {"type": "Солнечное", "date": "2025-09-21", "sign": "Дева", "emoji": "🌑"},
]

RETROGRADE_EFFECTS = {
    "Меркурий": {
        "areas": ["коммуникации", "документы", "техника", "транспорт", "переговоры"],
        "recommendations": [
            "Перепроверяй все документы",
            "Делай резервные копии данных",
            "Не подписывай важные контракты",
            "Будь внимателен в общении",
            "Хорошо для завершения старых дел"
        ],
        "warnings": [
            "Возможны задержки в пути",
            "Техника может сбоить",
            "Могут всплыть старые проблемы",
            "Легко возникают недопонимания"
        ]
    },
    "Венера": {
        "areas": ["любовь", "отношения", "финансы", "красота", "ценности"],
        "recommendations": [
            "Переосмысли отношения",
            "Не делай дорогих покупок",
            "Хорошо для возвращения старой любви",
            "Пересмотри свои ценности"
        ],
        "warnings": [
            "Не начинай новые отношения",
            "Избегай пластических операций",
            "Финансовые решения отложи"
        ]
    },
    "Марс": {
        "areas": ["энергия", "действия", "конфликты", "спорт", "секс"],
        "recommendations": [
            "Контролируй агрессию",
            "Избегай конфликтов",
            "Хорошо для завершения проектов",
            "Занимайся мягкими практиками"
        ],
        "warnings": [
            "Повышен риск травм",
            "Не начинай войны и споры",
            "Энергия может быть нестабильной"
        ]
    },
    "Юпитер": {
        "areas": ["удача", "расширение", "образование", "путешествия", "философия"],
        "recommendations": [
            "Переосмысли свои цели",
            "Хорошо для духовной практики",
            "Заверши отложенное обучение"
        ],
        "warnings": [
            "Удача может быть нестабильной",
            "Не рискуй по-крупному"
        ]
    },
    "Сатурн": {
        "areas": ["карьера", "ответственность", "структуры", "ограничения"],
        "recommendations": [
            "Пересмотри карьерные цели",
            "Хорошо для внутренней работы",
            "Укрепляй фундамент"
        ],
        "warnings": [
            "Возможны задержки в карьере",
            "Старые обязательства напомнят о себе"
        ]
    }
}


def get_current_retrogrades() -> List[AstroEvent]:
    """Получить текущие ретроградные периоды"""
    now = datetime.now()
    active = []
    
    for period in RETROGRADE_PERIODS:
        start = datetime.strptime(period["start"], "%Y-%m-%d")
        end = datetime.strptime(period["end"], "%Y-%m-%d")
        
        if start <= now <= end:
            effects = RETROGRADE_EFFECTS.get(period["planet"], {})
            active.append(AstroEvent(
                name=f"{period['planet']} ретроградный",
                start_date=start,
                end_date=end,
                event_type="retrograde",
                planet=period["planet"],
                description=f"Затронутые сферы: {', '.join(effects.get('areas', []))}",
                recommendations=effects.get("recommendations", []),
                warnings=effects.get("warnings", []),
                emoji=period["emoji"]
            ))
    
    return active


def get_upcoming_events(days: int = 30) -> List[dict]:
    """Получить предстоящие события"""
    now = datetime.now()
    future = now + timedelta(days=days)
    events = []
    
    # Ретрограды
    for period in RETROGRADE_PERIODS:
        start = datetime.strptime(period["start"], "%Y-%m-%d")
        end = datetime.strptime(period["end"], "%Y-%m-%d")
        
        if now <= start <= future:
            events.append({
                "date": start,
                "type": "retrograde_start",
                "name": f"☿️ {period['planet']} входит в ретроград",
                "description": f"До {end.strftime('%d.%m.%Y')}"
            })
        elif now <= end <= future:
            events.append({
                "date": end,
                "type": "retrograde_end",
                "name": f"✅ {period['planet']} выходит из ретрограда",
                "description": "Можно возобновлять дела"
            })
    
    # Затмения
    for eclipse in ECLIPSES:
        date = datetime.strptime(eclipse["date"], "%Y-%m-%d")
        if now <= date <= future:
            events.append({
                "date": date,
                "type": "eclipse",
                "name": f"{eclipse['emoji']} {eclipse['type']} затмение",
                "description": f"В знаке {eclipse['sign']}"
            })
    
    events.sort(key=lambda x: x["date"])
    return events


def get_retrograde_alert_text() -> str:
    """Получить текст алерта о ретроградах"""
    current = get_current_retrogrades()
    upcoming = get_upcoming_events(14)
    
    text = "🔮 *Астрологические алерты*\n\n"
    
    if current:
        text += "⚠️ *Сейчас в ретрограде:*\n\n"
        for event in current:
            days_left = (event.end_date - datetime.now()).days
            text += f"{event.emoji} *{event.planet}*\n"
            text += f"   До {event.end_date.strftime('%d.%m.%Y')} ({days_left} дн.)\n"
            text += f"   _{event.description}_\n\n"
    else:
        text += "✅ *Сейчас нет ретроградных планет!*\n\n"
    
    if upcoming:
        text += "📅 *Ближайшие события:*\n\n"
        for event in upcoming[:5]:
            text += f"• {event['date'].strftime('%d.%m')} — {event['name']}\n"
    
    return text


def get_favorable_hours(zodiac_sign: str, date: datetime = None) -> dict:
    """Получить благоприятные часы для знака"""
    if date is None:
        date = datetime.now()
    
    # Планетарные часы (упрощённо)
    # Каждый час дня управляется планетой
    # Порядок: Солнце, Венера, Меркурий, Луна, Сатурн, Юпитер, Марс
    
    planetary_hours = {
        0: ("Сатурн", "♄"), 1: ("Юпитер", "♃"), 2: ("Марс", "♂"),
        3: ("Солнце", "☉"), 4: ("Венера", "♀"), 5: ("Меркурий", "☿"),
        6: ("Луна", "☽"), 7: ("Сатурн", "♄"), 8: ("Юпитер", "♃"),
        9: ("Марс", "♂"), 10: ("Солнце", "☉"), 11: ("Венера", "♀"),
        12: ("Меркурий", "☿"), 13: ("Луна", "☽"), 14: ("Сатурн", "♄"),
        15: ("Юпитер", "♃"), 16: ("Марс", "♂"), 17: ("Солнце", "☉"),
        18: ("Венера", "♀"), 19: ("Меркурий", "☿"), 20: ("Луна", "☽"),
        21: ("Сатурн", "♄"), 22: ("Юпитер", "♃"), 23: ("Марс", "♂"),
    }
    
    # Благоприятные планеты для знаков
    favorable_planets = {
        "aries": ["Марс", "Солнце", "Юпитер"],
        "taurus": ["Венера", "Луна"],
        "gemini": ["Меркурий", "Венера"],
        "cancer": ["Луна", "Юпитер"],
        "leo": ["Солнце", "Юпитер", "Марс"],
        "virgo": ["Меркурий", "Сатурн"],
        "libra": ["Венера", "Сатурн"],
        "scorpio": ["Марс", "Луна"],
        "sagittarius": ["Юпитер", "Солнце"],
        "capricorn": ["Сатурн", "Марс"],
        "aquarius": ["Сатурн", "Меркурий"],
        "pisces": ["Юпитер", "Луна", "Венера"],
    }
    
    good_planets = favorable_planets.get(zodiac_sign.lower(), ["Солнце", "Юпитер"])
    
    good_hours = []
    neutral_hours = []
    
    for hour, (planet, emoji) in planetary_hours.items():
        if planet in good_planets:
            good_hours.append((hour, planet, emoji))
        elif planet in ["Солнце", "Юпитер", "Венера"]:
            neutral_hours.append((hour, planet, emoji))
    
    return {
        "excellent": good_hours[:5],
        "good": neutral_hours[:3],
        "best_for_money": [h for h in good_hours if h[1] == "Юпитер"][:2],
        "best_for_love": [h for h in good_hours if h[1] == "Венера"][:2],
        "best_for_action": [h for h in good_hours if h[1] == "Марс"][:2],
    }