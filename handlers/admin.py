from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from datetime import datetime

from database import (
    is_admin, add_admin, remove_admin, get_all_admins,
    get_stats, get_users_for_broadcast, create_broadcast,
    update_broadcast_status, get_broadcast_history,
    create_promo_code, get_promo_codes, deactivate_promo_code,
    search_users, get_user_details, ban_user, unban_user,
    give_subscription, get_setting, set_setting, use_promo_code
)
from config import config

router = Router()

# ID главного админа (ваш Telegram ID)
SUPER_ADMIN_ID = int(config.SUPER_ADMIN_ID) if hasattr(config, 'SUPER_ADMIN_ID') else 0


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_broadcast_photo = State()
    waiting_promo_code = State()
    waiting_promo_discount = State()
    waiting_promo_days = State()
    waiting_user_search = State()
    waiting_user_days = State()
    waiting_new_admin = State()


# ==================== ПРОВЕРКА ДОСТУПА ====================

async def check_admin(user_id: int) -> bool:
    """Проверка прав админа"""
    if user_id == SUPER_ADMIN_ID:
        return True
    return await is_admin(user_id)


# ==================== ГЛАВНОЕ МЕНЮ ====================

def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📜 История", callback_data="admin_broadcast_history")
        ],
        [
            InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_promos"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="👑 Админы", callback_data="admin_admins"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда входа в админку"""
    if not await check_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer(
        "🎛️ *Панель администратора*\n\n"
        "Выберите раздел:",
        parse_mode="Markdown",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "admin_menu")
async def show_admin_menu(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎛️ *Панель администратора*\n\n"
        "Выберите раздел:",
        parse_mode="Markdown",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "admin_close")
async def close_admin(callback: CallbackQuery):
    await callback.message.delete()


# ==================== СТАТИСТИКА ====================

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    stats = await get_stats()
    
    text = f"""
📊 *Статистика бота*

👥 *Пользователи:*
├ Всего: *{stats['total_users']}*
├ За сегодня: *+{stats['today_users']}*
├ За неделю: *+{stats['week_users']}*
├ Активных (24ч): *{stats['active_24h']}*
└ Премиум: *{stats['premium_users']}* ({stats['conversion_rate']}%)

💰 *Доход:*
├ Сегодня: *{stats['today_revenue']:.0f} ₽*
├ За месяц: *{stats['month_revenue']:.0f} ₽*
└ Всего: *{stats['total_revenue']:.0f} ₽*

🎴 *Активность:*
└ Раскладов сделано: *{stats['total_readings']}*

📈 *Конверсия:* {stats['conversion_rate']}%
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ==================== РАССЫЛКА ====================

def get_broadcast_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Всем пользователям", callback_data="broadcast_all")],
        [InlineKeyboardButton(text="👑 Только премиум", callback_data="broadcast_premium")],
        [InlineKeyboardButton(text="🆓 Только бесплатным", callback_data="broadcast_free")],
        [InlineKeyboardButton(text="😴 Неактивным (7+ дней)", callback_data="broadcast_inactive")],
        [InlineKeyboardButton(text="🆕 Новым (24ч)", callback_data="broadcast_new")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
    ])


@router.callback_query(F.data == "admin_broadcast")
async def show_broadcast_menu(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "📨 *Рассылка*\n\n"
        "Выберите целевую аудиторию:",
        parse_mode="Markdown",
        reply_markup=get_broadcast_menu()
    )


@router.callback_query(F.data.startswith("broadcast_"))
async def select_broadcast_audience(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    
    audience = callback.data.replace("broadcast_", "")
    
    # Считаем пользователей
    from database import get_users_count_by_audience
    count = await get_users_count_by_audience(audience)
    
    audience_names = {
        "all": "всем пользователям",
        "premium": "премиум пользователям",
        "free": "бесплатным пользователям",
        "inactive": "неактивным пользователям",
        "new": "новым пользователям"
    }
    
    await state.update_data(broadcast_audience=audience, broadcast_count=count)
    
    await callback.message.edit_text(
        f"📨 *Рассылка {audience_names.get(audience, audience)}*\n\n"
        f"👥 Получателей: *{count}*\n\n"
        "Отправьте текст сообщения для рассылки.\n"
        "Можно использовать *Markdown* разметку.\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.waiting_broadcast_text)


@router.message(AdminStates.waiting_broadcast_text)
async def receive_broadcast_text(message: Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена", reply_markup=get_admin_menu())
        return
    
    data = await state.get_data()
    audience = data.get('broadcast_audience', 'all')
    count = data.get('broadcast_count', 0)
    
    await state.update_data(broadcast_text=message.text)
    
    # Предпросмотр
    preview = f"""
📨 *Предпросмотр рассылки*

👥 Получателей: *{count}*
📝 Аудитория: *{audience}*

━━━━━━━━━━━━━━━━━
{message.text}
━━━━━━━━━━━━━━━━━

Хотите добавить фото?
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📷 Добавить фото", callback_data="broadcast_add_photo"),
            InlineKeyboardButton(text="▶️ Отправить", callback_data="broadcast_send")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")]
    ])
    
    await message.answer(preview, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "broadcast_add_photo")
async def request_broadcast_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📷 Отправьте фото для рассылки\n\n"
        "Для отмены отправьте /cancel"
    )
    await state.set_state(AdminStates.waiting_broadcast_photo)


@router.message(AdminStates.waiting_broadcast_photo, F.photo)
async def receive_broadcast_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(broadcast_photo=photo_id)
    
    data = await state.get_data()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Отправить", callback_data="broadcast_send")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")]
    ])
    
    await message.answer_photo(
        photo=photo_id,
        caption=f"📷 Фото добавлено!\n\n{data.get('broadcast_text', '')}\n\n"
                f"👥 Получателей: {data.get('broadcast_count', 0)}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(None)


@router.callback_query(F.data == "broadcast_send")
async def send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    audience = data.get('broadcast_audience', 'all')
    text = data.get('broadcast_text', '')
    photo = data.get('broadcast_photo')
    
    # Создаём запись о рассылке
    broadcast_id = await create_broadcast(
        admin_id=callback.from_user.id,
        message_text=text,
        target_audience=audience,
        message_photo=photo
    )
    
    await callback.message.edit_text("⏳ Рассылка запущена...")
    
    # Получаем пользователей
    users = await get_users_for_broadcast(audience)
    
    await update_broadcast_status(broadcast_id, 'started')
    
    sent = 0
    failed = 0
    
    for user_id in users:
        try:
            if photo:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=text,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="Markdown"
                )
            sent += 1
        except Exception as e:
            failed += 1
        
        # Пауза чтобы не превысить лимиты
        if sent % 30 == 0:
            await asyncio.sleep(1)
    
    await update_broadcast_status(broadcast_id, 'finished', sent, failed)
    
    await callback.message.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"📨 Отправлено: *{sent}*\n"
        f"❌ Ошибок: *{failed}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="admin_menu")]
        ])
    )
    
    await state.clear()


@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="admin_menu")]
        ])
    )


@router.callback_query(F.data == "admin_broadcast_history")
async def show_broadcast_history(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    history = await get_broadcast_history(10)
    
    if not history:
        text = "📜 История рассылок пуста"
    else:
        text = "📜 *Последние рассылки:*\n\n"
        for b in history:
            status_emoji = "✅" if b['status'] == 'finished' else "⏳" if b['status'] == 'started' else "📝"
            date = datetime.fromisoformat(b['created_at']).strftime('%d.%m %H:%M')
            text += f"{status_emoji} {date} | 👥 {b['sent_count']}/{b['total_users']} | {b['target_audience']}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ==================== ПРОМОКОДЫ ====================

@router.callback_query(F.data == "admin_promos")
async def show_promos(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    promos = await get_promo_codes()
    
    text = "🎁 *Промокоды*\n\n"
    
    if promos:
        for p in promos:
            status = "✅" if p['is_active'] else "❌"
            text += f"{status} `{p['code']}` "
            if p['discount_percent'] > 0:
                text += f"(-{p['discount_percent']}%) "
            if p['bonus_days'] > 0:
                text += f"(+{p['bonus_days']} дн.) "
            text += f"[{p['used_count']}/{p['max_uses']}]\n"
    else:
        text += "_Нет активных промокодов_"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="promo_create")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "promo_create")
async def start_create_promo(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "🎁 *Создание промокода*\n\n"
        "Введите код (латиница, цифры):\n"
        "Например: NEWYEAR2025",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_promo_code)


@router.message(AdminStates.waiting_promo_code)
async def receive_promo_code(message: Message, state: FSMContext):
    code = message.text.upper().strip()
    
    if not code.isalnum():
        await message.answer("❌ Код должен содержать только буквы и цифры")
        return
    
    await state.update_data(promo_code=code)
    
    await message.answer(
        f"Код: *{code}*\n\n"
        "Введите скидку в процентах (0-100):\n"
        "Или 0 если без скидки",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_promo_discount)


@router.message(AdminStates.waiting_promo_discount)
async def receive_promo_discount(message: Message, state: FSMContext):
    try:
        discount = int(message.text)
        if not 0 <= discount <= 100:
            raise ValueError
    except:
        await message.answer("❌ Введите число от 0 до 100")
        return
    
    await state.update_data(promo_discount=discount)
    
    await message.answer(
        "Введите количество бонусных дней подписки:\n"
        "Или 0 если без бонуса"
    )
    await state.set_state(AdminStates.waiting_promo_days)


@router.message(AdminStates.waiting_promo_days)
async def receive_promo_days(message: Message, state: FSMContext):
    try:
        days = int(message.text)
        if days < 0:
            raise ValueError
    except:
        await message.answer("❌ Введите положительное число")
        return
    
    data = await state.get_data()
    code = data['promo_code']
    discount = data['promo_discount']
    
    success = await create_promo_code(
        code=code,
        discount_percent=discount,
        bonus_days=days,
        max_uses=1000,
        valid_days=30
    )
    
    if success:
        text = f"✅ Промокод создан!\n\n"
        text += f"🎁 Код: `{code}`\n"
        if discount > 0:
            text += f"💸 Скидка: {discount}%\n"
        if days > 0:
            text += f"📅 Бонус: +{days} дней\n"
        text += f"⏰ Действует 30 дней"
    else:
        text = "❌ Ошибка создания промокода"
    
    await state.clear()
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К промокодам", callback_data="admin_promos")]
        ])
    )


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@router.callback_query(F.data == "admin_users")
async def show_users_menu(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    
    await callback.message.edit_text(
        "👥 *Управление пользователями*\n\n"
        "Введите ID или @username для поиска:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
        ])
    )
    await state.set_state(AdminStates.waiting_user_search)


@router.message(AdminStates.waiting_user_search)
async def search_user(message: Message, state: FSMContext):
    query = message.text.strip().replace("@", "")
    
    users = await search_users(query)
    
    if not users:
        await message.answer(
            "❌ Пользователи не найдены",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Искать снова", callback_data="admin_users")],
                [InlineKeyboardButton(text="◀️ В меню", callback_data="admin_menu")]
            ])
        )
        await state.clear()
        return
    
    text = f"👥 *Найдено: {len(users)}*\n\n"
    
    buttons = []
    for u in users[:10]:
        name = u.get('first_name') or u.get('username') or 'Без имени'
        is_premium = "👑" if u.get('subscription_until') else ""
        text += f"{is_premium} {name} | ID: `{u['user_id']}`\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"{is_premium} {name} ({u['user_id']})",
                callback_data=f"user_view_{u['user_id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ В меню", callback_data="admin_menu")])
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.clear()


@router.callback_query(F.data.startswith("user_view_"))
async def view_user(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("user_view_", ""))
    user = await get_user_details(user_id)
    
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    
    is_premium = "✅ Активна" if user.get('subscription_until') else "❌ Нет"
    
    text = f"""
👤 *Пользователь*

🆔 ID: `{user['user_id']}`
👤 Имя: {user.get('first_name', 'Нет')}
📧 Username: @{user.get('username', 'Нет')}
♈ Знак: {user.get('zodiac_sign', 'Не указан')}

📅 Регистрация: {user.get('created_at', '')[:10]}
🎴 Раскладов: {user.get('free_readings_used', 0)}
👑 Подписка: {is_premium}
👥 Рефералов: {user.get('referrals_count', 0)}

💳 *Последние платежи:*
"""
    
    payments = user.get('payments', [])
    if payments:
        for p in payments[:5]:
            status = "✅" if p['status'] == 'succeeded' else "⏳"
            text += f"{status} {p['amount']} ₽ | {p['created_at'][:10]}\n"
    else:
        text += "_Нет платежей_\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 Выдать подписку", callback_data=f"user_give_{user_id}"),
            InlineKeyboardButton(text="💬 Написать", callback_data=f"user_msg_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data=f"user_ban_{user_id}"),
            InlineKeyboardButton(text="✅ Разбан", callback_data=f"user_unban_{user_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data.startswith("user_give_"))
async def give_user_subscription(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("user_give_", ""))
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        "🎁 *Выдача подписки*\n\n"
        "Введите количество дней:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_user_days)


@router.message(AdminStates.waiting_user_days)
async def process_give_days(message: Message, state: FSMContext, bot: Bot):
    try:
        days = int(message.text)
        if days < 1:
            raise ValueError
    except:
        await message.answer("❌ Введите положительное число")
        return
    
    data = await state.get_data()
    user_id = data['target_user_id']
    
    new_until = await give_subscription(user_id, days)
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"🎁 *Подарок от администрации!*\n\n"
            f"Тебе начислено *{days} дней* премиум подписки!\n"
            f"Действует до: {new_until.strftime('%d.%m.%Y')}",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await state.clear()
    
    await message.answer(
        f"✅ Пользователю {user_id} выдано {days} дней подписки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="admin_menu")]
        ])
    )


@router.callback_query(F.data.startswith("user_ban_"))
async def ban_user_handler(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("user_ban_", ""))
    await ban_user(user_id)
    await callback.answer(f"🚫 Пользователь {user_id} заблокирован", show_alert=True)


@router.callback_query(F.data.startswith("user_unban_"))
async def unban_user_handler(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    user_id = int(callback.data.replace("user_unban_", ""))
    await unban_user(user_id)
    await callback.answer(f"✅ Пользователь {user_id} разблокирован", show_alert=True)


# ==================== УПРАВЛЕНИЕ АДМИНАМИ ====================

@router.callback_query(F.data == "admin_admins")
async def show_admins(callback: CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN_ID:
        await callback.answer("⛔ Только главный админ", show_alert=True)
        return
    
    admins = await get_all_admins()
    
    text = "👑 *Администраторы*\n\n"
    for admin_id in admins:
        is_super = "⭐" if admin_id == SUPER_ADMIN_ID else ""
        text += f"{is_super} `{admin_id}`\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_new")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "admin_add_new")
async def start_add_admin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != SUPER_ADMIN_ID:
        return
    
    await callback.message.edit_text(
        "➕ *Добавление админа*\n\n"
        "Отправьте ID нового администратора:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_new_admin)


@router.message(AdminStates.waiting_new_admin)
async def process_new_admin(message: Message, state: FSMContext):
    try:
        new_admin_id = int(message.text)
    except:
        await message.answer("❌ Введите корректный ID")
        return
    
    success = await add_admin(new_admin_id, message.from_user.id)
    
    if success:
        text = f"✅ Админ {new_admin_id} добавлен"
    else:
        text = "❌ Ошибка добавления"
    
    await state.clear()
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К админам", callback_data="admin_admins")]
        ])
    )


# ==================== НАСТРОЙКИ ====================

@router.callback_query(F.data == "admin_settings")
async def show_settings(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    
    text = """
⚙️ *Настройки бота*

Используйте команды:
• /set_price 490 — цена подписки
• /set_trial 3 — пробный период (дней)
• /set_free 1 — бесплатных раскладов
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ==================== ЭКСПОРТ ====================

@router.message(Command("export_users"))
async def export_users(message: Message):
    if not await check_admin(message.from_user.id):
        return
    
    # Простой экспорт
    from database import get_users_for_broadcast
    users = await get_users_for_broadcast('all')
    
    text = f"📊 Всего пользователей: {len(users)}\n\n"
    text += "ID:\n" + "\n".join(str(u) for u in users[:100])
    
    if len(users) > 100:
        text += f"\n... и ещё {len(users) - 100}"
    
    await message.answer(text)
