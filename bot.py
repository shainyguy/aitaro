import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import config
from database import init_db
from handlers import start, tarot, payments, referral
from handlers import horoscope, compatibility, moon, astro_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация БД
    await init_db()
    
    # Создание бота (без DefaultBotProperties)
    bot = Bot(
        token=config.BOT_TOKEN,
        parse_mode=ParseMode.MARKDOWN
    )
    
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
    
    # Удаляем webhook и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("🔮 Astro AI Bot запущен!")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
