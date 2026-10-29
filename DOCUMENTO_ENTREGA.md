# Documento Formal de Entrega — Sistema de Gestión de Exhibidores PPEAM Pereira

**Confidencial — Uso interno del equipo receptor**

| Campo | Detalle |
|---|---|
| Proyecto | Sistema de Gestión de Exhibidores (PPEAM Pereira) |
| Dominio | https://ppeamrisaralda.com.co |
| Servidor de producción | 206.81.0.238 |
| Fecha de entrega | _(completar)_ |
| Entrega | _(nombre de quien entrega)_ |
| Recibe | _(líder / nuevo equipo)_ |

> **Aviso de seguridad:** Este documento contiene credenciales reales de producción. Trátese como confidencial. Se recomienda que, una vez recibido el proyecto, el nuevo equipo **rote todas las credenciales** (contraseñas de base de datos, JWT_SECRET, MinIO, tokens de Twilio) y elimine o archive este documento de forma segura.

---

## 1. Descripción del Sistema

Sistema web (mobile-first) para coordinar la asignación de turnos de hermanos en "exhibidores" (puntos fijos de exhibición de publicaciones) de la zona Metropolitana de Pereira.

- Los **hermanos** se identifican por número de teléfono (sin contraseña) y solicitan turnos en los puntos disponibles.
- Los **administradores** gestionan puntos, horarios, encargados y solicitudes mediante usuario y contraseña.
- Las solicitudes públicas se **auto-aprueban** si hay cupo; la gestión del admin sirve para liberar/rechazar turnos.

---

## 2. Arquitectura y Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI (async) |
| Base de datos | PostgreSQL 15 |
| Cache / Cola | Redis 7 + Celery |
| Almacenamiento de archivos | MinIO (S3-compatible) |
| Mensajería | Twilio (SMS + WhatsApp) |
| Infraestructura | Docker + Docker Compose |
| Proxy inverso | Nginx + SSL (Let's Encrypt / Certbot) |
| Orquestación en servidor | systemd (`ppeam.service`) |

---

## 3. Acceso al Servidor de Producción

| Recurso | Valor |
|---|---|
| IP del servidor | 206.81.0.238 |
| Dominio | ppeamrisaralda.com.co, www.ppeamrisaralda.com.co |
| Registro DNS | `ppeamrisaralda.com.co. A 206.81.0.238` (confirmado) |
| Sistema operativo | Ubuntu 22.04 |
| Puerto SSH | 22 |
| Usuario SSH | `root` |
| Método de acceso SSH | Clave privada (archivo a entregar por canal seguro — ver nota) |
| Directorio del proyecto | `/data/containers/ppeam` (ver `ppeam.service`) |
| Directorio de uploads | `/opt/exhibidores/backend/uploads` |

> **El acceso SSH a `206.81.0.238` no está guardado en el equipo de origen** (no existe entrada para esa IP en la configuración SSH local). El usuario y la contraseña/clave privada deben obtenerse del responsable actual y entregarse por un canal seguro aparte (gestor de contraseñas o mensaje directo al líder), **no dentro de este documento ni del repositorio**.

---

## 4. Credenciales de la Aplicación

### 4.1 Usuarios administradores

| Rol | Usuario | Contraseña |
|---|---|---|
| Super Admin | `admin` | `Admin@2026` |
| Usuario de prueba | `cuba_principal_1` | `Admin@cuba_principal` |

### 4.2 Base de datos PostgreSQL

| Campo | Valor |
|---|---|
| Usuario | `exhibidores` |
| Contraseña | `exhibidores123` |
| Base de datos | `exhibidores_db` |
| Puerto expuesto (dev) | 5433 |
| Cadena de conexión | `postgresql://exhibidores:exhibidores123@postgres:5432/exhibidores_db` |

### 4.3 MinIO (almacenamiento de archivos)

| Campo | Valor |
|---|---|
| Usuario root | `minioadmin` |
| Contraseña | `minioadmin123` |
| Consola | puerto 9001 |
| Bucket | `exhibidores` |

### 4.4 Redis

| Campo | Valor |
|---|---|
| URL | `redis://redis:6379/0` |
| Contraseña | (sin contraseña) |
| Puerto expuesto (dev) | 6380 |

### 4.5 JWT

| Campo | Valor |
|---|---|
| JWT_SECRET (en `.env`) | `change_me_to_random_64_char_string_minimum_32_characters` |
| Algoritmo | HS256 |
| Expiración token usuario | 15 min |
| Expiración token admin | 480 min (8 h) |

> **Pendiente de seguridad:** el `JWT_SECRET` del `.env` del repositorio sigue siendo el valor placeholder por defecto. Debe verificarse cuál es el valor real en el `.env` del servidor de producción y, en todo caso, rotarse.

### 4.6 Twilio (SMS / WhatsApp)

| Campo | Valor |
|---|---|
| Account SID | _(placeholder en repo: `your_account_sid_here` — obtener valor real del `.env` del servidor)_ |
| Auth Token | _(placeholder en repo — obtener del servidor)_ |
| Número SMS | _(configurar)_ |
| Número WhatsApp | _(configurar)_ |

> Las credenciales de Twilio en el repositorio son placeholders. Los valores reales están en el `.env` del servidor de producción. Recuperarlos desde `/data/containers/ppeam/.env` y registrarlos aquí o entregarlos por canal seguro.

---

## 5. Variables de Entorno

El archivo de configuración es `.env` en la raíz del proyecto. Variables principales (ver `backend/app/config.py` para la lista completa):

- `DATABASE_URL`, `REDIS_URL`
- `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TWILIO_WHATSAPP_NUMBER`
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ENDPOINT`, `MINIO_BUCKET`
- `FRONTEND_URL`, `BACKEND_URL`, `ENVIRONMENT`, `ALLOWED_ORIGINS`

> El `.env` real de producción **vive en el servidor**, no en el repositorio. Debe copiarse del servidor y entregarse por canal seguro.

---

## 6. Despliegue

### En producción (servidor actual)

El sistema corre vía systemd + Docker Compose:

```bash
# Estado del servicio
sudo systemctl status ppeam

# Iniciar / detener / reiniciar
sudo systemctl start ppeam
sudo systemctl stop ppeam
sudo systemctl restart ppeam

# Logs
cd /data/containers/ppeam
sudo docker compose logs -f backend
```

Nginx + SSL: la configuración está en `deploy/nginx.conf` y `deploy/ppeamrisaralda.com.co`. El certificado SSL se renueva automáticamente cada semana (`deploy/certbot-weekly.timer`).

### En desarrollo local

```bash
# Levantar todo
docker compose up -d

# Reconstruir backend tras cambios
docker compose up -d --build backend
```

| Servicio | URL local |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8080 |
| API Docs (Swagger) | http://localhost:8080/docs |
| Health check | http://localhost:8080/health |
| MinIO Console | http://localhost:9001 |

---

## 7. Estructura del Repositorio

```
LuisGabrielSalas/
├── backend/               # FastAPI (app/, routers/, models.py, utils/)
│   ├── app/routers/       # auth, users, points, requests, admin, upload, reports, health
│   ├── alembic/           # Migraciones de base de datos
│   └── ListadoHermanosMetropolitana.csv  # Padrón de hermanos (datos de carga)
├── frontend/              # React + Vite
│   └── src/pages/         # HomePage, AdminPage, AdminPointsPage, etc.
├── deploy/                # nginx, systemd, certbot
├── docker-compose.yml     # Desarrollo
├── docker-compose.production.yml  # Producción
└── .env                   # Configuración (NO versionar con secretos reales)
```

---

## 8. Carga de Datos Iniciales

El padrón de hermanos se carga desde `backend/ListadoHermanosMetropolitana.csv` (formato `NOMBRE,CONGREGACION,TELEFONO`) mediante el script de carga que corre en el `entrypoint.sh`. El script salta la carga si ya hay hermanos en la base.

---

## 9. Estado Actual y Pendientes Conocidos

Durante la revisión del código se identificaron los siguientes puntos que el nuevo equipo debe atender. Se clasifican por severidad.

### Críticos

1. **SQL Injection** en `backend/app/routers/admin.py` y `auth.py`: varias consultas usan f-strings dentro de `text()` con valores de tokens/parámetros. Migrar a parámetros nombrados.
2. **`check_time_conflict` roto** (`requests.py` vs `admin.py`): la función retorna `bool` pero se la invoca esperando un `dict` y con un parámetro extra inexistente → error al aprobar solicitudes desde el panel admin.
3. **OTP inseguro** en `auth.py`: se genera con `random` (no criptográfico) y se imprime en los logs (`print(f"OTP CODE...")`). Usar `secrets` y quitar el print.
4. **Race condition** en la reserva de cupos (`requests.py`): el conteo de cupo y la inserción no están protegidos; bajo concurrencia un slot puede sobre-asignarse.
5. **`JWT_SECRET` por defecto**: verificar y rotar en producción.

### Altos

6. `audit.py` hace `commit` dentro del log de auditoría, lo que puede confirmar transacciones parciales del llamador.
7. `upload.py` permite subida de archivos sin autenticación y valida el MIME por el header (falsificable).
8. Token JWT almacenado en `localStorage` (vulnerable a XSS).
9. Divergencia ORM/BD: el modelo `Admin` no declara `hermano_id` pero el código y la BD sí lo usan.

### Medios

10. Días festivos solo definidos hasta 2025 en `date_helpers.py` (afecta cálculos a partir de 2026).
11. Consultas N+1 en el listado de solicitudes del admin.
12. Swagger/ReDoc expuestos en producción sin distinción de entorno.

### Correcciones ya aplicadas en esta entrega

- **Carga de fotos (uploads)**: se corrigió el directorio de almacenamiento (`upload.py`), se agregó volumen persistente en `docker-compose.yml`, se montó `/uploads` en el backend (`main.py`) y se agregó el bloque `/uploads/` en los dos archivos nginx. Requiere reconstruir el backend (`docker compose up -d --build backend`) para quedar activo.

---

## 10. Términos y Tratamiento de Datos

El sistema recolecta datos personales (nombre, teléfono, congregación). El aviso de privacidad actual (`frontend/src/components/DataPrivacyModal.jsx`) es básico y **no cumple completamente la Ley 1581 de 2012 de Colombia**. El nuevo equipo debería completar: identificación del responsable (nombre/NIT/dirección), canal para ejercer derechos HABEAS DATA, y transferencias a terceros (Twilio). Pendiente de decisión del cliente.

---

## 11. Entrega del Código

El código se entrega como:

- [ ] Repositorio Git — transferencia de propiedad o colaborador (cuando el líder provea la cuenta/organización GitHub del nuevo equipo).
- [ ] Respaldo comprimido (ZIP) del repositorio completo, incluyendo historial Git.

> **Recomendación:** no publicar el repositorio como público. Contiene credenciales. Preferir transferencia privada o agregar colaboradores. Si por requisito debe hacerse público, rotar primero todas las credenciales.

---

## 12. Contactos

| Rol | Nombre | Contacto |
|---|---|---|
| Entrega | _(completar)_ | _(completar)_ |
| Líder receptor | _(completar)_ | _(completar)_ |

---

_Documento generado como parte del proceso formal de entrega del proyecto. Los campos marcados con "_(completar)_" deben llenarse antes de la entrega final._
