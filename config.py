import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "AstroAI_bot")
    
    # 👑 ID ГЛАВНОГО АДМИНА (ваш Telegram ID)
    SUPER_ADMIN_ID: int = int(os.getenv("SUPER_ADMIN_ID", "0"))
    
    # GigaChat
    GIGACHAT_AUTH: str = os.getenv("GIGACHAT_AUTH", "")
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"
    
    # ЮKassa
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    YOOKASSA_RETURN_URL: str = os.getenv("YOOKASSA_RETURN_URL", "")
    
    # Цены
    SUBSCRIPTION_PRICE: int = 490
    COMPATIBILITY_PRICE: int = 299
    NATAL_CHART_PRICE: int = 599
    KARMA_PRICE: int = 399
    
    # Stars
    SUBSCRIPTION_STARS: int = 250
    COMPATIBILITY_STARS: int = 150
    NATAL_CHART_STARS: int = 300
    KARMA_STARS: int = 200
    
    # Лимиты
    FREE_READINGS_LIMIT: int = 1
    REFERRAL_BONUS_DAYS: int = 1
    TRIAL_DAYS: int = 0  # Пробный период

config = Config()
