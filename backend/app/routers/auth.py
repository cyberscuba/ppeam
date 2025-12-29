from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import random
import phonenumbers
from jose import jwt
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, OTPCode, Admin, Hermano
from app.config import settings
from app.services.sms import send_sms
from app.utils.security import create_access_token
from app.utils.audit import log_audit

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class OTPRequest(BaseModel):
    phone: str = Field(..., description="Phone number in E.164 format")
    full_name: str = Field(None, description="Full name for new users")

class OTPVerify(BaseModel):
    phone: str
    code: str = Field(..., min_length=6, max_length=6)
    device_id: str = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

def validate_phone(phone: str) -> str:
    """Validate and format phone number to E.164"""
    try:
        parsed = phonenumbers.parse(phone, "CO")
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

@router.post("/otp/request")
async def request_otp(
    data: OTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP code via SMS"""
    phone = validate_phone(data.phone)
    ip_address = request.client.host
    
    # Check rate limits
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)
    
    # Check OTP per hour for phone
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.phone == phone,
            OTPCode.created_at >= hour_ago
        )
    )
    recent_otps = result.scalars().all()
    if len(recent_otps) >= settings.MAX_OTP_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later.")

    
    # Generate 6-digit OTP
    code = str(random.randint(100000, 999999))
    expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    
    # Save OTP
    otp = OTPCode(
        phone=phone,
        code=code,
        purpose="login",
        expires_at=expires_at
    )
    db.add(otp)
    
    # DEBUG: Print OTP to logs (remove in production)
    print(f"🔐 OTP CODE for {phone}: {code}")
    
    # Get or create user
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    
    if not user and data.full_name:
        user = User(phone=phone, full_name=data.full_name)
        db.add(user)
    
    await db.commit()
    
    # Send SMS
    message = f"Su código de verificación es: {code}. Válido por {settings.OTP_EXPIRE_MINUTES} minutos."
    await send_sms(phone, message)
    
    await log_audit(db, None, "system", "otp_requested", {"phone": phone}, {"ip": ip_address})
    
    return {"message": "OTP sent successfully", "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}

@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(
    data: OTPVerify,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and return JWT token"""
    phone = validate_phone(data.phone)
    
    # Find valid OTP
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.phone == phone,
            OTPCode.code == data.code,
            OTPCode.expires_at > datetime.utcnow(),
            OTPCode.attempts < settings.MAX_OTP_ATTEMPTS
        ).order_by(OTPCode.created_at.desc())
    )
    otp = result.scalar_one_or_none()
    
    if not otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    
    # Increment attempts
    otp.attempts += 1
    await db.commit()
    
    # Get user
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="User not found or inactive")
    
    # Update device_id if provided
    if data.device_id:
        user.device_id = data.device_id
        await db.commit()
    
    # Create access token
    access_token = create_access_token({"sub": str(user.id), "phone": user.phone})
    
    await log_audit(db, user.id, "user", "login", {"phone": phone}, {"ip": request.client.host})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone": user.phone,
            "email": user.email
        }
    }


# Admin login with username/password
class AdminLogin(BaseModel):
    username: str
    password: str

@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(
    data: AdminLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Admin login with username and password"""
    # Find admin by username
    result = await db.execute(
        select(Admin).where(Admin.username == data.username)
    )
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    # Verify password
    if not pwd_context.verify(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    # Get user or hermano
    user = None
    hermano = None
    
    if admin.user_id:
        result = await db.execute(select(User).where(User.id == admin.user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Usuario inactivo")
    
    if admin.hermano_id:
        result = await db.execute(select(Hermano).where(Hermano.id == admin.hermano_id))
        hermano = result.scalar_one_or_none()
        if not hermano or not hermano.is_active:
            raise HTTPException(status_code=403, detail="Hermano inactivo")
    
    if not user and not hermano:
        raise HTTPException(status_code=403, detail="Admin sin usuario o hermano asociado")
    
    # Create access token with admin flag
    # Use user_id if available, otherwise use hermano_id with a prefix
    token_sub = str(user.id) if user else f"hermano_{admin.hermano_id}"
    phone = user.phone if user else hermano.telefono
    full_name = user.full_name if user else hermano.nombre
    
    # Admin tokens expire in 8 hours (480 minutes) instead of 15 minutes
    access_token = create_access_token({
        "sub": token_sub,
        "phone": phone,
        "is_admin": True,
        "role": admin.role
    }, expire_minutes=480)  # 8 hours for admin sessions
    
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "admin_login", {"username": data.username}, {"ip": request.client.host})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id) if user else str(hermano.id),
            "full_name": full_name,
            "phone": phone,
            "email": user.email if user else None,
            "is_admin": True,
            "role": admin.role
        }
    }
