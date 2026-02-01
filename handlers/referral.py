from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime

from database import get_user, get_referral_stats, get_referrals_list
from config import config

router = Router()


def get_referral_link(user_id: int, referral_code: str) -> str:
    """Генерация реферальной ссылки"""
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{referral_code}"


def get_referral_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Клавиатура реферальной программы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Поделиться ссылкой",
            switch_inline_query=f"🔮 Открой мир Таро и астрологии! {referral_link}"
        )],
        [InlineKeyboardButton(text="📋 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="subscription")]
    ])


REFERRAL_INFO = """
👥 *Реферальная программа*

🎁 Приглашай друзей и получай *+{bonus_days} день* подписки за каждого!

*Как это работает:*
1️⃣ Поделись своей ссылкой с другом
2️⃣ Друг регистрируется по ссылке
3️⃣ Когда друг оформит подписку — ты получишь бонус!

📊 *Твоя статистика:*
• Приглашено: *{total}* чел.
• Оформили подписку: *{activated}* чел.
• Получено дней: *{bonus_days_earned}*

🔗 *Твоя ссылка:*
`{referral_link}`

👆 _Нажми на ссылку, чтобы скопировать_
"""


@router.callback_query(F.data == "referral_program")
async def show_referral_program(callback: CallbackQuery):
    """Показать реферальную программу"""
    user = await get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка: профиль не найден", show_alert=True)
        return
    
    stats = await get_referral_stats(callback.from_user.id)
    referral_link = get_referral_link(callback.from_user.id, user['referral_code'])
    
    text = REFERRAL_INFO.format(
        bonus_days=config.REFERRAL_BONUS_DAYS,
        total=stats['total_referrals'],
        activated=stats['activated_referrals'],
        bonus_days_earned=stats['total_bonus_days'],
        referral_link=referral_link
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_referral_keyboard(referral_link)
    )


@router.callback_query(F.data == "my_referrals")
async def show_my_referrals(callback: CallbackQuery):
    """Показать список рефералов"""
    referrals = await get_referrals_list(callback.from_user.id, limit=15)
    
    if not referrals:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="referral_program")]
        ])
        await callback.message.edit_text(
            "👥 *Мои рефералы*\n\n"
            "У тебя пока нет рефералов.\n\n"
            "Поделись своей ссылкой с друзьями!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return
    
    text = "👥 *Мои рефералы*\n\n"
    
    for ref in referrals:
        name = ref.get('first_name') or ref.get('username') or 'Пользователь'
        status = "✅" if ref['bonus_applied'] else "⏳"
        date = datetime.fromisoformat(ref['created_at']).strftime('%d.%m.%Y')
        text += f"{status} *{name}* — {date}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="referral_program")]
    ])
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(Command("referral"))
async def cmd_referral(message: Message):
    """Команда /referral"""
    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer("Сначала зарегистрируйся: /start")
        return
    
    stats = await get_referral_stats(message.from_user.id)
    referral_link = get_referral_link(message.from_user.id, user['referral_code'])
    
    text = REFERRAL_INFO.format(
        bonus_days=config.REFERRAL_BONUS_DAYS,
        total=stats['total_referrals'],
        activated=stats['activated_referrals'],
        bonus_days_earned=stats['total_bonus_days'],
        referral_link=referral_link
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_referral_keyboard(referral_link)
    )