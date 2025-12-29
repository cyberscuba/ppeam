from twilio.rest import Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_sms_sync(to: str, message: str) -> bool:
    """Send SMS via Twilio (synchronous version for Celery tasks)"""
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to
        )
        logger.info(f"SMS sent to {to}: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to}: {e}")
        return False

async def send_sms(to: str, message: str) -> bool:
    """Send SMS via Twilio (async wrapper)"""
    return send_sms_sync(to, message)

def send_whatsapp_sync(to: str, message: str) -> bool:
    """Send WhatsApp message via Twilio (synchronous version for Celery tasks)"""
    if not settings.TWILIO_WHATSAPP_NUMBER:
        return False
    
    try:
        msg = twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}"
        )
        logger.info(f"WhatsApp sent to {to}: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp to {to}: {e}")
        return False

async def send_whatsapp(to: str, message: str) -> bool:
    """Send WhatsApp message via Twilio (async wrapper)"""
    return send_whatsapp_sync(to, message)
