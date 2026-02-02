import asyncio
import logging
import os
import json
import hashlib
import hmac
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery
from aiogram.enums import ParseMode
from aiogram.filters import Command

from config import config
from database import (
    init_db, get_user, create_user, has_active_subscription,
    get_subscription_end, get_referral_stats, increment_readings,
    extend_subscription, create_payment, update_payment_status,
    add_purchased_service, apply_referral_bonus
)
from handlers import start, tarot, payments, referral
from handlers import horoscope, compatibility, moon, astro_features
from services.yookassa_service import yookassa_service, PaymentType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный бот
bot: Bot = None


# ==================== API HANDLERS ====================

async def serve_mini_app(request):
    """Отдаём Mini App"""
    return web.FileResponse('static/index.html')


async def api_get_user(request):
    """Получить данные пользователя"""
    try:
        user_id = int(request.match_info['user_id'])
        
        # Проверяем Telegram данные
        init_data = request.headers.get('X-Telegram-Init-Data', '')
        tg_user = verify_telegram_data(init_data)
        
        # Получаем пользователя из БД
        user = await get_user(user_id)
        
        if not user:
            return web.json_response({
                'userId': user_id,
                'userName': 'Путник',
                'isPremium': False,
                'freeUsed': 0,
                'freeLimit': config.FREE_READINGS_LIMIT,
                'readings': 0,
                'referrals': 0,
                'bonusDays': 0,
                'zodiac': None,
                'zodiacEmoji': None
            })
        
        # Проверяем подписку
        is_premium = await has_active_subscription(user_id)
        sub_end = await get_subscription_end(user_id)
        ref_stats = await get_referral_stats(user_id)
        
        # Зодиак
        zodiac_map = {
            'aries': ('Овен', '♈'), 'taurus': ('Телец', '♉'),
            'gemini': ('Близнецы', '♊'), 'cancer': ('Рак', '♋'),
            'leo': ('Лев', '♌'), 'virgo': ('Дева', '♍'),
            'libra': ('Весы', '♎'), 'scorpio': ('Скорпион', '♏'),
            'sagittarius': ('Стрелец', '♐'), 'capricorn': ('Козерог', '♑'),
            'aquarius': ('Водолей', '♒'), 'pisces': ('Рыбы', '♓')
        }
        
        zodiac_key = user.get('zodiac_sign', '')
        zodiac_info = zodiac_map.get(zodiac_key, (None, None))
        
        return web.json_response({
            'userId': user_id,
            'userName': user.get('first_name', 'Путник'),
            'isPremium': is_premium,
            'subscriptionEnd': sub_end.isoformat() if sub_end else None,
            'freeUsed': user.get('free_readings_used', 0),
            'freeLimit': config.FREE_READINGS_LIMIT,
            'readings': user.get('free_readings_used', 0),
            'referrals': ref_stats.get('total_referrals', 0),
            'bonusDays': ref_stats.get('total_bonus_days', 0),
            'zodiac': zodiac_info[0],
            'zodiacEmoji': zodiac_info[1],
            'birthDate': user.get('birth_date')
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def api_use_reading(request):
    """Использовать бесплатный расклад"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        reading_type = data.get('type', 'tarot')
        
        if not user_id:
            return web.json_response({'error': 'user_id required'}, status=400)
        
        # Проверяем подписку
        is_premium = await has_active_subscription(user_id)
        
        if not is_premium:
            # Увеличиваем счётчик
            await increment_readings(user_id)
        
        # Получаем обновлённые данные
        user = await get_user(user_id)
        free_used = user.get('free_readings_used', 0) if user else 1
        
        return web.json_response({
            'status': 'ok',
            'freeUsed': free_used,
            'freeLimit': config.FREE_READINGS_LIMIT,
            'canUse': is_premium or free_used < config.FREE_READINGS_LIMIT
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def api_create_payment(request):
    """Создать платёж"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        method = data.get('method', 'stars')  # stars или yookassa
        product = data.get('product', 'subscription')
        
        if not user_id:
            return web.json_response({'error': 'user_id required'}, status=400)
        
        if method == 'stars':
            # Telegram Stars — создаём инвойс
            invoice_link = await create_stars_invoice(user_id, product)
            
            if invoice_link:
                return web.json_response({
                    'status': 'ok',
                    'method': 'stars',
                    'invoiceLink': invoice_link
                })
            else:
                return web.json_response({
                    'status': 'error',
                    'message': 'Failed to create invoice'
                }, status=500)
        
        elif method == 'yookassa':
            # ЮKassa — создаём платёж
            payment = await yookassa_service.create_payment(
                user_id=user_id,
                payment_type=PaymentType.SUBSCRIPTION,
                amount=config.SUBSCRIPTION_PRICE,
                description="Премиум подписка Astro AI на 30 дней"
            )
            
            if payment and payment.confirmation_url:
                # Сохраняем в БД
                await create_payment(
                    user_id=user_id,
                    payment_id=payment.payment_id,
                    amount=config.SUBSCRIPTION_PRICE,
                    payment_type='subscription',
                    description="Премиум подписка",
                    payment_method='yookassa'
                )
                
                return web.json_response({
                    'status': 'ok',
                    'method': 'yookassa',
                    'paymentUrl': payment.confirmation_url,
                    'paymentId': payment.payment_id
                })
            else:
                return web.json_response({
                    'status': 'error',
                    'message': 'Failed to create payment'
                }, status=500)
        
        return web.json_response({'error': 'Invalid method'}, status=400)
        
    except Exception as e:
        logger.error(f"Payment error: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def api_check_payment(request):
    """Проверить статус платежа"""
    try:
        payment_id = request.match_info['payment_id']
        
        payment = await yookassa_service.get_payment(payment_id)
        
        if not payment:
            return web.json_response({'status': 'not_found'})
        
        if payment.status == 'succeeded' and payment.paid:
            # Активируем подписку
            user_id = int(payment.metadata.get('user_id', 0))
            if user_id:
                await update_payment_status(payment_id, 'succeeded')
                new_until = await extend_subscription(user_id, 30)
                
                # Бонус рефереру
                user = await get_user(user_id)
                if user and user.get('referrer_id'):
                    await apply_referral_bonus(
                        user['referrer_id'], user_id, config.REFERRAL_BONUS_DAYS
                    )
                
                return web.json_response({
                    'status': 'succeeded',
                    'subscriptionEnd': new_until.isoformat()
                })
        
        return web.json_response({'status': payment.status})
        
    except Exception as e:
        logger.error(f"Check payment error: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def api_health(request):
    """Проверка здоровья"""
    return web.json_response({'status': 'healthy', 'bot': 'running'})


# ==================== TELEGRAM STARS ====================

async def create_stars_invoice(user_id: int, product: str = 'subscription') -> str:
    """Создать инвойс для Telegram Stars"""
    global bot
    
    if not bot:
        return None
    
    try:
        # Цены для разных продуктов
        prices = {
            'subscription': (config.SUBSCRIPTION_STARS, "⭐ Премиум подписка", "Безлимитный доступ на 30 дней"),
            'compatibility': (config.COMPATIBILITY_STARS, "💕 Совместимость", "Анализ совместимости пары"),
            'karma': (config.KARMA_STARS, "🔮 Кармический разбор", "Анализ прошлых жизней")
        }
        
        price, title, description = prices.get(product, prices['subscription'])
        
        # Создаём инвойс
        link = await bot.create_invoice_link(
            title=title,
            description=description,
            payload=f"{product}_{user_id}_{datetime.now().timestamp()}",
            currency="XTR",
            prices=[LabeledPrice(label=title, amount=price)]
        )
        
        return link
        
    except Exception as e:
        logger.error(f"Create invoice error: {e}")
        return None


def verify_telegram_data(init_data: str) -> dict:
    """Проверка данных от Telegram WebApp"""
    if not init_data or not config.BOT_TOKEN:
        return None
    
    try:
        # Парсим данные
        params = dict(x.split('=', 1) for x in init_data.split('&') if '=' in x)
        
        check_hash = params.pop('hash', None)
        if not check_hash:
            return None
        
        # Создаём строку для проверки
        data_check = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
        
        # Секретный ключ
        secret_key = hmac.new(
            b'WebAppData',
            config.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Проверяем хеш
        calculated_hash = hmac.new(
            secret_key,
            data_check.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash == check_hash:
            if 'user' in params:
                import urllib.parse
                return json.loads(urllib.parse.unquote(params['user']))
        
        return None
    except Exception as e:
        logger.error(f"Verify error: {e}")
        return None


# ==================== WEB SERVER ====================

def create_app() -> web.Application:
    """Создать веб-приложение"""
    app = web.Application()
    
    # CORS middleware
    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            if request.method == 'OPTIONS':
                return web.Response(headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-Telegram-Init-Data',
                })
            
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        return middleware_handler
    
    app.middlewares.append(cors_middleware)
    
    # Routes
    app.router.add_get('/', serve_mini_app)
    app.router.add_get('/app', serve_mini_app)
    app.router.add_get('/api/user/{user_id}', api_get_user)
    app.router.add_post('/api/use-reading', api_use_reading)
    app.router.add_post('/api/create-payment', api_create_payment)
    app.router.add_get('/api/check-payment/{payment_id}', api_check_payment)
    app.router.add_get('/api/health', api_health)
    app.router.add_get('/health', api_health)
    
    # Статика
    app.router.add_static('/static/', path='static/', name='static')
    
    return app


async def start_web_server():
    """Запуск веб-сервера"""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Web server started on port {port}")
    logger.info(f"📱 Mini App: http://localhost:{port}/")
    logger.info(f"🔌 API: http://localhost:{port}/api/")


# ==================== BOT HANDLERS ====================

async def handle_successful_payment(message: Message):
    """Обработка успешного платежа Stars"""
    payload = message.successful_payment.invoice_payload
    parts = payload.split('_')
    product = parts[0]
    user_id = int(parts[1]) if len(parts) > 1 else message.from_user.id
    
    if product == 'subscription':
        new_until = await extend_subscription(user_id, 30)
        
        # Бонус рефереру
        user = await get_user(user_id)
        if user and user.get('referrer_id'):
            bonus = await apply_referral_bonus(
                user['referrer_id'], user_id, config.REFERRAL_BONUS_DAYS
            )
            if bonus:
                try:
                    await bot.send_message(
                        user['referrer_id'],
                        f"🎁 *Бонус!* Твой друг оформил подписку!\n"
                        f"Тебе начислено +{config.REFERRAL_BONUS_DAYS} день!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
        
        await message.answer(
            f"🎉 *Подписка активирована!*\n\n"
            f"Действует до: *{new_until.strftime('%d.%m.%Y')}*\n\n"
            f"Теперь тебе доступны все функции! ✨",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await add_purchased_service(user_id, product, payload)
        await message.answer(
            f"🎉 *Оплата прошла успешно!*\n\n"
            f"Услуга доступна в меню.",
            parse_mode=ParseMode.MARKDOWN
        )


async def handle_pre_checkout(pre_checkout: PreCheckoutQuery):
    """Подтверждение платежа"""
    await pre_checkout.answer(ok=True)


# ==================== MAIN ====================

async def main():
    global bot
    
    # Инициализация БД
    await init_db()
    
    # Создание бота
    bot = Bot(
        token=config.BOT_TOKEN,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Диспетчер
    dp = Dispatcher()
    
    # Регистрация handlers
    dp.include_router(start.router)
    dp.include_router(tarot.router)
    dp.include_router(horoscope.router)
    dp.include_router(compatibility.router)
    dp.include_router(moon.router)
    dp.include_router(astro_features.router)
    dp.include_router(payments.router)
    dp.include_router(referral.router)
    
    # Платежи Stars
    dp.pre_checkout_query.register(handle_pre_checkout)
    dp.message.register(handle_successful_payment, F.successful_payment)
    
    # Запуск веб-сервера
    await start_web_server()
    
    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🔮 Astro AI Bot запущен!")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
