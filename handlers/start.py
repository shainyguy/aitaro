from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from database import (
    create_user, update_user_birth_data, get_user,
    get_user_by_referral_code, add_referral,
    get_referral_stats, get_subscription_end
)
from utils.keyboards import get_main_menu, get_back_keyboard
from utils.zodiac import get_zodiac_by_date, get_zodiac_info

router = Router()


class RegistrationStates(StatesGroup):
    waiting_birth_date = State()
    waiting_birth_time = State()
    waiting_birth_place = State()


WELCOME_TEXT = """
🔮 *Добро пожаловать в Astro AI!*

Я — твой личный таролог и астролог, доступный 24/7.

✨ *Что я умею:*
• 🎴 Расклады Таро
• ⭐ Персональные гороскопы
• 💕 Анализ совместимости
• 🌙 Лунный календарь красоты
• 💰 Денежный прогноз
• 🔮 Кармический разбор
• ⏰ Астро-будильник
• ☿️ Ретроградные алерты

*Введи дату рождения в формате ДД.ММ.ГГГГ*
"""


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_referral(message: Message, command: CommandObject, state: FSMContext):
    args = command.args
    referrer_id = None
    referrer_name = None
    
    if args and args.startswith("ref_"):
        referral_code = args.replace("ref_", "")
        referrer = await get_user_by_referral_code(referral_code)
        
        if referrer and referrer['user_id'] != message.from_user.id:
            referrer_id = referrer['user_id']
            referrer_name = referrer.get('first_name') or 'Друг'
    
    existing_user = await get_user(message.from_user.id)
    
    if existing_user and existing_user.get('birth_date'):
        await message.answer(
            f"🔮 С возвращением, *{message.from_user.first_name}*!",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
        return
    
    if not existing_user:
        await create_user(
            message.from_user.id, message.from_user.username,
            message.from_user.first_name, referrer_id
        )
        if referrer_id:
            await add_referral(referrer_id, message.from_user.id)
    
    welcome = WELCOME_TEXT
    if referrer_name:
        welcome = f"🎁 Тебя пригласил *{referrer_name}*!\n\n" + welcome
    
    await message.answer(welcome, parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_birth_date)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    existing_user = await get_user(message.from_user.id)
    
    if existing_user and existing_user.get('birth_date'):
        await message.answer(
            f"🔮 С возвращением, *{message.from_user.first_name}*!",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
        return
    
    if not existing_user:
        await create_user(
            message.from_user.id, message.from_user.username,
            message.from_user.first_name
        )
    
    await message.answer(WELCOME_TEXT, parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_birth_date)


@router.message(RegistrationStates.waiting_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    birth_date = message.text.strip()
    zodiac = get_zodiac_by_date(birth_date)
    
    if not zodiac:
        await message.answer("❌ Неверный формат. Введи дату как *ДД.ММ.ГГГГ*", parse_mode="Markdown")
        return
    
    await state.update_data(birth_date=birth_date, zodiac=zodiac)
    zodiac_info = get_zodiac_info(zodiac)
    
    await message.answer(
        f"✨ Ты — *{zodiac_info.symbol} {zodiac_info.name}*\n\n"
        "Введи время рождения (например: 14:30) или нажми «Пропустить»:",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard("skip_time")
    )
    await state.set_state(RegistrationStates.waiting_birth_time)


@router.callback_query(F.data == "skip_time")
async def skip_time(callback: CallbackQuery, state: FSMContext):
    await state.update_data(birth_time="Неизвестно")
    await callback.message.edit_text(
        "📍 Укажи город рождения или нажми «Пропустить»:",
        reply_markup=get_back_keyboard("skip_place")
    )
    await state.set_state(RegistrationStates.waiting_birth_place)


@router.message(RegistrationStates.waiting_birth_time)
async def process_birth_time(message: Message, state: FSMContext):
    await state.update_data(birth_time=message.text.strip())
    await message.answer(
        "📍 Укажи город рождения:",
        reply_markup=get_back_keyboard("skip_place")
    )
    await state.set_state(RegistrationStates.waiting_birth_place)


@router.callback_query(F.data == "skip_place")
async def skip_place(callback: CallbackQuery, state: FSMContext):
    await finish_registration(callback, state, "Не указано")


@router.message(RegistrationStates.waiting_birth_place)
async def process_birth_place(message: Message, state: FSMContext):
    await finish_registration(message, state, message.text.strip())


async def finish_registration(event, state: FSMContext, birth_place: str):
    data = await state.get_data()
    user_id = event.from_user.id
    zodiac_info = get_zodiac_info(data['zodiac'])
    
    await update_user_birth_data(
        user_id, data['birth_date'], data.get('birth_time', 'Неизвестно'),
        birth_place, data['zodiac']
    )
    
    text = f"""
🌟 *Регистрация завершена!*

{zodiac_info.symbol} Ты — *{zodiac_info.name}*
🌍 Стихия: *{zodiac_info.element}*
🪐 Планета: *{zodiac_info.ruling_planet}*

*Твой первый расклад — бесплатно* 🎁
"""
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu())
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())
    
    await state.clear()


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔮 *Главное меню*",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Профиль не найден", show_alert=True)
        return
    
    zodiac_info = get_zodiac_info(user.get('zodiac_sign', 'aries'))
    
    sub_status = "❌ Не активна"
    sub_end = await get_subscription_end(callback.from_user.id)
    if sub_end and sub_end > datetime.now():
        sub_status = f"✅ До {sub_end.strftime('%d.%m.%Y')}"
    
    ref_stats = await get_referral_stats(callback.from_user.id)
    
    text = f"""
👤 *Профиль*

{zodiac_info.symbol if zodiac_info else '⭐'} *Знак:* {zodiac_info.name if zodiac_info else 'Не указан'}
📅 *Дата рождения:* {user.get('birth_date', 'Не указана')}
⏰ *Время:* {user.get('birth_time', 'Не указано')}
📍 *Место:* {user.get('birth_place', 'Не указано')}

🔮 *Раскладов:* {user.get('free_readings_used', 0)}
⭐ *Подписка:* {sub_status}

👥 *Рефералов:* {ref_stats['total_referrals']}
🎁 *Бонус дней:* {ref_stats['total_bonus_days']}
"""
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_keyboard())