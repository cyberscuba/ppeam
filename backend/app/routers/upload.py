from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from minio import Minio
from minio.error import S3Error
import uuid
import re

from app.database import get_db
from app.models import Admin
from app.routers.admin import get_current_admin
from app.config import settings

router = APIRouter()

def get_minio_endpoint():
    """Normalize MinIO endpoint to format hostname:port"""
    endpoint = settings.MINIO_ENDPOINT.strip()
    # Remove protocol if present
    endpoint = re.sub(r'^https?://', '', endpoint)
    # Remove path if present
    endpoint = endpoint.split('/')[0]
    return endpoint

# MinIO client - initialize lazily to avoid import errors
_minio_client = None

def get_minio_client():
    """Get or create MinIO client"""
    global _minio_client
    if _minio_client is None:
        endpoint = get_minio_endpoint()
        _minio_client = Minio(
            endpoint,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_USE_SSL
        )
    return _minio_client

@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Upload photo to MinIO"""
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    # Generate unique filename
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    
    try:
        minio_client = get_minio_client()
        
        # Ensure bucket exists
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
        
        # Upload file
        minio_client.put_object(
            settings.MINIO_BUCKET,
            filename,
            file.file,
            length=-1,
            part_size=10*1024*1024,
            content_type=file.content_type
        )
        
        # Generate URL
        endpoint = get_minio_endpoint()
        url = f"http://{endpoint}/{settings.MINIO_BUCKET}/{filename}"
        
        return {"url": url, "filename": filename}
    
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
