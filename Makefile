.PHONY: install dev backend frontend seed test clean

install:
	cd backend && uv sync
	cd frontend && pnpm install

backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && pnpm dev

dev:
	@echo "Starting backend on :8000 and frontend on :5173"
	@(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && pnpm dev)

seed:
	cd backend && uv run python -m app.seed.demo_vessels

test:
	cd backend && uv run pytest -q

clean:
	rm -rf backend/.venv backend/.pytest_cache backend/**/__pycache__
	rm -rf frontend/node_modules frontend/dist
	rm -f backend/*.db
