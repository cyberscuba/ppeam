"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# ==================== AUTH ====================
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    exhibitor_id: Optional[str] = None
    position: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# ==================== HERMANO ====================
class HermanoResponse(BaseModel):
    id: str
    nombre: str
    telefono: str
    congregacion: str
    genero: Optional[str] = None

    class Config:
        from_attributes = True

# ==================== EXHIBITOR ====================
class ExhibitorResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

# ==================== REQUEST ====================
class RequestItemResponse(BaseModel):
    id: str
    schedule_id: str
    status: str
    date: Optional[str] = None

    class Config:
        from_attributes = True

class RequestResponse(BaseModel):
    id: str
    hermano: HermanoResponse
    status: str
    turns_requested: int
    created_at: str
    turns: List[RequestItemResponse] = []

    class Config:
        from_attributes = True

# ==================== POINT ADMIN ====================
class PointAdminStatsResponse(BaseModel):
    exhibitor: Dict[str, Any]
    stats: Dict[str, Any]
    updated_at: str

class PointAdminRequestListResponse(BaseModel):
    data: List[RequestResponse]
    pagination: Dict[str, Any]

class HermanoRequestListResponse(BaseModel):
    id: str
    nombre: str
    telefono: str
    congregacion: str
    genero: Optional[str] = None
    request_count: int

class HermanoRequestListDataResponse(BaseModel):
    data: List[HermanoRequestListResponse]
    pagination: Dict[str, Any]

class ReleaseTurnResponse(BaseModel):
    message: str
    request_item_id: str
    status: str

class ExportResponse(BaseModel):
    content: Optional[str] = None
    filename: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    exported_at: Optional[str] = None
    point_id: Optional[str] = None
