import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from database import init_db
from handlers import start, tarot, payments, referral
from handlers import horoscope, compatibility, moon, astro_features
from webhooks.payment_webhook import create_webhook_app, set_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start_webhook_server(app: web.Application):
    """Запуск webhook сервера"""
    port = int(os.getenv("PORT", 8080))  # Railway предоставляет PORT
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Webhook server started on port {port}")


async def main():
    # Инициализация БД
    await init_db()
    
    # Создание бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    set_bot(bot)
    
    # Диспетчер
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(tarot.router)
    dp.include_router(horoscope.router)
    dp.include_router(compatibility.router)
    dp.include_router(moon.router)
    dp.include_router(astro_features.router)
    dp.include_router(payments.router)
    dp.include_router(referral.router)
    
    # Webhook сервер для ЮKassa (если нужен)
    if config.YOOKASSA_SHOP_ID:
        webhook_app = create_webhook_app()
        await start_webhook_server(webhook_app)
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("🔮 Astro AI Bot запущен на Railway!")
    
    # Polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())