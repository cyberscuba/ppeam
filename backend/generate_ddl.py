#!/usr/bin/env python3
"""Generate DDL SQL from SQLAlchemy models."""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.schema import CreateTable
from app.models import Base

# Create an engine (dummy, just for DDL generation)
engine = create_engine("postgresql://user:pass@localhost/db", strategy="mock", executor=lambda sql, *_: None)

# Generate DDL
for table in Base.metadata.tables.values():
    ddl = CreateTable(table).compile(engine)
    print(f"{ddl};")
