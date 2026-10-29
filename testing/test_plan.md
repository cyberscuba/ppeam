# 🧪 PLAN DE TESTING - SISTEMA EXHIBIDORES

## 📋 ÍNDICE
1. Testing de Autenticación
2. Testing de Endpoints Backend
3. Testing de Frontend
4. Testing de Seguridad
5. Testing de Responsividad
6. Testing de Rendimiento

---

## 1️⃣ TESTING DE AUTENTICACIÓN

### 1.1 Super Admin Login
- [ ] Acceder a `/api/admin/login`
- [ ] Credenciales: admin / Admin@2026
- [ ] ✅ JWT token recibido
- [ ] ✅ Token contiene role: super_admin
- [ ] ✅ Acceso a /admin funciona

### 1.2 Point Admin Login (cuba_principal_1)
- [ ] Acceder a `/point-admin/login`
- [ ] Credenciales: cuba_principal_1 / Admin@cuba_principal
- [ ] ✅ JWT token recibido
- [ ] ✅ Token contiene exhibitor_id
- [ ] ✅ Token contiene position: principal
- [ ] ✅ Acceso a /point-admin/dashboard funciona

### 1.3 Point Admin Login - Suplente
- [ ] Credenciales: cuba_suplente_2 / Admin@cuba_suplente
- [ ] ✅ Token contiene position: suplente
- [ ] ✅ Permisos idénticos a principal

### 1.4 Validación de Credenciales Inválidas
- [ ] ❌ Usuario incorrecto → 401
- [ ] ❌ Contraseña incorrecta → 401
- [ ] ❌ Token expirado → 401

---

## 2️⃣ TESTING DE ENDPOINTS BACKEND

### 2.1 Point Admin - Dashboard
```
GET /api/point-admin/dashboard
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Contiene exhibitor (id, name, code)
- [ ] ✅ Contiene stats (total_slots, available_slots, taken_slots, occupancy_percent)
- [ ] ✅ Datos coinciden con BD

### 2.2 Point Admin - Requests (Solicitudes)
```
GET /api/point-admin/requests?status=approved&page=1&limit=20
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Array de requests con hermano info
- [ ] ✅ Paginación funciona
- [ ] ✅ Filtro por status funciona
- [ ] ✅ Solo ve solicitudes de su punto

### 2.3 Point Admin - Release Turn
```
POST /api/point-admin/release-turn/{request_item_id}?reason=No%20puede%20asistir
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Turno marcado como available
- [ ] ✅ Auditoría registrada
- [ ] ✅ Mensaje de confirmación

### 2.4 Point Admin - Hermanos Request List
```
GET /api/point-admin/hermanos-request-list?page=1&limit=20
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Lista ordenada por request_count DESC
- [ ] ✅ Paginación funciona
- [ ] ✅ Campos: nombre, telefono, congregacion, request_count

### 2.5 Point Admin - Export Data
```
GET /api/point-admin/export?format=csv
Authorization: Bearer {token}
```
- [ ] ✅ Response 200 (CSV)
- [ ] ✅ Archivo descargable
- [ ] ✅ Formato válido (encabezados, separadores)
- [ ] ✅ Datos completos

```
GET /api/point-admin/export?format=json
Authorization: Bearer {token}
```
- [ ] ✅ Response 200 (JSON)
- [ ] ✅ JSON válido
- [ ] ✅ Estructura correcta

### 2.6 Analytics - Occupancy Daily
```
GET /api/point-admin/analytics/occupancy-daily?days=30
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Array con datos por día
- [ ] ✅ Campos: date, taken, total, occupancy_percent
- [ ] ✅ average_occupancy calculado

### 2.7 Analytics - Requests Weekly
```
GET /api/point-admin/analytics/requests-weekly?weeks=4
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Array con datos por semana
- [ ] ✅ Campos: week, available, taken, total

### 2.8 Analytics - Audit Trail
```
GET /api/point-admin/audit-trail?days=30&page=1&limit=20
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Lista de acciones del admin
- [ ] ✅ Campos: action, entity_type, entity_id, details, created_at
- [ ] ✅ Paginación

### 2.9 Notifications Summary
```
GET /api/point-admin/notifications/summary
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Array de alerts
- [ ] ✅ Tipos: pending, available, expiring
- [ ] ✅ Counters actualizados

### 2.10 Requests Filtered
```
GET /api/point-admin/requests-filtered?status=approved&congregation=Portales&page=1
Authorization: Bearer {token}
```
- [ ] ✅ Response 200
- [ ] ✅ Filtro por status
- [ ] ✅ Filtro por congregation
- [ ] ✅ Filtro por fecha (date_from/date_to)
- [ ] ✅ Paginación

---

## 3️⃣ TESTING DE FRONTEND

### 3.1 Point Admin Login Page (`/point-admin/login`)
- [ ] ✅ Página carga correctamente
- [ ] ✅ Campos: Usuario, Contraseña
- [ ] ✅ Botón Ingresar funciona
- [ ] ✅ Validación: campos requeridos
- [ ] ✅ Mensaje de error en credenciales inválidas
- [ ] ✅ Redirección a dashboard tras login exitoso
- [ ] ✅ Token guardado en localStorage

### 3.2 Point Admin Dashboard (`/point-admin/dashboard`)

#### Tab Resumen
- [ ] ✅ Nombre del punto visible
- [ ] ✅ Posición (Principal/Suplente) visible
- [ ] ✅ Card de Total Slots
- [ ] ✅ Card de Disponibles
- [ ] ✅ Card de Tomados
- [ ] ✅ Card de Ocupación %
- [ ] ✅ Botón Cerrar Sesión funciona
- [ ] ✅ Datos actualizados

#### Tab Turnos Solicitados
- [ ] ✅ Lista de hermanos cargada
- [ ] ✅ Información: nombre, teléfono, congregación
- [ ] ✅ Estado de cada solicitud
- [ ] ✅ Botón para liberar turno
- [ ] ✅ Input para razón de liberación
- [ ] ✅ Paginación funciona
- [ ] ✅ Botones exportar CSV/JSON funcionan

#### Tab Hermanos
- [ ] ✅ Lista de hermanos cargada
- [ ] ✅ Ordenados por cantidad de solicitudes (DESC)
- [ ] ✅ Información: nombre, teléfono, congregación
- [ ] ✅ Badge con cantidad de turnos
- [ ] ✅ Paginación (20 x página)
- [ ] ✅ Número de posición visible

### 3.3 Analytics Page (`/point-admin/analytics`)

#### Notificaciones
- [ ] ✅ Card de solicitudes pendientes (24h)
- [ ] ✅ Card de turnos disponibles
- [ ] ✅ Card de turnos próximos a vencer
- [ ] ✅ Colores según severidad

#### Gráfico Ocupación Diaria
- [ ] ✅ Gráfico cargado
- [ ] ✅ Eje X: fechas
- [ ] ✅ Eje Y: porcentaje
- [ ] ✅ Línea azul visible
- [ ] ✅ Selector de días (7/14/30/90)
- [ ] ✅ Ocupación promedio mostrada
- [ ] ✅ Datos actualizados al cambiar selector

#### Gráfico Solicitudes Semanales
- [ ] ✅ Gráfico cargado (barras)
- [ ] ✅ 2 series: disponibles (verde), tomados (azul)
- [ ] ✅ Eje X: semanas
- [ ] ✅ Eje Y: cantidad
- [ ] ✅ Selector de semanas (4/8/12)
- [ ] ✅ Datos actualizados

#### Audit Trail
- [ ] ✅ Tabla cargada
- [ ] ✅ Columnas: acción, fecha/hora, detalles
- [ ] ✅ Histórico de últimos 30 días
- [ ] ✅ Paginación funciona
- [ ] ✅ Detalles en JSON visible

---

## 4️⃣ TESTING DE SEGURIDAD

### 4.1 Autenticación
- [ ] ✅ Token requerido en headers
- [ ] ✅ Token inválido → 401
- [ ] ✅ Token expirado → 401
- [ ] ✅ Sin token → 401

### 4.2 Autorización
- [ ] ✅ Point Admin solo ve su punto
- [ ] ✅ Point Admin no puede ver otros puntos
- [ ] ✅ Point Admin no puede eliminar turnos (solo liberar)
- [ ] ✅ Contraseñas almacenadas con bcrypt

### 4.3 Auditoría
- [ ] ✅ Todas las acciones registradas
- [ ] ✅ Admin ID asociado
- [ ] ✅ Razón de liberación guardada
- [ ] ✅ Timestamp preciso

### 4.4 Validación de Entrada
- [ ] ✅ Campos requeridos validados
- [ ] ✅ Tipos de datos verificados
- [ ] ✅ SQL injection prevenido (ORM)
- [ ] ✅ XSS prevenido (React)

---

## 5️⃣ TESTING DE RESPONSIVIDAD

### 5.1 Mobile (< 640px)
- [ ] ✅ Login page responsive
- [ ] ✅ Dashboard responsive
- [ ] ✅ Analytics responsive
- [ ] ✅ Gráficos se ajustan
- [ ] ✅ Tablas scrollean horizontalmente

### 5.2 Tablet (640px - 1024px)
- [ ] ✅ Todas las páginas legibles
- [ ] ✅ Contenido no se superpone
- [ ] ✅ Clickeable en touch

### 5.3 Desktop (> 1024px)
- [ ] ✅ Layout óptimo
- [ ] ✅ Gráficos en tamaño completo
- [ ] ✅ Tablas con todas las columnas

---

## 6️⃣ TESTING DE RENDIMIENTO

### 6.1 Carga
- [ ] ✅ Login page: < 2s
- [ ] ✅ Dashboard: < 3s
- [ ] ✅ Analytics: < 4s
- [ ] ✅ Gráficos: < 2s (renderizado)

### 6.2 API Response Time
- [ ] ✅ Dashboard endpoint: < 500ms
- [ ] ✅ Requests endpoint: < 500ms
- [ ] ✅ Analytics: < 1s
- [ ] ✅ Export: < 2s

### 6.3 Memoria
- [ ] ✅ Sin memory leaks
- [ ] ✅ Gráficos no congelan
- [ ] ✅ Paginación previene overload

---

## 📝 CASOS DE USO END-TO-END

### Caso 1: Encargado Principal Atiende Solicitud
```
1. Login: cuba_principal_1 / Admin@cuba_principal
2. Ver Dashboard → Tab Turnos Solicitados
3. Seleccionar hermano que no puede asistir
4. Ingresar razón: "Enfermo"
5. Liberar turno
6. Verificar auditoría
```
- [ ] ✅ Turno liberado
- [ ] ✅ Estado disponible
- [ ] ✅ Registro en auditoría

### Caso 2: Ver Analytics Completo
```
1. Ir a /point-admin/analytics
2. Ver notificaciones
3. Revisar gráfico de ocupación
4. Revisar gráfico de solicitudes
5. Descargar reporte CSV
6. Ver audit trail
```
- [ ] ✅ Todos los datos cargan
- [ ] ✅ CSV válido
- [ ] ✅ Gráficos precisos

### Caso 3: Super Admin Gestiona Sistema
```
1. Login: admin / Admin@2026
2. Ver /admin dashboard
3. Ver todos los puntos
4. Ver estadísticas globales
```
- [ ] ✅ Acceso a todo
- [ ] ✅ Datos completos

---

## ✅ CRITERIOS DE ACEPTACIÓN

| Criterio | Peso | Status |
|----------|------|--------|
| Todos los endpoints responden | 30% | ⏳ |
| Frontend no tiene errores | 20% | ⏳ |
| Seguridad funcionando | 20% | ⏳ |
| Datos correctos en BD | 15% | ⏳ |
| Performance aceptable | 15% | ⏳ |

**Pase si:** 95% de casos pasan ✅

---

## 🎯 RESULTADO FINAL

| Área | Pruebas | Pases | % |
|------|---------|-------|---|
| Autenticación | 4 | 0/4 | ⏳ |
| Backend | 10 | 0/10 | ⏳ |
| Frontend | 30 | 0/30 | ⏳ |
| Seguridad | 4 | 0/4 | ⏳ |
| Responsividad | 8 | 0/8 | ⏳ |
| Rendimiento | 6 | 0/6 | ⏳ |
| E2E | 3 | 0/3 | ⏳ |
| **TOTAL** | **65** | **0/65** | **0%** |
