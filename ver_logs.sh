#!/bin/bash

# Script para ver logs y diagnosticar errores
echo "=========================================="
echo "Sistema de Exhibidores - Ver Logs"
echo "=========================================="

# Navegar al directorio del proyecto
cd "$(dirname "$0")"

# Función para mostrar menú
show_menu() {
    echo ""
    echo "Selecciona qué logs ver:"
    echo ""
    echo "  1) Backend (FastAPI/Python)"
    echo "  2) Frontend (Nginx)"
    echo "  3) Base de datos (PostgreSQL)"
    echo "  4) Redis"
    echo "  5) Todos los servicios"
    echo "  6) Últimas 50 líneas de backend"
    echo "  7) Seguir logs en tiempo real (backend)"
    echo "  8) Buscar errores 500 en backend"
    echo "  9) Estado de todos los servicios"
    echo "  0) Salir"
    echo ""
}

# Si se pasa un argumento, usarlo directamente
if [ -n "$1" ]; then
    OPTION=$1
else
    show_menu
    read -p "Opción: " OPTION
fi

case $OPTION in
    1)
        echo ""
        echo "📋 Logs del Backend (últimas 100 líneas):"
        echo "=========================================="
        docker-compose logs --tail=100 backend
        ;;
    2)
        echo ""
        echo "📋 Logs del Frontend (últimas 100 líneas):"
        echo "=========================================="
        docker-compose logs --tail=100 frontend
        ;;
    3)
        echo ""
        echo "📋 Logs de PostgreSQL (últimas 100 líneas):"
        echo "=========================================="
        docker-compose logs --tail=100 postgres
        ;;
    4)
        echo ""
        echo "📋 Logs de Redis (últimas 100 líneas):"
        echo "=========================================="
        docker-compose logs --tail=100 redis
        ;;
    5)
        echo ""
        echo "📋 Logs de TODOS los servicios (últimas 50 líneas):"
        echo "=========================================="
        docker-compose logs --tail=50
        ;;
    6)
        echo ""
        echo "📋 Últimas 50 líneas del Backend:"
        echo "=========================================="
        docker-compose logs --tail=50 backend
        ;;
    7)
        echo ""
        echo "📋 Siguiendo logs del Backend en tiempo real..."
        echo "   (Presiona Ctrl+C para salir)"
        echo "=========================================="
        docker-compose logs -f backend
        ;;
    8)
        echo ""
        echo "🔍 Buscando errores 500 en Backend:"
        echo "=========================================="
        docker-compose logs backend | grep -i "500\|error\|exception\|traceback" | tail -100
        ;;
    9)
        echo ""
        echo "📊 Estado de todos los servicios:"
        echo "=========================================="
        docker-compose ps
        ;;
    0)
        echo "Saliendo..."
        exit 0
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Completado"
echo ""
echo "Comandos útiles:"
echo "  ./ver_logs.sh 1    # Backend"
echo "  ./ver_logs.sh 7    # Backend en tiempo real"
echo "  ./ver_logs.sh 8    # Buscar errores 500"
echo "=========================================="

