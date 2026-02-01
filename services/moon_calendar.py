from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
import math

@dataclass
class MoonDay:
    day: int
    phase: str
    phase_emoji: str
    sign: str
    sign_emoji: str
    is_growing: bool
    illumination: float
    recommendations: dict
    beauty: dict
    warnings: list

# Лунные фазы
MOON_PHASES = {
    0: ("🌑 Новолуние", "new"),
    1: ("🌒 Молодая луна", "waxing_crescent"),
    2: ("🌓 Первая четверть", "first_quarter"),
    3: ("🌔 Прибывающая луна", "waxing_gibbous"),
    4: ("🌕 Полнолуние", "full"),
    5: ("🌖 Убывающая луна", "waning_gibbous"),
    6: ("🌗 Последняя четверть", "last_quarter"),
    7: ("🌘 Старая луна", "waning_crescent"),
}

# Знаки зодиака для Луны
MOON_SIGNS = [
    ("♈ Овен", "Aries", "Огонь"),
    ("♉ Телец", "Taurus", "Земля"),
    ("♊ Близнецы", "Gemini", "Воздух"),
    ("♋ Рак", "Cancer", "Вода"),
    ("♌ Лев", "Leo", "Огонь"),
    ("♍ Дева", "Virgo", "Земля"),
    ("♎ Весы", "Libra", "Воздух"),
    ("♏ Скорпион", "Scorpio", "Вода"),
    ("♐ Стрелец", "Sagittarius", "Огонь"),
    ("♑ Козерог", "Capricorn", "Земля"),
    ("♒ Водолей", "Aquarius", "Воздух"),
    ("♓ Рыбы", "Pisces", "Вода"),
]

# Рекомендации по лунным дням
MOON_DAY_RECOMMENDATIONS = {
    1: {"good": ["новые начинания", "планирование"], "bad": ["стрижка", "операции"], "energy": 3},
    2: {"good": ["накопление", "покупки"], "bad": ["конфликты"], "energy": 4},
    3: {"good": ["активные действия", "спорт"], "bad": ["лень"], "energy": 5},
    4: {"good": ["работа с информацией", "учёба"], "bad": ["важные решения"], "energy": 4},
    5: {"good": ["духовные практики", "медитация"], "bad": ["переедание"], "energy": 3},
    6: {"good": ["общение", "любовь"], "bad": ["одиночество"], "energy": 5},
    7: {"good": ["молитвы", "просьбы"], "bad": ["ложь"], "energy": 4},
    8: {"good": ["трансформации", "очищение"], "bad": ["застолья"], "energy": 3},
    9: {"good": ["избавление от лишнего"], "bad": ["новые проекты"], "energy": 2},
    10: {"good": ["семья", "дом", "традиции"], "bad": ["путешествия"], "energy": 5},
    11: {"good": ["сила", "энергия", "власть"], "bad": ["слабость"], "energy": 5},
    12: {"good": ["благотворительность", "помощь"], "bad": ["эгоизм"], "energy": 4},
    13: {"good": ["обучение", "группы"], "bad": ["одиночные действия"], "energy": 4},
    14: {"good": ["призыв", "манифестация"], "bad": ["уныние"], "energy": 5},
    15: {"good": ["контроль эмоций"], "bad": ["агрессия", "споры"], "energy": 3},
    16: {"good": ["гармония", "баланс"], "bad": ["крайности"], "energy": 4},
    17: {"good": ["женская энергия", "танцы"], "bad": ["алкоголь"], "energy": 5},
    18: {"good": ["смирение", "принятие"], "bad": ["зависть"], "energy": 3},
    19: {"good": ["одиночество", "размышления"], "bad": ["толпа"], "energy": 2},
    20: {"good": ["духовные подвиги"], "bad": ["материализм"], "energy": 4},
    21: {"good": ["активность", "храбрость"], "bad": ["трусость"], "energy": 5},
    22: {"good": ["знания", "мудрость"], "bad": ["невежество"], "energy": 4},
    23: {"good": ["защита", "охрана"], "bad": ["пассивность"], "energy": 3},
    24: {"good": ["творчество", "пробуждение"], "bad": ["разрушение"], "energy": 5},
    25: {"good": ["созерцание", "мечты"], "bad": ["активность"], "energy": 3},
    26: {"good": ["молчание", "пост"], "bad": ["болтовня"], "energy": 2},
    27: {"good": ["путешествия", "вода"], "bad": ["тайны"], "energy": 4},
    28: {"good": ["лёгкость", "радость"], "bad": ["уныние"], "energy": 5},
    29: {"good": ["очищение", "завершение"], "bad": ["начинания"], "energy": 2},
    30: {"good": ["прощение", "благодарность"], "bad": ["обиды"], "energy": 3},
}

# Календарь красоты
BEAUTY_CALENDAR = {
    "hair_cut": {
        "good_days": [5, 8, 11, 13, 14, 21, 22, 27],
        "bad_days": [9, 15, 19, 23, 29],
        "good_signs": ["Лев", "Дева", "Весы"],
        "bad_signs": ["Рыбы", "Рак"],
    },
    "hair_color": {
        "good_days": [5, 8, 11, 14, 21, 27],
        "bad_days": [9, 15, 19, 29],
        "good_signs": ["Лев", "Весы", "Стрелец"],
        "bad_signs": ["Рыбы", "Скорпион"],
    },
    "manicure": {
        "good_days": [2, 5, 8, 11, 13, 14, 17, 21, 27],
        "bad_days": [9, 19, 29],
        "good_signs": ["Телец", "Дева", "Козерог", "Весы"],
        "bad_signs": ["Рыбы"],
    },
    "cosmetic_procedures": {
        "good_days": [6, 7, 14, 16, 24, 28],
        "bad_days": [9, 15, 19, 23, 29],
        "good_signs": ["Телец", "Весы", "Рыбы"],
        "bad_signs": ["Овен", "Скорпион"],
    },
    "epilation": {
        "good_days": [3, 4, 7, 18, 26, 27],
        "bad_days": [1, 2, 14, 15],
        "good_signs": ["Козерог", "Дева"],
        "bad_signs": ["Лев", "Овен"],
        "note": "Лучше на убывающей луне"
    }
}


def calculate_moon_phase(date: datetime) -> tuple:
    """Расчёт фазы луны (упрощённый алгоритм)"""
    # Известное новолуние: 6 января 2000, 18:14 UTC
    known_new_moon = datetime(2000, 1, 6, 18, 14)
    lunar_cycle = 29.530588853  # дней
    
    diff = (date - known_new_moon).total_seconds() / 86400
    lunations = diff / lunar_cycle
    current_phase = (lunations - int(lunations)) * lunar_cycle
    
    # Лунный день (1-30)
    moon_day = int(current_phase) + 1
    if moon_day > 30:
        moon_day = 30
    
    # Освещённость (0-100%)
    illumination = (1 - math.cos(2 * math.pi * current_phase / lunar_cycle)) / 2 * 100
    
    # Фаза (0-7)
    phase_index = int(current_phase / (lunar_cycle / 8))
    if phase_index > 7:
        phase_index = 7
    
    # Растущая или убывающая
    is_growing = current_phase < lunar_cycle / 2
    
    return moon_day, phase_index, illumination, is_growing


def get_moon_sign(date: datetime) -> tuple:
    """Получить знак, в котором находится Луна (упрощённо)"""
    # Луна проходит знак примерно за 2.5 дня
    days_since_epoch = (date - datetime(2000, 1, 1)).days
    sign_index = int((days_since_epoch / 2.5) % 12)
    return MOON_SIGNS[sign_index]


def get_moon_day_info(date: datetime = None) -> MoonDay:
    """Получить информацию о лунном дне"""
    if date is None:
        date = datetime.now()
    
    moon_day, phase_index, illumination, is_growing = calculate_moon_phase(date)
    phase_name, phase_key = MOON_PHASES[phase_index]
    moon_sign = get_moon_sign(date)
    
    recommendations = MOON_DAY_RECOMMENDATIONS.get(moon_day, {
        "good": ["нейтральный день"],
        "bad": [],
        "energy": 3
    })
    
    # Красота
    beauty = {}
    sign_name = moon_sign[0].split()[1]  # Получаем название знака без эмодзи
    
    for procedure, rules in BEAUTY_CALENDAR.items():
        is_good_day = moon_day in rules["good_days"]
        is_bad_day = moon_day in rules["bad_days"]
        is_good_sign = any(s in sign_name for s in rules["good_signs"])
        is_bad_sign = any(s in sign_name for s in rules["bad_signs"])
        
        if is_bad_day or is_bad_sign:
            status = "❌"
        elif is_good_day and is_good_sign:
            status = "✅✅"
        elif is_good_day or is_good_sign:
            status = "✅"
        else:
            status = "➖"
        
        beauty[procedure] = status
    
    # Предупреждения
    warnings = []
    if moon_day in [9, 15, 19, 29]:
        warnings.append("⚠️ Сатанинский лунный день — будьте осторожны")
    if phase_key == "full":
        warnings.append("🌕 Полнолуние — эмоции обострены")
    if phase_key == "new":
        warnings.append("🌑 Новолуние — низкая энергия")
    
    return MoonDay(
        day=moon_day,
        phase=phase_name,
        phase_emoji=phase_name.split()[0],
        sign=moon_sign[0],
        sign_emoji=moon_sign[0].split()[0],
        is_growing=is_growing,
        illumination=round(illumination, 1),
        recommendations=recommendations,
        beauty=beauty,
        warnings=warnings
    )


def get_beauty_calendar_text(date: datetime = None) -> str:
    """Получить текст календаря красоты"""
    moon = get_moon_day_info(date)
    
    beauty_names = {
        "hair_cut": "✂️ Стрижка",
        "hair_color": "🎨 Окрашивание",
        "manicure": "💅 Маникюр",
        "cosmetic_procedures": "💆 Косметология",
        "epilation": "🦵 Эпиляция",
    }
    
    text = f"🌙 *Лунный день:* {moon.day}\n"
    text += f"{moon.phase}\n"
    text += f"🔮 Луна в знаке: {moon.sign}\n\n"
    
    text += "💄 *Календарь красоты на сегодня:*\n\n"
    
    for proc, status in moon.beauty.items():
        text += f"{beauty_names.get(proc, proc)}: {status}\n"
    
    text += "\n📝 *Расшифровка:*\n"
    text += "✅✅ — идеально\n✅ — благоприятно\n➖ — нейтрально\n❌ — не рекомендуется\n"
    
    if moon.is_growing:
        text += "\n🌒 *Луна растущая* — хорошо для роста волос и ногтей"
    else:
        text += "\n🌘 *Луна убывающая* — хорошо для эпиляции и чистки"
    
    return text