from aiohttp import web
import json
import logging

from database import update_payment_status, extend_subscription, add_purchased_service, get_user, apply_referral_bonus
from config import config

logger = logging.getLogger(__name__)

bot_instance = None

def set_bot(bot):
    global bot_instance
    bot_instance = bot


async def handle_yookassa_webhook(request: web.Request) -> web.Response:
    try:
        body = await request.read()
        data = json.loads(body)
        
        logger.info(f"YooKassa webhook: {data}")
        
        event_type = data.get("event")
        payment_data = data.get("object", {})
        
        if event_type == "payment.succeeded":
            payment_id = payment_data.get("id")
            metadata = payment_data.get("metadata", {})
            user_id = int(metadata.get("user_id", 0))
            payment_type = metadata.get("payment_type")
            
            await update_payment_status(payment_id, "succeeded")
            
            if payment_type == "subscription":
                await extend_subscription(user_id, 30)
                
                user = await get_user(user_id)
                if user and user.get('referrer_id'):
                    await apply_referral_bonus(
                        user['referrer_id'], user_id, config.REFERRAL_BONUS_DAYS
                    )
            
            elif payment_type in ["compatibility", "natal_chart"]:
                await add_purchased_service(user_id, payment_type, payment_id)
        
        return web.Response(status=200, text="OK")
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500)


def create_webhook_app() -> web.Application:
    app = web.Application()
    app.router.add_post(config.WEBHOOK_PATH, handle_yookassa_webhook)
    return app