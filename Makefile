.PHONY: help build up down logs migrate seed test clean

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make migrate  - Run database migrations"
	@echo "  make seed     - Seed database with initial data"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Remove all containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "Services started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	docker-compose down

logs:
	docker-compose logs -f

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python scripts/seed.py

test:
	docker-compose exec backend pytest

test-frontend:
	cd frontend && npm test

clean:
	docker-compose down -v
	docker system prune -f

restart:
	docker-compose restart

ps:
	docker-compose ps

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec postgres psql -U exhibidores exhibidores_db

backup:
	docker-compose exec postgres pg_dump -U exhibidores exhibidores_db > backup_$$(date +%Y%m%d_%H%M%S).sql

restore:
	@read -p "Enter backup file: " file; \
	docker-compose exec -T postgres psql -U exhibidores exhibidores_db < $$file
