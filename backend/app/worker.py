from celery import Celery
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Request, RequestItem, User, Notification, AppSetting, Hermano, Slot, Schedule, Exhibitor
from app.services.sms import send_sms_sync, send_whatsapp_sync
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Celery app
celery_app = Celery(
    "exhibidores",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Bogota",
    enable_utc=True,
)

# Sync database for Celery
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

@celery_app.task
def send_notification_task(request_id: str, notification_type: str):
    """Send notification for request"""
    db = SessionLocal()
    try:
        # Get request
        request = db.execute(
            select(Request).where(Request.id == request_id)
        ).scalar_one_or_none()
        
        if not request:
            logger.error(f"Request {request_id} not found")
            return
        
        # Get user
        user = db.execute(
            select(User).where(User.id == request.user_id)
        ).scalar_one()
        
        # Get templates
        settings_result = db.execute(
            select(AppSetting).where(AppSetting.key == "notification_templates")
        ).scalar_one_or_none()
        
        templates = settings_result.value if settings_result else {}
        template = templates.get(notification_type, "Notificación de solicitud")
        
        # Format message
        message = template.format(
            point_name="Punto",
            date="fecha",
            time="hora",
            request_id=str(request.id)[:8]
        )
        
        # Send SMS
        send_sms_sync(user.phone, message)
        
        # Send WhatsApp if opted in
        if user.whatsapp_opt_in:
            send_whatsapp_sync(user.phone, message)
        
        # Log notification
        notification = Notification(
            user_id=user.id,
            channel="sms",
            type=notification_type,
            payload={"message": message},
            status="sent"
        )
        db.add(notification)
        db.commit()
        
        logger.info(f"Notification sent for request {request_id}")
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        db.rollback()
    finally:
        db.close()

@celery_app.task
def notify_slot_liberated_task(item_id: str):
    """Notificar a todos los hermanos activos cuando se libera un turno"""
    db = SessionLocal()
    try:
        # Obtener información del item liberado
        item_result = db.execute(
            select(RequestItem, Slot, Schedule, Exhibitor)
            .join(Slot, RequestItem.slot_id == Slot.id)
            .join(Schedule, Slot.schedule_id == Schedule.id)
            .join(Exhibitor, Slot.exhibitor_id == Exhibitor.id)
            .where(RequestItem.id == item_id)
        )
        result = item_result.first()
        
        if not result:
            logger.error(f"RequestItem {item_id} not found")
            return
        
        item, slot, schedule, exhibitor = result
        
        # Formatear fecha en español
        MONTH_NAMES = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        slot_date = slot.slot_date
        weekday_name = WEEKDAYS[slot_date.weekday()]
        month_name = MONTH_NAMES[slot_date.month - 1]
        formatted_date = f"{weekday_name}, {slot_date.day} de {month_name} de {slot_date.year}"
        
        # Formatear hora (Time objects de SQLAlchemy)
        start_time_str = str(schedule.start_time)[:5]  # HH:MM
        end_time_str = str(schedule.end_time)[:5]     # HH:MM
        time_range = f"{start_time_str} - {end_time_str}"
        
        # Crear mensaje
        message = (
            f"🎉 ¡TURNO DISPONIBLE!\n\n"
            f"📅 Fecha: {formatted_date}\n"
            f"🕐 Horario: {time_range}\n"
            f"📍 Exhibidor: {exhibitor.name}\n"
            f"💚 Un turno ha sido liberado y está disponible. ¡Reserva ahora!"
        )
        
        # Obtener todos los hermanos activos con teléfono
        hermanos_result = db.execute(
            select(Hermano).where(
                Hermano.is_active == True,
                Hermano.telefono.isnot(None),
                Hermano.telefono != ''
            )
        )
        hermanos = hermanos_result.scalars().all()
        
        logger.info(f"Enviando notificación de turno liberado a {len(hermanos)} hermanos")
        
        # Enviar a cada hermano
        sent_count = 0
        failed_count = 0
        
        for hermano in hermanos:
            try:
                # Limpiar y formatear teléfono
                phone_clean = re.sub(r'\D', '', hermano.telefono)
                if len(phone_clean) >= 10:
                    # Formatear a E.164 (Colombia)
                    if phone_clean.startswith('57'):
                        phone_formatted = f"+{phone_clean}"
                    elif len(phone_clean) == 10:
                        phone_formatted = f"+57{phone_clean}"
                    else:
                        phone_formatted = f"+57{phone_clean[-10:]}"
                    
                    # Enviar SMS (versión síncrona para Celery)
                    success = send_sms_sync(phone_formatted, message)
                    
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to send SMS to {hermano.nombre} ({phone_formatted})")
                else:
                    logger.warning(f"Invalid phone for {hermano.nombre}: {hermano.telefono}")
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error sending to {hermano.nombre}: {e}")
                failed_count += 1
        
        logger.info(f"Notificaciones enviadas: {sent_count} exitosas, {failed_count} fallidas")
        
        # Log notification summary
        notification = Notification(
            user_id=None,  # Notificación masiva
            channel="sms",
            type="slot_liberated",
            payload={
                "message": message,
                "exhibitor_name": exhibitor.name,
                "date": slot_date.isoformat(),
                "time_range": time_range,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_recipients": len(hermanos)
            },
            status="sent" if sent_count > 0 else "failed"
        )
        db.add(notification)
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to send slot liberation notifications: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
    finally:
        db.close()
