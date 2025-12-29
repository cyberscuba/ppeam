from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import make_asgi_app
import time
import logging

from app.config import settings
from app.routers import auth, points, requests, admin, reports, upload, health

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de gestión de exhibidores con calendario quincenal",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
# In development, add common localhost origins if not already present
if settings.ENVIRONMENT == "development":
    dev_origins = ["http://localhost:3001", "http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3001", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
    for dev_origin in dev_origins:
        if dev_origin not in origins:
            origins.append(dev_origin)
    logger.info(f"CORS configured for development with origins: {origins}")
else:
    logger.info(f"CORS configured with origins: {origins}")
logger.info(f"Environment: {settings.ENVIRONMENT}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
from app.routers import users

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(points.router, prefix="/points", tags=["Points"])
app.include_router(requests.router, prefix="/requests", tags=["Requests"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(reports.router, prefix="/admin/reports", tags=["Reports"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(health.router, tags=["Health"])

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs"
    }

def add_cors_headers(response: JSONResponse, request: Request):
    """Add CORS headers to response"""
    origin = request.headers.get("origin")
    
    # Get allowed origins
    if settings.ENVIRONMENT == "development":
        # In development, allow common localhost origins
        allowed_origins = [
            "http://localhost:3001", "http://localhost:3000", "http://localhost:5173",
            "http://127.0.0.1:3001", "http://127.0.0.1:3000", "http://127.0.0.1:5173"
        ]
        # Also add configured origins
        allowed_origins.extend([o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()])
    else:
        # In production, use configured origins
        allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    
    # Add CORS headers if origin is allowed
    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    elif settings.ENVIRONMENT == "development" and origin:
        # In development, be more permissive but still require origin
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with CORS headers"""
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    add_cors_headers(response, request)
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with CORS headers"""
    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )
    add_cors_headers(response, request)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with CORS headers"""
    logger.error(f"Global exception: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
    add_cors_headers(response, request)
    return response
