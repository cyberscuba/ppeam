#!/bin/bash

# Script para reconstruir servicios (después de cambios en código)
echo "=========================================="
echo "Sistema de Gestión de Exhibidores"
echo "Reconstruyendo servicios..."
echo "=========================================="

# Arreglar permisos de Docker (si es necesario)
if [ ! -w /var/run/docker.sock ]; then
    echo ""
    echo "Arreglando permisos de Docker..."
    sudo chmod 666 /var/run/docker.sock
fi

# Navegar al directorio del proyecto
cd "$(dirname "$0")"

# Detectar qué servicio reconstruir
SERVICE=${1:-all}

if [ "$SERVICE" = "frontend" ]; then
    echo ""
    echo "Reconstruyendo solo frontend..."
    docker-compose stop frontend
    docker rm -f exhibidores_frontend 2>/dev/null || true
    docker-compose build --no-cache frontend
    docker-compose up -d frontend
elif [ "$SERVICE" = "backend" ]; then
    echo ""
    echo "Reconstruyendo solo backend..."
    docker-compose stop backend
    docker rm -f exhibidores_backend 2>/dev/null || true
    docker-compose build --no-cache backend
    docker-compose up -d backend
else
    echo ""
    echo "Reconstruyendo todos los servicios..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
fi

echo ""
echo "Esperando 5 segundos..."
sleep 5

echo ""
echo "Estado de los servicios:"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ ¡Reconstrucción completada!"
echo ""
echo "Accede a la aplicación en:"
echo "  📱 Frontend:    http://localhost:3001"
echo "  🔧 Backend:     http://localhost:8000"
echo ""
echo "Recarga el navegador con Ctrl + Shift + R"
echo ""
echo "Uso:"
echo "  ./reconstruir.sh          # Reconstruir todo"
echo "  ./reconstruir.sh frontend # Solo frontend"
echo "  ./reconstruir.sh backend  # Solo backend"
echo "=========================================="

