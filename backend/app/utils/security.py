from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import User, Hermano
from uuid import UUID

security = HTTPBearer()

def create_access_token(data: dict, expire_minutes: int = None) -> str:
    """Create JWT access token
    
    Args:
        data: Token payload data
        expire_minutes: Optional expiration time in minutes. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES
    """
    to_encode = data.copy()
    expire_time = expire_minutes if expire_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.utcnow() + timedelta(minutes=expire_time)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user - handles both User and Hermano tokens"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Por favor, inicie sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception
    
    # Check if it's a hermano token (prefixed with "hermano_")
    if user_id.startswith("hermano_"):
        # Extract hermano_id
        hermano_id_str = user_id.replace("hermano_", "")
        try:
            hermano_id = UUID(hermano_id_str)
        except ValueError:
            raise credentials_exception
        
        # Get hermano
        result = await db.execute(select(Hermano).where(Hermano.id == hermano_id))
        hermano = result.scalar_one_or_none()
        
        if hermano is None or not hermano.is_active:
            raise credentials_exception
        
        # Create or get a temporary User for hermano (for compatibility)
        # Try to find existing user by phone - be flexible with phone matching
        import re
        phone_clean = re.sub(r'\D', '', hermano.telefono)
        
        # Try multiple phone formats
        phone_variants = []
        if len(phone_clean) == 10:
            phone_variants = [
                f"+57{phone_clean}",
                f"57{phone_clean}",
                phone_clean,
                hermano.telefono  # Original format
            ]
        else:
            phone_variants = [
                f"+{phone_clean}" if not phone_clean.startswith('+') else phone_clean,
                phone_clean,
                hermano.telefono  # Original format
            ]
        
        user = None
        phone_last_10 = phone_clean[-10:] if len(phone_clean) >= 10 else phone_clean
        for phone_variant in phone_variants:
            result_user = await db.execute(
                select(User).where(
                    (User.phone == phone_variant) | 
                    (User.phone.like(f'%{phone_last_10}%'))
                )
            )
            user = result_user.scalar_one_or_none()
            if user:
                break
        
        if not user:
            # Create temporary user for hermano
            phone_formatted = f"+57{phone_last_10}" if len(phone_clean) >= 10 else f"+{phone_clean}"
            user = User(
                full_name=hermano.nombre,
                phone=phone_formatted,
                is_active=True
            )
            db.add(user)
            await db.flush()
            await db.commit()
            await db.refresh(user)
        
        return user
    
    # Regular user token
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user
