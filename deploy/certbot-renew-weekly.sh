#!/bin/bash
# Script para renovar certificados SSL semanalmente

LOG_FILE="/var/log/certbot-renew.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Iniciando renovación de certificados SSL..." >> "$LOG_FILE"

# Renovar certificados
/usr/bin/certbot renew --quiet --nginx >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$DATE] Renovación completada exitosamente" >> "$LOG_FILE"
    # Recargar nginx si hay certificados nuevos
    systemctl reload nginx
else
    echo "[$DATE] Error en la renovación (código: $EXIT_CODE)" >> "$LOG_FILE"
fi

exit $EXIT_CODE

