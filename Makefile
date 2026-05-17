up:
	docker compose up

down:
	docker compose down

rebuild:
	docker compose up --build

logs:
	docker compose logs -f

flush-cache:
	docker compose exec redis redis-cli FLUSHALL

reset-db:
	docker compose down -v && docker compose up

shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

ingest:
	docker compose exec backend python -m app.ingestion.cli --file $(file)

ingest-url:
	docker compose exec backend python -m app.ingestion.cli --url $(url)
