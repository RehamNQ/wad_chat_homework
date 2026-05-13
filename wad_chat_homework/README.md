# wad_chat_homework — Setup, Run, Test, and Submission Guide

## Student
**Reham Qassem**

## Project
**wad_chat_homework**

## 1. Project summary

This project is a server-rendered FastAPI web application.

Main features:
- local registration and login with hashed passwords
- GitHub OAuth login
- JWT access token and refresh token flow
- Redis refresh sessions with 30-day TTL
- PostgreSQL database with Alembic migrations
- chat creation and stored chat history
- local GGUF model inference through `llama-cpp-python`

## 2. Main technologies

- FastAPI
- Jinja2 templates
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Authlib
- Argon2
- python-jose
- llama-cpp-python
- Docker Compose

## 3. Ubuntu prerequisites

Install the required system tools:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential cmake ninja-build pkg-config libopenblas-dev libgomp1 docker.io docker-compose-plugin zip
```

If Docker needs permission:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

## 4. Project setup

Go to the project folder:

```bash
cd /path/to/wad_chat_homework
```

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade pip tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Install the project requirements:

```bash
pip install -r requirements.txt
```

## 5. Environment file

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Open `.env` and edit the values:

```env
APP_NAME=wad_chat_homework
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
SESSION_SECRET_KEY=REPLACE_WITH_ANOTHER_LONG_RANDOM_SECRET
COOKIE_SECURE=false

DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/wad_chat_homework
REDIS_URL=redis://127.0.0.1:6379/0

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

GITHUB_CLIENT_ID=YOUR_GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET=YOUR_GITHUB_CLIENT_SECRET

MODEL_PATH=/home/tharaa/Desktop/Riham/qwen.gguf
LLM_CTX_SIZE=1024
LLM_THREADS=4
LLM_MAX_TOKENS=256
LLM_TEMPERATURE=0.2
LLM_PRELOAD_ON_STARTUP=true

ALLOW_DEV_LLM_FALLBACK=false
```

Generate the secret keys with:

```bash
python3 - <<'PY'
import secrets
print("SECRET_KEY=" + secrets.token_urlsafe(48))
print("SESSION_SECRET_KEY=" + secrets.token_urlsafe(48))
PY
```

## 6. GGUF model file

The model file is **not included** in the repository.

The application expects the local GGUF file through the `MODEL_PATH` environment variable.

Example:

```env
MODEL_PATH=/home/tharaa/Desktop/Riham/qwen.gguf
```

If the model file does not exist, the application should fail clearly on startup.

## 7. GitHub OAuth setup

Create a GitHub OAuth app and use these values:

- Homepage URL: `http://127.0.0.1:8000`
- Authorization callback URL: `http://127.0.0.1:8000/auth/github/callback`

Then place the real values into `.env`:

```env
GITHUB_CLIENT_ID=YOUR_REAL_CLIENT_ID
GITHUB_CLIENT_SECRET=YOUR_REAL_CLIENT_SECRET
```

## 8. Start PostgreSQL and Redis

From the project folder:

```bash
docker compose up -d
docker compose ps
```

## 9. Run Alembic migrations

```bash
python -m alembic upgrade head
```

## 10. Start the application

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open in the browser:

```text
http://127.0.0.1:8000
```

## 11. Evidence commands

### PostgreSQL schema
```bash
docker exec -it wad_chat_homework_postgres psql -P pager=off -U postgres -d wad_chat_homework -c "\\dt"
docker exec -it wad_chat_homework_postgres psql -P pager=off -U postgres -d wad_chat_homework -c "\\d users"
docker exec -it wad_chat_homework_postgres psql -P pager=off -U postgres -d wad_chat_homework -c "\\d chats"
docker exec -it wad_chat_homework_postgres psql -P pager=off -U postgres -d wad_chat_homework -c "\\d messages"
docker exec -it wad_chat_homework_postgres psql -P pager=off -U postgres -d wad_chat_homework -c "\\d oauth_identities"
```

### PostgreSQL stored messages
```bash
docker exec -it wad_chat_homework_postgres psql -P pager=off -U postgres -d wad_chat_homework -c "SELECT id, chat_id, role, LEFT(content, 80) FROM messages ORDER BY id;"
```

### Redis refresh session
```bash
docker exec -it wad_chat_homework_redis redis-cli --scan --pattern 'refresh_session:*'
docker exec -it wad_chat_homework_redis redis-cli TTL refresh_session:PASTE_REAL_KEY_HERE
docker exec -it wad_chat_homework_redis redis-cli GET refresh_session:PASTE_REAL_KEY_HERE
```

