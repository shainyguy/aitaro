from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, LabeledPrice,
    PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from datetime import datetime
import uuid

from database import (
    get_user, extend_subscription, create_payment, update_payment_status,
    add_purchased_service, get_subscription_end, apply_referral_bonus
)
from services.yookassa_service import (
    yookassa_service, PaymentType, get_payment_description, get_payment_amount
)
from utils.keyboards import get_main_menu, get_back_keyboard
from config import config

router = Router()


# ==================== ЦЕНЫ ====================

SERVICES = {
    "subscription": {
        "title": "⭐ Премиум подписка",
        "description": "Безлимитный доступ на 30 дней",
        "price_rub": config.SUBSCRIPTION_PRICE,
        "price_stars": config.SUBSCRIPTION_STARS,
        "type": PaymentType.SUBSCRIPTION
    },
    "compatibility": {
        "title": "💕 Анализ совместимости",
        "description": "Детальный анализ пары",
        "price_rub": config.COMPATIBILITY_PRICE,
        "price_stars": config.COMPATIBILITY_STARS,
        "type": PaymentType.COMPATIBILITY
    },
    "natal_chart": {
        "title": "📊 Натальная карта",
        "description": "Полный разбор натальной карты",
        "price_rub": config.NATAL_CHART_PRICE,
        "price_stars": config.NATAL_CHART_STARS,
        "type": PaymentType.NATAL_CHART
    },
    "karma": {
        "title": "🔮 Кармический разбор",
        "description": "Анализ прошлых жизней и кармы",
        "price_rub": config.KARMA_PRICE,
        "price_stars": config.KARMA_STARS,
        "type": None
    },
    "synastry_photo": {
        "title": "📸 Синастрия по фото",
        "description": "Анализ совместимости по фотографии",
        "price_rub": config.SYNASTRY_PHOTO_PRICE,
        "price_stars": config.SYNASTRY_PHOTO_STARS,
        "type": None
    }
}


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Подписка — {config.SUBSCRIPTION_PRICE} ₽",
            callback_data="pay_subscription"
        )],
        [InlineKeyboardButton(
            text=f"⭐ Подписка — {config.SUBSCRIPTION_STARS} Stars",
            callback_data="stars_subscription"
        )],
        [InlineKeyboardButton(
            text="👥 Пригласить друга (+1 день)",
            callback_data="referral_program"
        )],
        [InlineKeyboardButton(text="📋 Все услуги", callback_data="all_services")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_all_services_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, service in SERVICES.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{service['title']} — {service['price_rub']}₽ / {service['price_stars']}⭐",
                callback_data=f"service_{key}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_method_keyboard(service_key: str) -> InlineKeyboardMarkup:
    service = SERVICES.get(service_key, {})
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 ЮKassa — {service.get('price_rub', 0)} ₽",
            callback_data=f"pay_{service_key}"
        )],
        [InlineKeyboardButton(
            text=f"⭐ Telegram Stars — {service.get('price_stars', 0)}",
            callback_data=f"stars_{service_key}"
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="all_services")]
    ])


# ==================== МЕНЮ ====================

@router.callback_query(F.data == "subscription")
async def show_subscription(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    
    status_text = ""
    if user:
        sub_end = await get_subscription_end(callback.from_user.id)
        if sub_end and sub_end > datetime.now():
            status_text = f"\n\n✅ *Подписка активна до:* {sub_end.strftime('%d.%m.%Y')}"
        else:
            status_text = "\n\n🎁 *У тебя есть 1 бесплатный расклад*"
    
    text = f"""
⭐ *Премиум подписка Astro AI*

✨ *Что входит:*
• 🎴 Безлимитные расклады Таро
• ⭐ Ежедневный гороскоп
• 💕 Анализ совместимости
• 🌙 Лунный календарь
• 💰 Денежный прогноз
• 🔮 Кармический разбор
• ⏰ Астро-будильник
• ☿️ Ретроградные алерты

💰 *Стоимость:* {config.SUBSCRIPTION_PRICE} ₽/мес или {config.SUBSCRIPTION_STARS} ⭐

🎁 Приглашай друзей — получай +1 день!{status_text}
"""
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_subscription_keyboard()
    )


@router.callback_query(F.data == "all_services")
async def show_all_services(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 *Все услуги*\n\n"
        "Выбери услугу для покупки:",
        parse_mode="Markdown",
        reply_markup=get_all_services_keyboard()
    )


@router.callback_query(F.data.startswith("service_"))
async def show_service_details(callback: CallbackQuery):
    service_key = callback.data.replace("service_", "")
    service = SERVICES.get(service_key)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{service['title']}\n\n"
        f"_{service['description']}_\n\n"
        "Выбери способ оплаты:",
        parse_mode="Markdown",
        reply_markup=get_payment_method_keyboard(service_key)
    )


# ==================== ОПЛАТА ЧЕРЕЗ ЮKASSA ====================

@router.callback_query(F.data.startswith("pay_"))
async def process_yookassa_payment(callback: CallbackQuery):
    service_key = callback.data.replace("pay_", "")
    service = SERVICES.get(service_key)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"💳 *Создаю платёж...*\n\n"
        f"{service['title']}\n"
        f"Сумма: {service['price_rub']} ₽",
        parse_mode="Markdown"
    )
    
    payment_type = service.get("type") or PaymentType.SUBSCRIPTION
    
    payment = await yookassa_service.create_payment(
        user_id=callback.from_user.id,
        payment_type=payment_type,
        amount=service["price_rub"],
        description=service["description"]
    )
    
    if not payment:
        await callback.message.edit_text(
            "❌ *Ошибка создания платежа*\n\nПопробуйте позже.",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard("subscription")
        )
        return
    
    await create_payment(
        user_id=callback.from_user.id,
        payment_id=payment.payment_id,
        amount=service["price_rub"],
        payment_type=service_key,
        description=service["description"],
        payment_method="yookassa"
    )
    
    await callback.message.edit_text(
        f"{service['title']}\n\n"
        f"💰 Сумма: *{service['price_rub']} ₽*\n\n"
        "Нажми «Оплатить» для перехода к оплате.\n"
        "После оплаты нажми «Я оплатил».",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment.confirmation_url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment:{payment.payment_id}:{service_key}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="subscription")]
        ])
    )


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    payment_id = parts[1]
    service_key = parts[2] if len(parts) > 2 else "subscription"
    
    await callback.answer("⏳ Проверяю платёж...")
    
    payment = await yookassa_service.get_payment(payment_id)
    
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    
    if payment.status == "succeeded" and payment.paid:
        await process_successful_payment(callback, bot, payment_id, service_key)
    elif payment.status == "pending":
        await callback.answer("⏳ Платёж ещё обрабатывается. Подождите.", show_alert=True)
    else:
        await callback.message.edit_text(
            f"❌ *Статус платежа: {payment.status}*",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard("subscription")
        )


# ==================== ОПЛАТА ЧЕРЕЗ TELEGRAM STARS ====================

@router.callback_query(F.data.startswith("stars_"))
async def process_stars_payment(callback: CallbackQuery):
    service_key = callback.data.replace("stars_", "")
    service = SERVICES.get(service_key)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    # Отправляем invoice для Telegram Stars
    await callback.message.answer_invoice(
        title=service["title"],
        description=service["description"],
        payload=f"stars_{service_key}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=service["title"], amount=service["price_stars"])],
    )
    
    await callback.message.delete()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout: PreCheckoutQuery):
    """Подтверждение платежа Stars"""
    await pre_checkout.answer(ok=True)


@router.message(F.successful_payment)
async def process_stars_success(message: Message, bot: Bot):
    """Успешная оплата Stars"""
    payload = message.successful_payment.invoice_payload
    service_key = payload.replace("stars_", "")
    
    payment_id = f"stars_{uuid.uuid4().hex[:8]}"
    
    await create_payment(
        user_id=message.from_user.id,
        payment_id=payment_id,
        amount=message.successful_payment.total_amount,
        payment_type=service_key,
        payment_method="telegram_stars",
        currency="XTR"
    )
    
    await update_payment_status(payment_id, "succeeded")
    
    # Активируем услугу
    if service_key == "subscription":
        new_until = await extend_subscription(message.from_user.id, 30)
        
        # Бонус рефереру
        user = await get_user(message.from_user.id)
        if user and user.get('referrer_id'):
            bonus_applied = await apply_referral_bonus(
                user['referrer_id'], message.from_user.id, config.REFERRAL_BONUS_DAYS
            )
            if bonus_applied:
                try:
                    await bot.send_message(
                        user['referrer_id'],
                        f"🎁 *Бонус!* Твой друг оформил подписку. Тебе +{config.REFERRAL_BONUS_DAYS} день!",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        await message.answer(
            f"🎉 *Подписка активирована!*\n\n"
            f"Действует до: *{new_until.strftime('%d.%m.%Y')}*\n\n"
            "Наслаждайся всеми возможностями! ✨",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await add_purchased_service(message.from_user.id, service_key, payment_id)
        
        await message.answer(
            f"🎉 *Оплата прошла успешно!*\n\n"
            f"Услуга «{SERVICES[service_key]['title']}» доступна.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )


# ==================== ОБРАБОТКА УСПЕШНОГО ПЛАТЕЖА ====================

async def process_successful_payment(callback: CallbackQuery, bot: Bot, payment_id: str, service_key: str):
    await update_payment_status(payment_id, "succeeded")
    
    user = await get_user(callback.from_user.id)
    service = SERVICES.get(service_key, {})
    
    if service_key == "subscription":
        new_until = await extend_subscription(callback.from_user.id, 30)
        
        if user and user.get('referrer_id'):
            bonus_applied = await apply_referral_bonus(
                user['referrer_id'], callback.from_user.id, config.REFERRAL_BONUS_DAYS
            )
            if bonus_applied:
                try:
                    await bot.send_message(
                        user['referrer_id'],
                        f"🎁 *Бонус!* Твой друг оформил подписку. Тебе +{config.REFERRAL_BONUS_DAYS} день!",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        await callback.message.edit_text(
            f"🎉 *Подписка активирована!*\n\n"
            f"Действует до: *{new_until.strftime('%d.%m.%Y')}*",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await add_purchased_service(callback.from_user.id, service_key, payment_id)
        
        await callback.message.edit_text(
            f"🎉 *Оплата прошла!*\n\n"
            f"Услуга «{service.get('title', service_key)}» доступна.",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )