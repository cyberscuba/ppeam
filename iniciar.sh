#!/bin/bash

# Script para iniciar todos los servicios del proyecto
echo "=========================================="
echo "Sistema de Gestión de Exhibidores"
echo "Iniciando servicios..."
echo "=========================================="

# Arreglar permisos de Docker (si es necesario)
if [ ! -w /var/run/docker.sock ]; then
    echo ""
    echo "Arreglando permisos de Docker..."
    sudo chmod 666 /var/run/docker.sock
fi

# Navegar al directorio del proyecto
cd "$(dirname "$0")"

echo ""
echo "Levantando servicios con Docker Compose..."
docker-compose up -d

echo ""
echo "Esperando 5 segundos para que los servicios inicien..."
sleep 5

echo ""
echo "Estado de los servicios:"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ ¡Servicios iniciados!"
echo ""
echo "Accede a la aplicación en:"
echo "  📱 Frontend:    http://localhost:3001"
echo "  🔧 Backend:     http://localhost:8000"
echo "  📚 API Docs:    http://localhost:8000/docs"
echo "  💾 MinIO:       http://localhost:9001"
echo ""
echo "Para ver logs:"
echo "  docker-compose logs -f"
echo ""
echo "Para detener:"
echo "  ./detener.sh"
echo "=========================================="

