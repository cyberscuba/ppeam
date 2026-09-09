#!/bin/bash
set -e

echo "🔄 Iniciando aplicación..."

# Wait for database to be ready
echo "⏳ Esperando a que la BD esté lista..."
while ! pg_isready -h "${DATABASE_HOST:-postgres}" -p "${DATABASE_PORT:-5432}" -U "${POSTGRES_USER:-postgres}" > /dev/null 2>&1; do
  echo "  BD aún no está lista, esperando..."
  sleep 2
done
echo "✅ BD lista"

# Try to initialize database if tables don't exist
echo "📊 Verificando esquema de BD..."
python init_database.py || echo "⚠️ Error al inicializar, continuando..."

# Load initial data
echo "📥 Cargando exhibidores..."
python load_data.py || echo "⚠️ Error al cargar exhibidores, continuando..."

# Load hermanos from CSV
echo "👥 Cargando hermanos..."
python load_hermanos.py || echo "⚠️ Error al cargar hermanos, continuando..."

# Start uvicorn
echo "🚀 Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
