from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class ZodiacSign:
    name: str
    name_en: str
    symbol: str
    element: str
    dates: str
    ruling_planet: str

ZODIAC_SIGNS = {
    "aries": ZodiacSign("Овен", "Aries", "♈", "Огонь", "21.03 - 19.04", "Марс"),
    "taurus": ZodiacSign("Телец", "Taurus", "♉", "Земля", "20.04 - 20.05", "Венера"),
    "gemini": ZodiacSign("Близнецы", "Gemini", "♊", "Воздух", "21.05 - 20.06", "Меркурий"),
    "cancer": ZodiacSign("Рак", "Cancer", "♋", "Вода", "21.06 - 22.07", "Луна"),
    "leo": ZodiacSign("Лев", "Leo", "♌", "Огонь", "23.07 - 22.08", "Солнце"),
    "virgo": ZodiacSign("Дева", "Virgo", "♍", "Земля", "23.08 - 22.09", "Меркурий"),
    "libra": ZodiacSign("Весы", "Libra", "♎", "Воздух", "23.09 - 22.10", "Венера"),
    "scorpio": ZodiacSign("Скорпион", "Scorpio", "♏", "Вода", "23.10 - 21.11", "Плутон"),
    "sagittarius": ZodiacSign("Стрелец", "Sagittarius", "♐", "Огонь", "22.11 - 21.12", "Юпитер"),
    "capricorn": ZodiacSign("Козерог", "Capricorn", "♑", "Земля", "22.12 - 19.01", "Сатурн"),
    "aquarius": ZodiacSign("Водолей", "Aquarius", "♒", "Воздух", "20.01 - 18.02", "Уран"),
    "pisces": ZodiacSign("Рыбы", "Pisces", "♓", "Вода", "19.02 - 20.03", "Нептун"),
}

def get_zodiac_by_date(birth_date: str) -> Optional[str]:
    """Определить знак зодиака по дате рождения"""
    try:
        # Пробуем разные форматы даты
        for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                date = datetime.strptime(birth_date, fmt)
                break
            except ValueError:
                continue
        else:
            return None
        
        month = date.month
        day = date.day
        
        if (month == 3 and day >= 21) or (month == 4 and day <= 19):
            return "aries"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            return "taurus"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
            return "gemini"
        elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
            return "cancer"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            return "leo"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            return "virgo"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
            return "libra"
        elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
            return "scorpio"
        elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
            return "sagittarius"
        elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
            return "capricorn"
        elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
            return "aquarius"
        else:
            return "pisces"
    except Exception:
        return None

def get_zodiac_info(zodiac_key: str) -> Optional[ZodiacSign]:
    """Получить информацию о знаке зодиака"""
    return ZODIAC_SIGNS.get(zodiac_key)

def get_compatibility_score(sign1: str, sign2: str) -> int:
    """Базовая совместимость по стихиям"""
    if sign1 not in ZODIAC_SIGNS or sign2 not in ZODIAC_SIGNS:
        return 50
    
    element1 = ZODIAC_SIGNS[sign1].element
    element2 = ZODIAC_SIGNS[sign2].element
    
    compatibility = {
        ("Огонь", "Огонь"): 80,
        ("Огонь", "Воздух"): 90,
        ("Огонь", "Земля"): 50,
        ("Огонь", "Вода"): 40,
        ("Воздух", "Воздух"): 75,
        ("Воздух", "Земля"): 55,
        ("Воздух", "Вода"): 60,
        ("Земля", "Земля"): 85,
        ("Земля", "Вода"): 90,
        ("Вода", "Вода"): 80,
    }
    
    key = (element1, element2) if (element1, element2) in compatibility else (element2, element1)
    return compatibility.get(key, 65)