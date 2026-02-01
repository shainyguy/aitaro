import uuid
import aiohttp
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from config import config


class PaymentType(Enum):
    SUBSCRIPTION = "subscription"
    COMPATIBILITY = "compatibility"
    NATAL_CHART = "natal_chart"


@dataclass
class PaymentInfo:
    payment_id: str
    status: str
    amount: float
    currency: str
    confirmation_url: Optional[str]
    payment_method: Optional[str]
    paid: bool
    metadata: Dict[str, Any]


class YooKassaService:
    """Сервис для работы с ЮKassa API"""
    
    API_URL = "https://api.yookassa.ru/v3"
    
    def __init__(self):
        self.shop_id = config.YOOKASSA_SHOP_ID
        self.secret_key = config.YOOKASSA_SECRET_KEY
    
    def _get_auth_header(self) -> str:
        credentials = f"{self.shop_id}:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _get_headers(self, idempotency_key: str = None) -> dict:
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json"
        }
        if idempotency_key:
            headers["Idempotence-Key"] = idempotency_key
        return headers
    
    async def create_payment(
        self,
        user_id: int,
        payment_type: PaymentType,
        amount: float,
        description: str,
        return_url: str = None
    ) -> Optional[PaymentInfo]:
        """Создать платёж"""
        
        idempotency_key = str(uuid.uuid4())
        
        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or config.YOOKASSA_RETURN_URL
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": user_id,
                "payment_type": payment_type.value
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/payments",
                    json=payload,
                    headers=self._get_headers(idempotency_key)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_payment_response(data)
                    else:
                        print(f"YooKassa error: {await response.text()}")
                        return None
        except Exception as e:
            print(f"YooKassa exception: {e}")
            return None
    
    async def get_payment(self, payment_id: str) -> Optional[PaymentInfo]:
        """Получить информацию о платеже"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_URL}/payments/{payment_id}",
                    headers=self._get_headers()
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_payment_response(data)
                    return None
        except Exception:
            return None
    
    def _parse_payment_response(self, data: dict) -> PaymentInfo:
        confirmation_url = None
        if "confirmation" in data:
            confirmation_url = data["confirmation"].get("confirmation_url")
        
        payment_method = None
        if "payment_method" in data:
            payment_method = data["payment_method"].get("type")
        
        return PaymentInfo(
            payment_id=data["id"],
            status=data["status"],
            amount=float(data["amount"]["value"]),
            currency=data["amount"]["currency"],
            confirmation_url=confirmation_url,
            payment_method=payment_method,
            paid=data.get("paid", False),
            metadata=data.get("metadata", {})
        )


yookassa_service = YooKassaService()


def get_payment_description(payment_type: PaymentType) -> str:
    descriptions = {
        PaymentType.SUBSCRIPTION: "Премиум подписка Astro AI на 30 дней",
        PaymentType.COMPATIBILITY: "Анализ совместимости Astro AI",
        PaymentType.NATAL_CHART: "Полная натальная карта Astro AI"
    }
    return descriptions.get(payment_type, "Услуга Astro AI")


def get_payment_amount(payment_type: PaymentType) -> float:
    amounts = {
        PaymentType.SUBSCRIPTION: config.SUBSCRIPTION_PRICE,
        PaymentType.COMPATIBILITY: config.COMPATIBILITY_PRICE,
        PaymentType.NATAL_CHART: config.NATAL_CHART_PRICE
    }
    return amounts.get(payment_type, 0)