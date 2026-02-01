import aiohttp
import uuid
import ssl
from typing import Optional
from config import config


class GigaChatService:
    """Сервис для работы с GigaChat API"""
    
    AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    
    def __init__(self):
        self.access_token: Optional[str] = None
    
    async def _get_token(self) -> str:
        """Получить токен доступа"""
        if not config.GIGACHAT_AUTH:
            return ""
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {config.GIGACHAT_AUTH}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.AUTH_URL,
                    headers=headers,
                    data={"scope": config.GIGACHAT_SCOPE},
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.access_token = result["access_token"]
                        return self.access_token
        except Exception as e:
            print(f"GigaChat auth error: {e}")
        
        return ""
    
    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Генерация текста"""
        if not config.GIGACHAT_AUTH:
            return self._fallback_response(user_prompt)
        
        if not self.access_token:
            await self._get_token()
        
        if not self.access_token:
            return self._fallback_response(user_prompt)
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        payload = {
            "model": "GigaChat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 1500
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    ssl=ssl_context
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    elif response.status == 401:
                        await self._get_token()
                        return await self.generate_text(system_prompt, user_prompt)
        except Exception as e:
            print(f"GigaChat error: {e}")
        
        return self._fallback_response(user_prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """Запасной ответ без AI"""
        return "✨ Звёзды говорят, что сейчас благоприятное время для размышлений и самопознания."
    
    async def generate_horoscope(self, zodiac_sign: str, period: str = "день") -> str:
        """Генерация гороскопа"""
        system_prompt = """Ты — профессиональный астролог с 30-летним опытом. 
Пиши гороскопы красивым, мистическим языком. 
Давай конкретные советы по сферам: любовь, карьера, финансы, здоровье.
Упоминай планетарные влияния. Длина: 200-300 слов."""

        user_prompt = f"Напиши гороскоп на {period} для знака {zodiac_sign}."
        
        return await self.generate_text(system_prompt, user_prompt)
    
    async def generate_compatibility(self, sign1: str, sign2: str) -> str:
        """Анализ совместимости"""
        system_prompt = """Ты — астролог-синастрист. Анализируй совместимость пар.
Структура: общая совместимость, эмоции, интеллект, страсть, конфликты, советы.
Будь честен, но тактичен. Дай процент совместимости."""

        user_prompt = f"Проанализируй совместимость {sign1} и {sign2}."
        
        return await self.generate_text(system_prompt, user_prompt)
    
    async def generate_karma_analysis(self, birth_date: str, zodiac_sign: str) -> str:
        """Кармический анализ"""
        system_prompt = """Ты — кармический астролог и эксперт по прошлым жизням.
Проводи глубокий анализ кармы по дате рождения.
Расскажи о: кармических уроках, прошлых жизнях, талантах из прошлого,
кармических долгах, и как их отработать. Стиль — мистический, глубокий."""

        user_prompt = f"Проведи кармический анализ для человека: дата рождения {birth_date}, знак {zodiac_sign}."
        
        return await self.generate_text(system_prompt, user_prompt)
    
    async def generate_money_forecast(self, zodiac_sign: str) -> str:
        """Финансовый прогноз"""
        system_prompt = """Ты — финансовый астролог.
Давай конкретные прогнозы по деньгам на неделю.
Укажи: благоприятные дни для заработка, дни для экономии,
что стоит/не стоит делать с деньгами. Практичные советы."""

        user_prompt = f"Дай финансовый прогноз на неделю для знака {zodiac_sign}."
        
        return await self.generate_text(system_prompt, user_prompt)
    
    async def analyze_photo_synastry(self, description: str) -> str:
        """Анализ совместимости по описанию (для фото)"""
        system_prompt = """Ты — астролог-физиогномист.
Анализируй энергетику пары. Описывай их взаимодействие,
потенциал отношений, возможные трудности и советы.
Говори уверенно и мистически."""

        user_prompt = f"Проанализируй совместимость этой пары: {description}"
        
        return await self.generate_text(system_prompt, user_prompt)


gigachat_service = GigaChatService()