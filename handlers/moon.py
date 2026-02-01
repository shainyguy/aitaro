from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from services.moon_calendar import get_moon_day_info, get_beauty_calendar_text
from utils.keyboards import get_back_keyboard

router = Router()


def get_moon_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌙 Лунный день сегодня", callback_data="moon_today")],
        [InlineKeyboardButton(text="💄 Календарь красоты", callback_data="moon_beauty")],
        [InlineKeyboardButton(text="📅 Луна на 7 дней", callback_data="moon_week")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


@router.callback_query(F.data == "moon_day")
async def show_moon_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌙 *Лунный календарь*\n\n"
        "Выбери, что тебя интересует:",
        parse_mode="Markdown",
        reply_markup=get_moon_menu()
    )


@router.callback_query(F.data == "moon_today")
async def show_moon_today(callback: CallbackQuery):
    moon = get_moon_day_info()
    
    energy_bar = "🔥" * moon.recommendations.get("energy", 3) + "⚪" * (5 - moon.recommendations.get("energy", 3))
    
    text = f"""
🌙 *Лунный день: {moon.day}*

{moon.phase}
{moon.sign}
{'🌒 Луна растущая' if moon.is_growing else '🌘 Луна убывающая'}
💡 Освещённость: {moon.illumination}%

⚡ *Энергия дня:* {energy_bar}

✅ *Благоприятно:*
{chr(10).join('• ' + item for item in moon.recommendations.get('good', []))}

❌ *Не рекомендуется:*
{chr(10).join('• ' + item for item in moon.recommendations.get('bad', []))}
"""
    
    if moon.warnings:
        text += f"\n\n⚠️ *Предупреждения:*\n"
        text += "\n".join(moon.warnings)
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_moon_menu()
    )


@router.callback_query(F.data == "moon_beauty")
async def show_beauty_calendar(callback: CallbackQuery):
    text = get_beauty_calendar_text()
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_moon_menu()
    )


@router.callback_query(F.data == "moon_week")
async def show_moon_week(callback: CallbackQuery):
    text = "📅 *Луна на 7 дней*\n\n"
    
    for i in range(7):
        date = datetime.now() + timedelta(days=i)
        moon = get_moon_day_info(date)
        
        day_name = "Сегодня" if i == 0 else ("Завтра" if i == 1 else date.strftime("%d.%m"))
        energy = "🔥" * moon.recommendations.get("energy", 3)
        
        text += f"*{day_name}* — {moon.phase_emoji} {moon.day} л.д. {moon.sign_emoji}\n"
        text += f"   {energy}\n"
    
    text += "\n_Нажми «Лунный день сегодня» для подробностей_"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_moon_menu()
    )