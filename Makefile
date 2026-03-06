.PHONY: help setup install run-backend run-frontend run-dashboard run-all stop clean test lint

help:
	@echo "TestTrack Pro - Available Commands"
	@echo "===================================="
	@echo "make setup          - Initial setup"
	@echo "make install        - Install all dependencies"
	@echo "make run-backend    - Run backend API"
	@echo "make run-frontend   - Run frontend"
	@echo "make run-dashboard  - Run Streamlit dashboard"
	@echo "make run-all        - Run all services with Docker Compose"
	@echo "make stop           - Stop all Docker services"
	@echo "make clean          - Clean up build artifacts and cache"
	@echo "make test           - Run tests"
	@echo "make lint           - Run linters"

setup:
	cp .env.example .env
	@echo "Setup complete! Update .env with your settings."

install:
	cd backend && pip install -r requirements.txt
	cd ../frontend && npm install
	cd ../dashboard && pip install -r requirements.txt

run-backend:
	cd backend && python app/main.py

run-frontend:
	cd frontend && npm run dev

run-dashboard:
	cd dashboard && streamlit run app.py

run-all:
	docker-compose up --build

stop:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf frontend/dist
	rm -rf backend/build
	rm -rf .pytest_cache

test:
	cd backend && pytest

lint:
	cd backend && flake8 app
	cd ../frontend && npm run lint
