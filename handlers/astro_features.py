from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    get_user, has_active_subscription, has_purchased_service, 
    use_purchased_service, get_user_notifications, update_notification_setting
)
from services.gigachat_service import gigachat_service
from services.astro_events import get_retrograde_alert_text, get_favorable_hours, get_upcoming_events
from utils.keyboards import get_back_keyboard, get_subscription_keyboard
from utils.zodiac import get_zodiac_info
from config import config

router = Router()


class KarmaStates(StatesGroup):
    waiting_confirm = State()


def get_astro_features_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ Астро-будильник", callback_data="astro_alarm")],
        [InlineKeyboardButton(text="☿️ Ретроградный алерт", callback_data="retrograde_alert")],
        [InlineKeyboardButton(text="💰 Денежный прогноз", callback_data="money_forecast")],
        [InlineKeyboardButton(text="🔮 Кармический разбор", callback_data="karma_analysis")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_notifications_keyboard(settings: dict) -> InlineKeyboardMarkup:
    def status(val):
        return "✅" if val else "❌"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{status(settings.get('daily_horoscope'))} Ежедневный гороскоп",
            callback_data="toggle_daily_horoscope"
        )],
        [InlineKeyboardButton(
            text=f"{status(settings.get('astro_alarm'))} Астро-будильник",
            callback_data="toggle_astro_alarm"
        )],
        [InlineKeyboardButton(
            text=f"{status(settings.get('retrograde_alerts'))} Ретроградные алерты",
            callback_data="toggle_retrograde_alerts"
        )],
        [InlineKeyboardButton(
            text=f"{status(settings.get('moon_calendar'))} Лунный календарь",
            callback_data="toggle_moon_calendar"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="astro_features")]
    ])


# ==================== ГЛАВНОЕ МЕНЮ ====================

@router.callback_query(F.data == "astro_features")
async def show_astro_features(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔮 *Астро-функции*\n\n"
        "Дополнительные возможности для глубокого понимания космических влияний:",
        parse_mode="Markdown",
        reply_markup=get_astro_features_menu()
    )


# ==================== АСТРО-БУДИЛЬНИК ====================

@router.callback_query(F.data == "astro_alarm")
async def show_astro_alarm(callback: CallbackQuery):
    has_sub = await has_active_subscription(callback.from_user.id)
    
    if not has_sub:
        await callback.message.edit_text(
            "⏰ *Астро-будильник*\n\n"
            "Получай уведомления о благоприятных часах для:\n"
            "• 💰 Финансовых дел\n"
            "• 💕 Любовных встреч\n"
            "• ⚡ Важных действий\n\n"
            "Доступно с премиум-подпиской!",
            parse_mode="Markdown",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    user = await get_user(callback.from_user.id)
    zodiac = user.get('zodiac_sign', 'aries') if user else 'aries'
    zodiac_info = get_zodiac_info(zodiac)
    
    hours = get_favorable_hours(zodiac)
    
    text = f"⏰ *Астро-будильник*\n\n"
    text += f"🔮 Благоприятные часы для {zodiac_info.symbol} *{zodiac_info.name}* сегодня:\n\n"
    
    if hours["excellent"]:
        text += "⭐ *Отличные часы:*\n"
        for h, planet, emoji in hours["excellent"]:
            text += f"   {h:02d}:00 — {emoji} {planet}\n"
    
    if hours["best_for_money"]:
        text += "\n💰 *Для денежных дел:*\n"
        for h, planet, emoji in hours["best_for_money"]:
            text += f"   {h:02d}:00\n"
    
    if hours["best_for_love"]:
        text += "\n💕 *Для любви:*\n"
        for h, planet, emoji in hours["best_for_love"]:
            text += f"   {h:02d}:00\n"
    
    settings = await get_user_notifications(callback.from_user.id)
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_notifications_keyboard(settings or {})
    )


# ==================== РЕТРОГРАДНЫЙ АЛЕРТ ====================

@router.callback_query(F.data == "retrograde_alert")
async def show_retrograde_alert(callback: CallbackQuery):
    text = get_retrograde_alert_text()
    
    settings = await get_user_notifications(callback.from_user.id)
    has_sub = await has_active_subscription(callback.from_user.id)
    
    if has_sub:
        keyboard = get_notifications_keyboard(settings or {})
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Включить алерты (премиум)", callback_data="subscription")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="astro_features")]
        ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ==================== ДЕНЕЖНЫЙ ПРОГНОЗ ====================

@router.callback_query(F.data == "money_forecast")
async def show_money_forecast(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    zodiac = user.get('zodiac_sign', '') if user else ''
    
    if not zodiac:
        await callback.answer("Сначала укажи дату рождения", show_alert=True)
        return
    
    has_sub = await has_active_subscription(callback.from_user.id)
    if not has_sub:
        await callback.message.edit_text(
            "💰 *Денежный прогноз*\n\n"
            "Финансовая астрология на неделю:\n"
            "• Благоприятные дни для заработка\n"
            "• Когда лучше экономить\n"
            "• Советы по инвестициям\n\n"
            "Доступно с премиум-подпиской!",
            parse_mode="Markdown",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    zodiac_info = get_zodiac_info(zodiac)
    
    await callback.message.edit_text(
        f"💰 Составляю финансовый прогноз для {zodiac_info.symbol} *{zodiac_info.name}*...",
        parse_mode="Markdown"
    )
    
    forecast = await gigachat_service.generate_money_forecast(zodiac_info.name)
    
    text = f"💰 *Финансовый прогноз на неделю*\n\n"
    text += f"Для {zodiac_info.symbol} *{zodiac_info.name}*\n\n"
    text += forecast
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("astro_features")
    )


# ==================== КАРМИЧЕСКИЙ РАЗБОР ====================

@router.callback_query(F.data == "karma_analysis")
async def show_karma_analysis(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    
    if not user or not user.get('birth_date'):
        await callback.answer("Сначала укажи дату рождения", show_alert=True)
        return
    
    has_sub = await has_active_subscription(callback.from_user.id)
    has_service = await has_purchased_service(callback.from_user.id, "karma")
    
    if not has_sub and not has_service:
        await callback.message.edit_text(
            "🔮 *Кармический разбор*\n\n"
            "Глубокий анализ твоей кармы:\n"
            "• Прошлые жизни\n"
            "• Кармические уроки\n"
            "• Таланты из прошлого\n"
            "• Кармические долги\n"
            "• Как их отработать\n\n"
            f"💰 Стоимость: {config.KARMA_PRICE} ₽ или {config.KARMA_STARS} ⭐\n\n"
            "Или бесплатно с премиум-подпиской!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💳 Купить за {config.KARMA_PRICE} ₽", callback_data="pay_karma")],
                [InlineKeyboardButton(text=f"⭐ Купить за {config.KARMA_STARS} Stars", callback_data="stars_karma")],
                [InlineKeyboardButton(text="⭐ Оформить подписку", callback_data="subscription")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="astro_features")]
            ])
        )
        return
    
    # Используем услугу
    if not has_sub:
        await use_purchased_service(callback.from_user.id, "karma")
    
    zodiac = user.get('zodiac_sign', 'aries')
    zodiac_info = get_zodiac_info(zodiac)
    birth_date = user.get('birth_date', '')
    
    await callback.message.edit_text(
        f"🔮 Провожу кармический анализ для даты *{birth_date}*...\n\n"
        "Это может занять минуту...",
        parse_mode="Markdown"
    )
    
    analysis = await gigachat_service.generate_karma_analysis(birth_date, zodiac_info.name)
    
    text = f"🔮 *Кармический разбор*\n\n"
    text += f"Дата рождения: *{birth_date}*\n"
    text += f"Знак: {zodiac_info.symbol} *{zodiac_info.name}*\n\n"
    text += analysis
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("astro_features")
    )


# ==================== ПЕРЕКЛЮЧЕНИЕ УВЕДОМЛЕНИЙ ====================

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_notification(callback: CallbackQuery):
    has_sub = await has_active_subscription(callback.from_user.id)
    if not has_sub:
        await callback.answer("Уведомления доступны с премиум-подпиской", show_alert=True)
        return
    
    setting = callback.data.replace("toggle_", "")
    current = await get_user_notifications(callback.from_user.id)
    
    new_value = not current.get(setting, False)
    await update_notification_setting(callback.from_user.id, setting, new_value)
    
    status = "включено ✅" if new_value else "выключено ❌"
    await callback.answer(f"Уведомление {status}")
    
    # Обновляем клавиатуру
    settings = await get_user_notifications(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=get_notifications_keyboard(settings))