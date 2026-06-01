.PHONY: run stop build logs db-shell test lint

run:
	docker-compose up -d

stop:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

db-shell:
	docker exec -it styleforge_db psql -U styleforge_user -d styleforge_db

test:
	pytest

lint:
	flake8 .
	black .
