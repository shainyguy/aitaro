from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, PhotoSize
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_user, has_active_subscription, has_purchased_service, use_purchased_service
from services.gigachat_service import gigachat_service
from utils.keyboards import get_back_keyboard, get_subscription_keyboard
from utils.zodiac import ZODIAC_SIGNS, get_zodiac_info, get_compatibility_score

router = Router()


class CompatibilityStates(StatesGroup):
    waiting_partner_sign = State()
    waiting_photo = State()


def get_compatibility_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💕 По знакам зодиака", callback_data="compat_signs")],
        [InlineKeyboardButton(text="📸 По фото пары (разработка)", callback_data="compat_photo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_zodiac_select_keyboard() -> InlineKeyboardMarkup:
    zodiac_list = [
        ("♈", "aries"), ("♉", "taurus"), ("♊", "gemini"),
        ("♋", "cancer"), ("♌", "leo"), ("♍", "virgo"),
        ("♎", "libra"), ("♏", "scorpio"), ("♐", "sagittarius"),
        ("♑", "capricorn"), ("♒", "aquarius"), ("♓", "pisces"),
    ]
    
    buttons = []
    for i in range(0, 12, 4):
        row = [
            InlineKeyboardButton(text=z[0], callback_data=f"partner_{z[1]}")
            for z in zodiac_list[i:i+4]
        ]
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="compatibility")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "compatibility")
async def show_compatibility_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💕 *Анализ совместимости*\n\n"
        "Выбери способ анализа:",
        parse_mode="Markdown",
        reply_markup=get_compatibility_menu()
    )


@router.callback_query(F.data == "compat_signs")
async def compatibility_by_signs(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    user_zodiac = user.get('zodiac_sign', '') if user else ''
    
    if not user_zodiac:
        await callback.answer("Сначала укажи свою дату рождения в профиле", show_alert=True)
        return
    
    user_info = get_zodiac_info(user_zodiac)
    
    await callback.message.edit_text(
        f"💕 *Твой знак:* {user_info.symbol} {user_info.name}\n\n"
        "Выбери знак партнёра:",
        parse_mode="Markdown",
        reply_markup=get_zodiac_select_keyboard()
    )
    await state.set_state(CompatibilityStates.waiting_partner_sign)


@router.callback_query(F.data.startswith("partner_"), CompatibilityStates.waiting_partner_sign)
async def process_partner_sign(callback: CallbackQuery, state: FSMContext):
    partner_zodiac = callback.data.replace("partner_", "")
    
    user = await get_user(callback.from_user.id)
    user_zodiac = user.get('zodiac_sign', '')
    
    user_info = get_zodiac_info(user_zodiac)
    partner_info = get_zodiac_info(partner_zodiac)
    
    if not user_info or not partner_info:
        await callback.answer("Ошибка", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🔮 Анализирую совместимость...\n\n"
        f"{user_info.symbol} {user_info.name} + {partner_info.symbol} {partner_info.name}",
        parse_mode="Markdown"
    )
    
    # Базовая совместимость
    base_score = get_compatibility_score(user_zodiac, partner_zodiac)
    
    # Генерируем анализ
    analysis = await gigachat_service.generate_compatibility(user_info.name, partner_info.name)
    
    text = (
        f"💕 *Совместимость*\n\n"
        f"{user_info.symbol} *{user_info.name}* + {partner_info.symbol} *{partner_info.name}*\n\n"
        f"📊 *Базовая совместимость:* {base_score}%\n\n"
        f"{analysis}"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("compatibility")
    )
    
    await state.clear()


@router.callback_query(F.data == "compat_photo")
async def compatibility_by_photo(callback: CallbackQuery, state: FSMContext):
    # Проверяем подписку или покупку
    has_sub = await has_active_subscription(callback.from_user.id)
    has_service = await has_purchased_service(callback.from_user.id, "synastry_photo")
    
    if not has_sub and not has_service:
        from config import config
        await callback.message.edit_text(
            "📸 *Синастрия по фото*\n\n"
            "Эта услуга анализирует энергетику пары по фотографии.\n\n"
            f"💰 Стоимость: {config.SYNASTRY_PHOTO_PRICE} ₽ или {config.SYNASTRY_PHOTO_STARS} ⭐\n\n"
            "Или доступно бесплатно с премиум-подпиской!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💳 Купить за {config.SYNASTRY_PHOTO_PRICE} ₽", callback_data="pay_synastry_photo")],
                [InlineKeyboardButton(text=f"⭐ Купить за {config.SYNASTRY_PHOTO_STARS} Stars", callback_data="stars_synastry_photo")],
                [InlineKeyboardButton(text="⭐ Оформить подписку", callback_data="subscription")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="compatibility")]
            ])
        )
        return
    
    await callback.message.edit_text(
        "📸 *Синастрия по фото*\n\n"
        "Отправь фотографию, где вы вместе с партнёром.\n"
        "Я проанализирую вашу энергетику и совместимость.\n\n"
        "⚡ _Для лучшего результата выбери фото, где видны оба лица_",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("compatibility")
    )
    
    await state.set_state(CompatibilityStates.waiting_photo)


@router.message(CompatibilityStates.waiting_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    # Используем услугу если не подписка
    has_sub = await has_active_subscription(message.from_user.id)
    if not has_sub:
        await use_purchased_service(message.from_user.id, "synastry_photo")
    
    await message.answer("🔮 Анализирую энергетику пары на фото...")
    
    # Генерируем анализ (без реального анализа фото, используем AI)
    analysis = await gigachat_service.analyze_photo_synastry(
        "Пара на совместном фото. Анализирую их энергетику и потенциал отношений."
    )
    
    text = (
        "📸 *Синастрия по фото*\n\n"
        f"{analysis}\n\n"
        "_Анализ основан на энергетическом считывании_"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("compatibility")
    )
    
    await state.clear()


@router.message(CompatibilityStates.waiting_photo)
async def wrong_photo_format(message: Message):
    await message.answer(
        "❌ Пожалуйста, отправь фотографию.\n"
        "Или нажми «Назад» для отмены.",
        reply_markup=get_back_keyboard("compatibility")

    )
