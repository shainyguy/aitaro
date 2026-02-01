from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from database import get_user, has_active_subscription
from services.gigachat_service import gigachat_service
from utils.keyboards import get_back_keyboard, get_subscription_keyboard
from utils.zodiac import ZODIAC_SIGNS, get_zodiac_info

router = Router()


def get_horoscope_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 На сегодня", callback_data="horo_today")],
        [InlineKeyboardButton(text="📆 На завтра", callback_data="horo_tomorrow")],
        [InlineKeyboardButton(text="🗓️ На неделю", callback_data="horo_week")],
        [InlineKeyboardButton(text="📊 На месяц", callback_data="horo_month")],
        [
            InlineKeyboardButton(text="💰 Финансовый", callback_data="horo_money"),
            InlineKeyboardButton(text="💕 Любовный", callback_data="horo_love")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_zodiac_keyboard(prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора знака"""
    zodiac_list = [
        ("♈ Овен", "aries"), ("♉ Телец", "taurus"), ("♊ Близнецы", "gemini"),
        ("♋ Рак", "cancer"), ("♌ Лев", "leo"), ("♍ Дева", "virgo"),
        ("♎ Весы", "libra"), ("♏ Скорпион", "scorpio"), ("♐ Стрелец", "sagittarius"),
        ("♑ Козерог", "capricorn"), ("♒ Водолей", "aquarius"), ("♓ Рыбы", "pisces"),
    ]
    
    buttons = []
    for i in range(0, 12, 3):
        row = [
            InlineKeyboardButton(text=z[0], callback_data=f"{prefix}_{z[1]}")
            for z in zodiac_list[i:i+3]
        ]
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="horoscope_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "horoscope_menu")
async def show_horoscope_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    zodiac = user.get('zodiac_sign', '') if user else ''
    zodiac_info = get_zodiac_info(zodiac) if zodiac else None
    
    text = "⭐ *Гороскопы*\n\n"
    if zodiac_info:
        text += f"Твой знак: {zodiac_info.symbol} *{zodiac_info.name}*\n\n"
    text += "Выбери тип гороскопа:"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_horoscope_menu())


@router.callback_query(F.data.in_(["horo_today", "horo_tomorrow", "horo_week", "horo_month", "horo_money", "horo_love"]))
async def select_horoscope_type(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    zodiac = user.get('zodiac_sign', '') if user else ''
    
    horo_type = callback.data.replace("horo_", "")
    
    # Для недели и месяца нужна подписка
    if horo_type in ["week", "month"] and not await has_active_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "⭐ *Расширенные гороскопы доступны по подписке*\n\n"
            "Оформи премиум для доступа к гороскопам на неделю и месяц:",
            parse_mode="Markdown",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    if zodiac:
        await generate_horoscope(callback, zodiac, horo_type)
    else:
        await callback.message.edit_text(
            "Выбери свой знак зодиака:",
            reply_markup=get_zodiac_keyboard(f"genhoro_{horo_type}")
        )


@router.callback_query(F.data.startswith("genhoro_"))
async def generate_horoscope_for_sign(callback: CallbackQuery):
    parts = callback.data.split("_")
    horo_type = parts[1]
    zodiac = parts[2]
    
    await generate_horoscope(callback, zodiac, horo_type)


async def generate_horoscope(callback: CallbackQuery, zodiac: str, horo_type: str):
    zodiac_info = get_zodiac_info(zodiac)
    if not zodiac_info:
        await callback.answer("Знак не найден", show_alert=True)
        return
    
    period_names = {
        "today": "сегодня",
        "tomorrow": "завтра",
        "week": "неделю",
        "month": "месяц",
        "money": "неделю (финансы)",
        "love": "неделю (любовь)"
    }
    
    period = period_names.get(horo_type, "сегодня")
    
    await callback.message.edit_text(
        f"🔮 Составляю гороскоп для {zodiac_info.symbol} *{zodiac_info.name}* на {period}...",
        parse_mode="Markdown"
    )
    
    # Генерируем гороскоп
    if horo_type == "money":
        horoscope = await gigachat_service.generate_money_forecast(zodiac_info.name)
        title = f"💰 Финансовый гороскоп для {zodiac_info.symbol} {zodiac_info.name}"
    elif horo_type == "love":
        horoscope = await gigachat_service.generate_horoscope(zodiac_info.name, "неделю в сфере любви")
        title = f"💕 Любовный гороскоп для {zodiac_info.symbol} {zodiac_info.name}"
    else:
        horoscope = await gigachat_service.generate_horoscope(zodiac_info.name, period)
        title = f"⭐ Гороскоп для {zodiac_info.symbol} {zodiac_info.name} на {period}"
    
    text = f"*{title}*\n\n{horoscope}"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("horoscope_menu")
    )