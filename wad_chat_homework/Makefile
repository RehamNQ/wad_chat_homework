.PHONY: install up down migrate run zip

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

migrate:
	. .venv/bin/activate && alembic upgrade head

run:
	. .venv/bin/activate && uvicorn app.main:app --reload

zip:
	cd .. && zip -r wad_chat_homework_submission.zip wad_chat_homework
