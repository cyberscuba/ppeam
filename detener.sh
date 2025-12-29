#!/bin/bash

# Script para detener todos los servicios del proyecto
echo "=========================================="
echo "Sistema de Gestión de Exhibidores"
echo "Deteniendo servicios..."
echo "=========================================="

# Navegar al directorio del proyecto
cd "$(dirname "$0")"

echo ""
echo "Deteniendo servicios con Docker Compose..."
docker-compose stop

echo ""
echo "Estado de los servicios:"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ ¡Servicios detenidos!"
echo ""
echo "Para iniciar nuevamente:"
echo "  ./iniciar.sh"
echo ""
echo "Para eliminar completamente (incluyendo datos):"
echo "  docker-compose down -v"
echo "=========================================="

