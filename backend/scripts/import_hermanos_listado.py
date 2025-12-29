#!/usr/bin/env python3
"""Import hermanos desde ListadoHermanosMetropolitana.csv con limpieza de teléfonos.

- Limpia la tabla `hermanos` antes de importar.
- Si una celda tiene más de un número de teléfono, toma solo el primer número válido.
- Quita espacios, guiones y caracteres no numéricos.
- Normaliza a un formato E.164 aproximado (+57...).
"""
import sys
import os
import csv
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models import Hermano
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

CSV_FILENAME = "ListadoHermanosMetropolitana.csv"


def extract_primary_phone(raw_phone: str) -> str | None:
    """Extrae el primer número de teléfono válido de una celda.

    - Separa por espacios, comas, guiones, slash, punto y punto y coma.
    - Devuelve la primera secuencia de dígitos con longitud >= 7.
    """
    if not raw_phone:
        return None

    # Normalizar a str y quitar espacios extremos
    raw_phone = str(raw_phone).strip()
    if not raw_phone:
        return None

    # Reemplazar separadores comunes por espacio
    cleaned = re.sub(r"[,/;|]+", " ", raw_phone)

    # Partir en fragmentos
    candidates = []
    for part in cleaned.split():
        digits = re.sub(r"\D", "", part)
        if len(digits) >= 7:
            candidates.append(digits)

    if not candidates:
        # Como fallback, tomar todos los dígitos de la celda
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) >= 7:
            candidates.append(digits)

    if not candidates:
        return None

    return candidates[0]


def to_e164_colombia(digits: str) -> str | None:
    """Convierte una cadena de dígitos a un formato E.164 aproximado para Colombia.

    Reglas simples:
    - 10 dígitos: se asume celular colombiano -> +57XXXXXXXXXX
    - 7 dígitos: se asume fijo Pereira -> +576XXXXXXXX
    - 8-12 dígitos: se antepone + si no lo tiene (ya incluye país/ciudad)
    """
    if not digits:
        return None

    digits = re.sub(r"\D", "", digits)
    if not digits:
        return None

    n = len(digits)

    if n == 10:
        # Celular Colombia
        digits = "57" + digits
    elif n == 7:
        # Fijo Pereira
        digits = "576" + digits
    # Para otros largos, asumimos que ya incluyen indicativos

    if not digits.startswith("+"):
        digits = "+" + digits

    return digits


def import_hermanos_from_listado(clear_first: bool = True):
    db = SessionLocal()

    try:
        csv_path = os.path.join(os.path.dirname(__file__), "..", CSV_FILENAME)
        if not os.path.exists(csv_path):
            # Intentar en /app (dentro del contenedor)
            alt_path = os.path.join("/app", CSV_FILENAME)
            if os.path.exists(alt_path):
                csv_path = alt_path
            else:
                logger.error(f"CSV file not found: {csv_path} ni {alt_path}")
                return

        logger.info(f"Reading CSV file: {csv_path}")

        if clear_first:
            logger.warning("LIMPIANDO tabla hermanos...")
            db.query(Hermano).delete()
            db.commit()
            logger.info("Tabla hermanos limpiada")

        imported = 0
        skipped = 0
        errors = 0

        # Muchos archivos de Excel/Windows vienen en latin-1/ANSI, no en UTF-8.
        # Usamos latin-1 para evitar errores de decodificación y conservar caracteres.
        with open(csv_path, "r", encoding="latin-1") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    nombre = (row.get("NOMBRE") or "").strip()
                    congregacion = (row.get("CONGREGACION") or "").strip()
                    telefono_raw = (row.get("TELEFONO") or "").strip()

                    if not nombre:
                        logger.warning(f"Fila sin nombre, se omite: {row}")
                        skipped += 1
                        continue

                    primary_digits = extract_primary_phone(telefono_raw)
                    if not primary_digits:
                        logger.warning(f"Teléfono inválido para {nombre}: '{telefono_raw}'")
                        skipped += 1
                        continue

                    telefono_norm = to_e164_colombia(primary_digits)
                    if not telefono_norm:
                        logger.warning(f"No se pudo normalizar teléfono para {nombre}: '{telefono_raw}'")
                        skipped += 1
                        continue

                    # Truncar a 50 caracteres por seguridad
                    if len(telefono_norm) > 50:
                        telefono_norm = telefono_norm[:50]

                    # Evitar duplicados por teléfono
                    existing = db.query(Hermano).filter(Hermano.telefono == telefono_norm).first()
                    if existing:
                        logger.debug(f"Hermano ya existe con teléfono {telefono_norm}: {existing.nombre}")
                        skipped += 1
                        continue

                    h = Hermano(
                        nombre=nombre,
                        congregacion=congregacion or None,
                        telefono=telefono_norm,
                        is_active=True,
                    )
                    db.add(h)
                    imported += 1

                    if imported % 100 == 0:
                        logger.info(f"Importados {imported} hermanos...")
                        db.commit()

                except Exception as e:
                    logger.error(f"Error importando hermano '{row}': {e}")
                    errors += 1
                    db.rollback()
                    continue

        db.commit()

        logger.info("=" * 60)
        logger.info("✓ Importación de ListadoHermanosMetropolitana completada")
        logger.info(f"  Importados: {imported}")
        logger.info(f"  Omitidos: {skipped}")
        logger.info(f"  Errores: {errors}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error durante la importación: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Iniciando importación desde ListadoHermanosMetropolitana.csv...")
    import_hermanos_from_listado(clear_first=True)
    logger.info("Importación finalizada")

{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}