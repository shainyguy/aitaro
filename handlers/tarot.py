from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random

from database import get_user, can_use_free_reading, increment_readings, save_reading
from utils.keyboards import get_tarot_menu, get_ask_question_keyboard, get_subscription_keyboard, get_back_keyboard
from config import config

router = Router()


class TarotStates(StatesGroup):
    waiting_question = State()


# Хранилище текущего типа расклада
user_spread_type = {}

# ==================== КОЛОДА ТАРО ====================

MAJOR_ARCANA = [
    {"name": "Шут", "keywords": ["новые начинания", "спонтанность", "свобода"]},
    {"name": "Маг", "keywords": ["сила воли", "творчество", "мастерство"]},
    {"name": "Верховная Жрица", "keywords": ["интуиция", "тайны", "мудрость"]},
    {"name": "Императрица", "keywords": ["плодородие", "красота", "изобилие"]},
    {"name": "Император", "keywords": ["власть", "структура", "стабильность"]},
    {"name": "Иерофант", "keywords": ["традиции", "духовность", "наставничество"]},
    {"name": "Влюблённые", "keywords": ["любовь", "выбор", "гармония"]},
    {"name": "Колесница", "keywords": ["победа", "воля", "движение вперёд"]},
    {"name": "Сила", "keywords": ["внутренняя сила", "мужество", "терпение"]},
    {"name": "Отшельник", "keywords": ["самопознание", "уединение", "мудрость"]},
    {"name": "Колесо Фортуны", "keywords": ["удача", "перемены", "судьба"]},
    {"name": "Справедливость", "keywords": ["справедливость", "истина", "карма"]},
    {"name": "Повешенный", "keywords": ["пауза", "жертва", "новый взгляд"]},
    {"name": "Смерть", "keywords": ["трансформация", "конец", "перерождение"]},
    {"name": "Умеренность", "keywords": ["баланс", "гармония", "терпение"]},
    {"name": "Дьявол", "keywords": ["зависимость", "материализм", "страсть"]},
    {"name": "Башня", "keywords": ["разрушение", "откровение", "освобождение"]},
    {"name": "Звезда", "keywords": ["надежда", "вдохновение", "исцеление"]},
    {"name": "Луна", "keywords": ["иллюзии", "интуиция", "страхи"]},
    {"name": "Солнце", "keywords": ["радость", "успех", "оптимизм"]},
    {"name": "Суд", "keywords": ["возрождение", "призыв", "прощение"]},
    {"name": "Мир", "keywords": ["завершение", "достижение", "целостность"]},
]

SPREAD_CONFIGS = {
    "tarot_one": {
        "name": "Карта дня", 
        "count": 1, 
        "positions": ["Послание дня"]
    },
    "tarot_three": {
        "name": "Прошлое — Настоящее — Будущее", 
        "count": 3, 
        "positions": ["Прошлое", "Настоящее", "Будущее"]
    },
    "tarot_love": {
        "name": "Расклад на отношения", 
        "count": 3, 
        "positions": ["Вы", "Партнёр", "Отношения"]
    },
    "tarot_career": {
        "name": "Расклад на карьеру", 
        "count": 3, 
        "positions": ["Ситуация", "Препятствия", "Совет"]
    },
    "tarot_yesno": {
        "name": "Да/Нет", 
        "count": 1, 
        "positions": ["Ответ"]
    },
    "tarot_celtic": {
        "name": "Кельтский крест", 
        "count": 5, 
        "positions": ["Ситуация", "Препятствие", "Основа", "Прошлое", "Итог"]
    },
}


def draw_cards(count: int) -> list:
    """Вытянуть карты"""
    cards = random.sample(MAJOR_ARCANA, count)
    result = []
    for card in cards:
        is_reversed = random.choice([True, False])
        result.append({
            "name": card["name"],
            "keywords": card["keywords"],
            "is_reversed": is_reversed,
            "display_name": f"{card['name']} {'(перевёрнутая)' if is_reversed else ''}"
        })
    return result


def generate_interpretation(cards: list, question: str, positions: list) -> str:
    """Генерация интерпретации"""
    interpretation = "✨ *Карты открыли мне следующее...*\n\n"
    
    for i, card in enumerate(cards):
        position = positions[i] if i < len(positions) else f"Позиция {i+1}"
        status = "🔄" if card["is_reversed"] else "⬆️"
        
        if card["is_reversed"]:
            meaning = f"Энергия {card['name']} заблокирована. Возможны задержки в сфере: {', '.join(card['keywords'])}."
        else:
            meaning = f"Карта несёт позитивную энергию: {', '.join(card['keywords'])}."
        
        interpretation += f"*{position}:* {status} {card['display_name']}\n"
        interpretation += f"_{meaning}_\n\n"
    
    # Общий вывод
    positive_count = sum(1 for c in cards if not c["is_reversed"])
    if positive_count > len(cards) // 2:
        conclusion = "🌟 *Вывод:* Карты благоприятны! Действуй смело, энергия на твоей стороне."
    elif positive_count == len(cards) // 2:
        conclusion = "⚖️ *Вывод:* Ситуация неоднозначна. Прислушайся к интуиции и будь внимателен к деталям."
    else:
        conclusion = "🌙 *Вывод:* Сейчас время для паузы и размышлений. Не торопись с решениями."
    
    interpretation += conclusion
    
    # Для Да/Нет
    if len(cards) == 1 and "Ответ" in positions:
        if cards[0]["is_reversed"]:
            interpretation += "\n\n❌ *Ответ: Скорее НЕТ* — но всё в твоих руках."
        else:
            interpretation += "\n\n✅ *Ответ: Скорее ДА* — звёзды благоволят!"
    
    return interpretation


@router.callback_query(F.data == "tarot_menu")
async def show_tarot_menu(callback: CallbackQuery):
    """Показать меню Таро"""
    await callback.message.edit_text(
        "🎴 *Расклады Таро*\n\n"
        "Выбери тип расклада:\n\n"
        "• *Карта дня* — общее послание на сегодня\n"
        "• *3 карты* — прошлое, настоящее, будущее\n"
        "• *На отношения* — анализ любовной ситуации\n"
        "• *На карьеру* — рабочие вопросы\n"
        "• *Да/Нет* — быстрый ответ\n"
        "• *Кельтский крест* — глубокий анализ",
        parse_mode="Markdown",
        reply_markup=get_tarot_menu()
    )


@router.callback_query(F.data.in_(SPREAD_CONFIGS.keys()))
async def select_spread(callback: CallbackQuery, state: FSMContext):
    """Выбор типа расклада"""
    spread_type = callback.data
    user_id = callback.from_user.id
    
    # Проверяем лимит бесплатных раскладов
    can_use = await can_use_free_reading(user_id, config.FREE_READINGS_LIMIT)
    if not can_use:
        await callback.message.edit_text(
            "⭐ *Бесплатный расклад уже использован*\n\n"
            "Для безлимитных раскладов оформи подписку:",
            parse_mode="Markdown",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    user_spread_type[user_id] = spread_type
    spread_config = SPREAD_CONFIGS[spread_type]
    
    await callback.message.edit_text(
        f"🔮 *{spread_config['name']}*\n\n"
        "Задай свой вопрос картам.\n"
        "Будь конкретен — карты любят ясность.\n\n"
        "Примеры:\n"
        "• «Стоит ли мне менять работу?»\n"
        "• «Как развиваются мои отношения с...?»\n"
        "• «Что мне нужно знать о ситуации с...?»",
        parse_mode="Markdown",
        reply_markup=get_ask_question_keyboard()
    )
    await state.set_state(TarotStates.waiting_question)


@router.callback_query(F.data == "no_question")
async def no_question(callback: CallbackQuery, state: FSMContext):
    """Расклад без вопроса"""
    await perform_reading(callback, state, "Общее послание на данный момент")


@router.message(TarotStates.waiting_question)
async def process_question(message: Message, state: FSMContext):
    """Обработка вопроса"""
    question = message.text.strip()
    await perform_reading(message, state, question)


async def perform_reading(event, state: FSMContext, question: str):
    """Выполнение расклада"""
    user_id = event.from_user.id
    spread_type = user_spread_type.get(user_id, "tarot_three")
    spread_config = SPREAD_CONFIGS[spread_type]
    
    # Отправляем сообщение о процессе
    if isinstance(event, CallbackQuery):
        loading_msg = await event.message.edit_text(
            "🔮 *Перемешиваю колоду...*\n\n"
            "✨ Карты выбирают свои позиции...",
            parse_mode="Markdown"
        )
    else:
        loading_msg = await event.answer(
            "🔮 *Перемешиваю колоду...*\n\n"
            "✨ Карты выбирают свои позиции...",
            parse_mode="Markdown"
        )
    
    # Тянем карты
    cards = draw_cards(spread_config["count"])
    
    # Формируем текст с картами
    cards_text = "🎴 *Выпавшие карты:*\n\n"
    for i, card in enumerate(cards):
        position = spread_config["positions"][i] if i < len(spread_config["positions"]) else f"Позиция {i+1}"
        status = "🔄" if card["is_reversed"] else "⬆️"
        cards_text += f"*{position}:* {status} {card['display_name']}\n"
    
    # Генерируем интерпретацию
    interpretation = generate_interpretation(cards, question, spread_config["positions"])
    
    # Полный текст ответа
    full_response = (
        f"🔮 *{spread_config['name']}*\n\n"
        f"❓ *Твой вопрос:* {question}\n\n"
        f"{cards_text}\n"
        f"📜 *Интерпретация:*\n"
        f"{interpretation}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"_Помни: карты показывают возможности, но выбор всегда за тобой_ ✨"
    )
    
    # Увеличиваем счётчик раскладов
    await increment_readings(user_id)
    
    # Сохраняем расклад
    card_names = [card["display_name"] for card in cards]
    await save_reading(
        user_id=user_id,
        reading_type=spread_type,
        question=question,
        cards=card_names,
        interpretation=interpretation
    )
    
    # Отправляем результат
    await loading_msg.edit_text(
        full_response,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("tarot_menu")
    )
    
    await state.clear()