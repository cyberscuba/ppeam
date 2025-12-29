from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models import User, Hermano
from app.utils.gender_detector import detect_gender_from_name, get_gender_label
import phonenumbers
import re

router = APIRouter()

@router.get("/search")
async def search_user(
    phone: str = Query(..., description="Phone number to search"),
    db: AsyncSession = Depends(get_db)
):
    """Search hermano by phone number - searches in hermanos table first"""
    # Clean phone: remove all non-digits for comparison
    phone_clean = re.sub(r'\D', '', phone)
    
    if not phone_clean or len(phone_clean) < 7:
        return {"found": False}
    
    # Try to format phone for E.164 (for User table search as fallback)
    try:
        parsed = phonenumbers.parse(phone, "CO")
        formatted_phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except:
        formatted_phone = phone
    
    # First, search in hermanos table (exact match or contains)
    # Search by exact match first
    result_hermano = await db.execute(
        select(Hermano).where(
            Hermano.is_active == True,
            or_(
                Hermano.telefono == phone.strip(),
                Hermano.telefono.like(f'%{phone_clean}%')
            )
        )
    )
    hermano = result_hermano.scalar_one_or_none()
    
    if hermano:
        gender = detect_gender_from_name(hermano.nombre)
        gender_label = get_gender_label(hermano.nombre)
        return {
            "found": True,
            "user": {
                "id": str(hermano.id),
                "full_name": hermano.nombre,
                "nombre": hermano.nombre,  # Alias for compatibility
                "phone": hermano.telefono,
                "telefono": hermano.telefono,  # Alias for compatibility
                "congregacion": hermano.congregacion
            },
            "type": "hermano",
            "gender": gender,
            "gender_label": gender_label
        }
    
    # Fallback: search in users table (for backward compatibility)
    result_user = await db.execute(
        select(User).where(User.phone == formatted_phone, User.is_active == True)
    )
    user = result_user.scalar_one_or_none()
    
    if user:
        gender = detect_gender_from_name(user.full_name)
        gender_label = get_gender_label(user.full_name)
        return {
            "found": True,
            "user": {
                "id": str(user.id),
                "full_name": user.full_name,
                "phone": user.phone
            },
            "type": "user",
            "gender": gender,
            "gender_label": gender_label
        }
    
    return {"found": False}
