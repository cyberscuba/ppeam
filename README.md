# Sistema de Gestión de Exhibidores

Sistema web responsivo (mobile-first) para gestionar solicitudes de asignación de exhibidores con 40 puntos, 4 horarios por punto y calendario quincenal.

## 🚀 Tech Stack

- **Frontend**: React 18 + Vite + Tailwind CSS
- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15 + Redis
- **Queue**: Celery + Redis
- **Storage**: MinIO (S3-compatible)
- **Messaging**: Twilio (SMS + WhatsApp)
- **Infrastructure**: Docker + Docker Compose

## 📋 Características Principales

- ✅ Autenticación passwordless con OTP SMS (6 dígitos)
- ✅ Búsqueda única por nombre o teléfono
- ✅ Calendario quincenal configurable (2-4 semanas)
- ✅ Gestión de 40 puntos con 4 horarios cada uno
- ✅ Sistema de concurrencia con prioridad por timestamp
- ✅ Notificaciones automáticas SMS/WhatsApp
- ✅ Panel administrativo completo
- ✅ Reportes exportables (CSV/XLSX)
- ✅ Almacenamiento de fotos en S3/MinIO
- ✅ Auditoría completa de acciones
- ✅ Accesibilidad WCAG 2.1 AA
- ✅ Internacionalización (es-CO)

## 🔧 Requisitos Previos

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (para desarrollo local)
- Python 3.11+ (para desarrollo local)

## 🚀 Inicio Rápido

### 1. Clonar y Configurar

```bash
git clone <repo-url>
cd exhibidores-app
cp .env.example .env
# Editar .env con tus credenciales (ver sección de Variables de Entorno)
```

### 2. Iniciar Servicios

```bash
# En Windows con WSL
wsl bash iniciar.sh

# En Linux/Mac
./iniciar.sh
```

Este script:
- ✅ Arregla permisos de Docker automáticamente
- ✅ Levanta todos los servicios
- ✅ Muestra el estado de los contenedores
- ✅ Indica las URLs de acceso

### 3. Ejecutar Migraciones y Seed (Primera vez)

```bash
# Migraciones
docker-compose exec backend alembic upgrade head

# Seed inicial (puntos de exhibidor y horarios)
docker-compose exec backend python scripts/seed.py
```

### 4. Acceder a la Aplicación

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### 5. Otros Comandos Útiles

```bash
# Detener servicios
wsl bash detener.sh

# Reconstruir después de cambios en código
wsl bash reconstruir.sh           # Todo
wsl bash reconstruir.sh frontend  # Solo frontend
wsl bash reconstruir.sh backend   # Solo backend

# Ver logs
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f frontend
```

## ⚙️ Variables de Entorno

Configurar en `.env`:

```env
# Database
POSTGRES_USER=exhibidores
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=exhibidores_db
DATABASE_URL=postgresql://exhibidores:change_me_in_production@postgres:5432/exhibidores_db

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=change_me_to_random_64_char_string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890

# MinIO/S3
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=exhibidores
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# App Settings
APP_NAME="Sistema de Exhibidores"
FRONTEND_URL=http://localhost:3001
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development

# Security
RATE_LIMIT_PER_MINUTE=60
OTP_EXPIRE_MINUTES=5
MAX_OTP_ATTEMPTS=3
MAX_OTP_PER_HOUR=3
MAX_OTP_PER_DAY_IP=10

# Retention
DATA_RETENTION_DAYS=365
```

## 📱 Uso de la Aplicación

### Usuario Final

1. Ingresar nombre completo o teléfono en la búsqueda
2. Seleccionar puntos y horarios deseados
3. Solicitar OTP por SMS
4. Ingresar código de 6 dígitos
5. Confirmar solicitud
6. Recibir notificación de confirmación

### Administrador

1. Acceder con credenciales de admin
2. Ver solicitudes pendientes
3. Aprobar/Rechazar/Aprobar parcialmente
4. Gestionar puntos (activar/desactivar, fotos)
5. Configurar ventana quincenal
6. Exportar reportes

## 🔐 Seguridad

- Autenticación passwordless con OTP
- JWT con tokens de corta duración (15 min)
- Rate limiting por IP y teléfono
- Validación E.164 para teléfonos
- CSRF/XSS protection
- CSP headers
- HTTPS obligatorio en producción
- Auditoría completa de acciones

## 📊 Base de Datos

### Migraciones

```bash
# Crear nueva migración
docker-compose exec backend alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
docker-compose exec backend alembic upgrade head

# Revertir última migración
docker-compose exec backend alembic downgrade -1
```

### Backup

```bash
# Backup manual
docker-compose exec postgres pg_dump -U exhibidores exhibidores_db > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U exhibidores exhibidores_db < backup_20231201.sql
```

### Backup Automático

El sistema incluye backups nocturnos automáticos a las 2 AM:

```bash
# Ver logs de backup
docker-compose logs backup
```

## 🔄 Configuración de Ventana Quincenal

### Desde Admin UI

1. Ir a Configuración → Ventana de Reservas
2. Seleccionar duración (2, 3 o 4 semanas)
3. Establecer fecha de inicio y fin
4. Guardar cambios

### Desde Base de Datos

```sql
-- Cambiar ventana a 3 semanas
UPDATE app_settings 
SET value = '{"weeks": 3, "start_date": "2024-01-01", "end_date": "2024-01-21"}'::jsonb
WHERE key = 'booking_window';
```

## 📨 Configuración de Mensajería

### Twilio SMS

1. Crear cuenta en [Twilio](https://www.twilio.com)
2. Obtener Account SID y Auth Token
3. Comprar número de teléfono
4. Configurar en `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890
```

### Twilio WhatsApp

1. Activar WhatsApp en Twilio Console
2. Configurar WhatsApp Sandbox o número aprobado
3. Configurar en `.env`:

```env
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890
```

### Meta Business API (Alternativa)

Documentación en `docs/meta-whatsapp-setup.md`

## 🧪 Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Con coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 📦 Despliegue en Producción (Ubuntu 22.04)

### 1. Preparar Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose-plugin -y
```

### 2. Clonar y Configurar

```bash
cd /opt
sudo git clone <repo-url> exhibidores-app
cd exhibidores-app
sudo cp .env.example .env
sudo nano .env  # Configurar variables de producción
```

### 3. Configurar Systemd

```bash
sudo cp deploy/exhibidores.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable exhibidores
sudo systemctl start exhibidores
```

### 4. Configurar Nginx + SSL

```bash
sudo apt install nginx certbot python3-certbot-nginx -y
sudo cp deploy/nginx.conf /etc/nginx/sites-available/exhibidores
sudo ln -s /etc/nginx/sites-available/exhibidores /etc/nginx/sites-enabled/
sudo certbot --nginx -d tu-dominio.com
sudo systemctl restart nginx
```

### 5. Verificar

```bash
sudo systemctl status exhibidores
sudo docker-compose ps
curl https://tu-dominio.com/health
```

## 📊 Monitoreo

### Logs

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs específicos
docker-compose logs -f backend
docker-compose logs -f worker
```

### Métricas

- Prometheus: http://localhost:9090
- Endpoint de métricas: http://localhost:8000/metrics

### Health Check

```bash
curl http://localhost:8000/health
```

## 🔄 Política de Retención de Datos

Por defecto, los datos se retienen por 1 año (365 días).

### Cambiar Retención

```sql
UPDATE app_settings 
SET value = '{"days": 730}'::jsonb  -- 2 años
WHERE key = 'data_retention';
```

### Ejecutar Limpieza Manual

```bash
docker-compose exec backend python scripts/cleanup_old_data.py
```

La limpieza automática se ejecuta diariamente a las 3 AM.

## 📚 Documentación Adicional

- [API Documentation](http://localhost:8000/docs) - Swagger UI (auto-generada)
- [Database Schema](docs/database_schema.md)
- [Meta WhatsApp Setup](docs/meta-whatsapp-setup.md)
- [Security Best Practices](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

## 🆘 Soporte

Para soporte, contactar a: soporte@ejemplo.com
