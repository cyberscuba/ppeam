from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, Time, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Hermano(Base):
    __tablename__ = "hermanos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(Text, nullable=False)
    congregacion = Column(String(100))
    telefono = Column(String(50), unique=True, nullable=False, index=True)  # Increased from 20 to 50 for multiple phones
    genero = Column(String(10), default='hermano')  # 'hermano' or 'hermana'
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    admin = relationship("Admin", back_populates="hermano", uselist=False)

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(Text, nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255))
    device_id = Column(String(255))
    whatsapp_opt_in = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    requests = relationship("Request", back_populates="user")
    admin = relationship("Admin", back_populates="user", uselist=False)

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    hermano_id = Column(UUID(as_uuid=True), ForeignKey("hermanos.id", ondelete="CASCADE"), nullable=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'super_admin' or 'lider_exhibidor'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="admin")
    hermano = relationship("Hermano", back_populates="admin")
    exhibitor_leaders = relationship("ExhibitorLeader", back_populates="admin", cascade="all, delete-orphan")

class Exhibitor(Base):
    __tablename__ = "exhibitors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=True)  # Código único del punto de exhibidor
    name = Column(Text, nullable=False)  # Nombre del punto de exhibidor (ej: "Parque de Cuba Exhibidor 1")
    description = Column(Text)
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    photo_url = Column(Text)
    order = Column(Integer, default=1)  # Order of display (para múltiples exhibidores del mismo lugar)
    max_exhibidores = Column(Integer, default=1)  # Deprecated - use max_persons_per_slot
    min_persons_per_slot = Column(Integer, default=3)  # Mínimo de personas por turno (1-9)
    max_persons_per_slot = Column(Integer, default=5)  # Máximo de personas por turno (1-9)
    open_date = Column(Date, nullable=True)  # Fecha de apertura para solicitudes
    close_date = Column(Date, nullable=True)  # Fecha de cierre para solicitudes (último día del mes)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    schedules = relationship("Schedule", back_populates="exhibitor", cascade="all, delete-orphan")
    slots = relationship("Slot", back_populates="exhibitor")
    leaders = relationship("ExhibitorLeader", back_populates="exhibitor", cascade="all, delete-orphan")

class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exhibitor_id = Column(UUID(as_uuid=True), ForeignKey("exhibitors.id", ondelete="CASCADE"), nullable=False)
    weekday = Column(Integer)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    exhibitor = relationship("Exhibitor", back_populates="schedules", lazy="select")
    slots = relationship("Slot", back_populates="schedule")

class Slot(Base):
    __tablename__ = "slots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exhibitor_id = Column(UUID(as_uuid=True), ForeignKey("exhibitors.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id"))
    slot_date = Column(Date, nullable=False, index=True)
    start_ts = Column(TIMESTAMP(timezone=True), nullable=False)
    end_ts = Column(TIMESTAMP(timezone=True), nullable=False)
    capacity = Column(Integer, default=1)  # Siempre 1 hermano por slot
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    exhibitor = relationship("Exhibitor", back_populates="slots")
    schedule = relationship("Schedule", back_populates="slots")
    request_items = relationship("RequestItem", back_populates="slot")

class Request(Base):
    __tablename__ = "requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String(30), nullable=False, default="pending", index=True)
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="requests")
    items = relationship("RequestItem", back_populates="request", cascade="all, delete-orphan")

class RequestItem(Base):
    __tablename__ = "request_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    slot_id = Column(UUID(as_uuid=True), ForeignKey("slots.id"), index=True)  # Removed unique to allow multiple requests per slot (up to capacity)
    status = Column(String(30), nullable=False, default="pending")
    assigned_at = Column(TIMESTAMP(timezone=True))
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True)  # Aprobador
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    request = relationship("Request", back_populates="items")
    slot = relationship("Slot", back_populates="request_items")
    approver = relationship("Admin", foreign_keys=[assigned_by])

class ExhibitorLeader(Base):
    __tablename__ = "exhibitor_leaders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    exhibitor_id = Column(UUID(as_uuid=True), ForeignKey("exhibitors.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(String(50), nullable=False)  # 'encargado_turnos_principal', 'encargado_turnos_remplazo', 'publicaciones_mantenimiento', 'principal', 'suplente'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    admin = relationship("Admin", back_populates="exhibitor_leaders")
    exhibitor = relationship("Exhibitor", back_populates="leaders")

class OTPCode(Base):
    __tablename__ = "otp_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), index=True)
    code = Column(String(10))
    purpose = Column(String(50))
    attempts = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), index=True)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), unique=True, nullable=False)
    device_id = Column(String(255))
    is_revoked = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    channel = Column(String(20))
    type = Column(String(50))
    external_id = Column(Text)
    payload = Column(JSON)
    status = Column(String(20), default="pending")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), index=True)
    actor_type = Column(String(20))
    action = Column(String(100))
    target = Column(JSON)
    meta = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)

class AppSetting(Base):
    __tablename__ = "app_settings"
    
    key = Column(Text, primary_key=True)
    value = Column(JSON)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
