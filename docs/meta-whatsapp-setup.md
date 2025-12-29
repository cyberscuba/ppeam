# Meta WhatsApp Business API Setup

## Alternativa a Twilio WhatsApp

### Requisitos

1. Cuenta de Meta Business
2. Número de teléfono verificado
3. WhatsApp Business API access

### Pasos de Configuración

#### 1. Crear App en Meta for Developers

1. Ir a https://developers.facebook.com/
2. Crear nueva app → Business
3. Agregar producto "WhatsApp"

#### 2. Configurar Número

1. En WhatsApp → Getting Started
2. Agregar número de teléfono
3. Verificar número con código SMS

#### 3. Obtener Credenciales

```
Phone Number ID: xxxxx
WhatsApp Business Account ID: xxxxx
Access Token: xxxxx
```

#### 4. Configurar Webhook

URL: `https://tu-dominio.com/webhooks/whatsapp`

Eventos a suscribir:
- messages
- message_status

#### 5. Variables de Entorno

```env
META_WHATSAPP_PHONE_ID=xxxxx
META_WHATSAPP_TOKEN=xxxxx
META_WHATSAPP_VERIFY_TOKEN=random_string_for_webhook
```

#### 6. Implementación en Backend

```python
# app/services/meta_whatsapp.py
import httpx
from app.config import settings

async def send_whatsapp_meta(to: str, message: str):
    """Send WhatsApp via Meta Business API"""
    url = f"https://graph.facebook.com/v18.0/{settings.META_WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()
```

### Plantillas de Mensajes

Para mensajes proactivos, debes crear plantillas aprobadas:

1. Ir a WhatsApp → Message Templates
2. Crear plantilla con variables
3. Esperar aprobación (24-48 horas)

Ejemplo:
```
Nombre: solicitud_confirmada
Categoría: TRANSACTIONAL
Idioma: es

Contenido:
Hola {{1}}, su solicitud para {{2}} el {{3}} fue confirmada. Gracias.
```

### Costos

- Conversaciones iniciadas por usuario: Gratis (primeras 1000/mes)
- Conversaciones iniciadas por negocio: ~$0.005 - $0.03 USD por mensaje

### Ventajas vs Twilio

- ✅ Más económico para alto volumen
- ✅ Plantillas ricas (botones, imágenes)
- ✅ Integración directa con Meta
- ❌ Requiere aprobación de plantillas
- ❌ Setup más complejo

### Documentación Oficial

https://developers.facebook.com/docs/whatsapp/cloud-api/
