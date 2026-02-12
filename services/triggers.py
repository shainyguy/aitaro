import asyncio
from datetime import datetime, timedelta
from aiogram import Bot

from database import (
    get_user, has_active_subscription, get_subscription_end,
    get_setting
)
from config import config


class TriggerService:
    """Сервис триггерных сообщений для повышения конверсии"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_after_registration(self, user_id: int, user_name: str):
        """Через 1 час после регистрации"""
        await asyncio.sleep(3600)  # 1 час
        
        try:
            await self.bot.send_message(
                user_id,
                f"🌟 {user_name}, как тебе первый расклад?\n\n"
                "Если хочешь узнать больше о своей судьбе — "
                "карты ждут твоих вопросов! 🔮\n\n"
                "Напиши /start чтобы продолжить ✨"
            )
        except:
            pass
    
    async def send_after_free_used(self, user_id: int):
        """После использования бесплатной попытки — скидка!"""
        await asyncio.sleep(300)  # 5 минут
        
        if await has_active_subscription(user_id):
            return
        
        try:
            await self.bot.send_message(
                user_id,
                "🎁 *Специальное предложение!*\n\n"
                "Тебе понравился расклад? У нас есть подарок:\n\n"
                "🔥 *Скидка 30%* на премиум подписку!\n"
                "⏰ Действует только *2 часа*\n\n"
                "Промокод: `FIRST30`\n\n"
                "Используй в разделе «⭐ Подписка»",
                parse_mode="Markdown"
            )
        except:
            pass
    
    async def send_inactive_reminder(self, user_id: int, user_name: str):
        """Пользователь не заходил 3 дня"""
        try:
            await self.bot.send_message(
                user_id,
                f"🌙 {user_name}, звёзды скучают по тебе...\n\n"
                "Карты приготовили важное послание! 🔮\n\n"
                "Вернись и узнай, что ждёт тебя на этой неделе ✨\n\n"
                "/start"
            )
        except:
            pass
    
    async def send_subscription_expiring(self, user_id: int, days_left: int):
        """Подписка скоро истекает"""
        try:
            if days_left == 3:
                text = (
                    "⚠️ Твоя подписка истекает через *3 дня*!\n\n"
                    "Продли сейчас со скидкой *20%*:\n"
                    "Промокод: `RENEW20`"
                )
            elif days_left == 1:
                text = (
                    "🔔 *Последний день подписки!*\n\n"
                    "Завтра доступ к премиум функциям закроется.\n"
                    "Продли сейчас, чтобы не потерять доступ!"
                )
            elif days_left == 0:
                text = (
                    "😢 Твоя подписка истекла...\n\n"
                    "Но мы приготовили подарок!\n"
                    "Скидка *30%* на продление: `COMEBACK30`"
                )
            else:
                return
            
            await self.bot.send_message(user_id, text, parse_mode="Markdown")
        except:
            pass
    
    async def send_morning_horoscope_teaser(self, user_id: int, zodiac: str):
        """Утренний тизер гороскопа (только для бесплатных)"""
        if await has_active_subscription(user_id):
            return
        
        try:
            await self.bot.send_message(
                user_id,
                f"☀️ Доброе утро!\n\n"
                f"Твой гороскоп на сегодня готов! ⭐\n\n"
                f"_{zodiac}: Сегодня особенный день..._\n\n"
                f"🔒 Полный прогноз доступен с премиум подпиской\n\n"
                f"👑 Оформи сейчас и узнай, что приготовили звёзды!"
            )
        except:
            pass
    
    async def send_birthday_gift(self, user_id: int, user_name: str):
        """Подарок на день рождения"""
        try:
            await self.bot.send_message(
                user_id,
                f"🎂 *С Днём Рождения, {user_name}!*\n\n"
                "В честь твоего праздника дарим:\n\n"
                "🎁 *50% скидка* на годовую подписку!\n"
                "Промокод: `BIRTHDAY50`\n\n"
                "Действует 24 часа! 🎉",
                parse_mode="Markdown"
            )
        except:
            pass


# Функция для запуска проверки триггеров
async def run_trigger_checks(bot: Bot):
    """Периодическая проверка триггеров"""
    trigger_service = TriggerService(bot)
    
    while True:
        try:
            # Проверка истекающих подписок
            from database import get_users_with_expiring_subscription
            
            # ... логика проверки
            
            await asyncio.sleep(3600)  # Каждый час
        except Exception as e:
            print(f"Trigger check error: {e}")
            await asyncio.sleep(60)
