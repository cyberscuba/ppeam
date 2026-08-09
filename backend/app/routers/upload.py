from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from pathlib import Path
from datetime import datetime

from app.database import get_db
from app.models import Admin
from app.routers.admin import get_current_admin
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuración de almacenamiento local (writable directory)
# Usar /opt/exhibidores/uploads en producción (persistente)
# O /tmp en desarrollo
UPLOAD_DIR = Path("/opt/exhibidores/uploads") if Path("/opt/exhibidores").exists() else Path("/tmp/exhibidores_uploads")

# Configuración de validación
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


async def get_optional_admin(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """Autenticación opcional - retorna admin si token es válido, None si no"""
    if not credentials:
        return None

    try:
        admin = await get_current_admin(credentials, db)
        return admin
    except:
        return None


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validar archivo - retorna (es_válido, mensaje_error)"""

    # Validar que el archivo tenga nombre
    if not file.filename:
        return False, "El archivo no tiene nombre"

    # Validar extensión
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensión no permitida: {ext}. Permitidas: JPG, PNG, WebP, GIF"

    # Validar MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False, f"Tipo de archivo no permitido: {file.content_type}. Permitidos: JPG, PNG, WebP, GIF"

    return True, ""


@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_optional_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload photo para exhibidores.

    Permite uploads sin autenticación.
    Almacena archivos en filesystem local persistente.
    """

    try:

        # Validación preliminar del archivo
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            logger.warning(f"Validación fallida: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # Validar tamaño del archivo - leer en chunks
        file_size = 0
        chunks = []

        while True:
            chunk = await file.read(8192)  # 8KB chunks
            if not chunk:
                break
            file_size += len(chunk)

            if file_size > MAX_FILE_SIZE_BYTES:
                logger.warning(f"Archivo demasiado grande: {file_size} bytes")
                raise HTTPException(
                    status_code=413,
                    detail=f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE_MB}MB"
                )

            chunks.append(chunk)

        # Validar que no esté vacío
        if file_size == 0:
            logger.warning("Archivo vacío recibido")
            raise HTTPException(status_code=400, detail="El archivo está vacío")

        # Generar nombre seguro y único
        ext = file.filename.rsplit(".", 1)[-1].lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{uuid.uuid4().hex[:8]}_{timestamp}.{ext}"

        # Crear directorio si no existe (lazy initialization)
        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Error al crear directorio de uploads: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al preparar el almacenamiento"
            )

        # Crear ruta del archivo
        file_path = UPLOAD_DIR / filename

        # Escribir archivo al disco
        try:
            with open(file_path, "wb") as f:
                for chunk in chunks:
                    f.write(chunk)

            logger.info(f"Archivo guardado: {filename} ({file_size} bytes)")

        except IOError as e:
            logger.error(f"Error al guardar archivo: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Error al guardar el archivo en el servidor"
            )

        # Generar URL del archivo
        url = f"/uploads/{filename}"

        # Log de auditoría
        if admin:
            logger.info(f"Admin {admin.id} subió foto: {filename}")
        else:
            logger.info(f"Upload anónimo: {filename}")

        return {
            "success": True,
            "url": url,
            "filename": filename,
            "message": "Foto cargada exitosamente",
            "size": file_size
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al procesar la solicitud"
        )
