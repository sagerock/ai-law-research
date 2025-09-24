.PHONY: help setup dev stop clean test deploy logs

help:
	@echo "Legal Research Tool - Available Commands:"
	@echo "  make setup    - Initial setup with Docker Compose"
	@echo "  make dev      - Start development environment"
	@echo "  make stop     - Stop all services"
	@echo "  make clean    - Clean up containers and volumes"
	@echo "  make test     - Run tests"
	@echo "  make deploy   - Deploy to Railway"
	@echo "  make logs     - View logs"
	@echo "  make etl      - Run ETL pipeline"

setup:
	@echo "Setting up Legal Research Tool..."
	cp .env.example .env
	@echo "Please edit .env file with your API keys"
	docker-compose build
	docker-compose up -d postgres
	sleep 5
	docker-compose up -d

dev:
	docker-compose up -d
	@echo "Services starting..."
	@echo "API: http://localhost:8000"
	@echo "OpenSearch: http://localhost:9200"
	@echo "OpenSearch Dashboards: http://localhost:5601"

stop:
	docker-compose down

clean:
	docker-compose down -v
	rm -rf postgres_data opensearch_data redis_data

test:
	docker-compose exec backend pytest

deploy:
	@echo "Deploying to Railway..."
	railway up

logs:
	docker-compose logs -f

etl:
	docker-compose run worker python etl.py

download-bulk:
	./scripts/download_bulk.sh

import-bulk:
	docker-compose run -e DATA_DIR=/data/bulk worker python /app/scripts/initial_import.py

import-bulk-local:
	python scripts/initial_import.py

# Railway-specific commands
start:
	@if [ "$$RAILWAY_ENVIRONMENT" = "production" ]; then \
		uvicorn main:app --host 0.0.0.0 --port $$PORT; \
	else \
		uvicorn main:app --host 0.0.0.0 --port 8000 --reload; \
	fi