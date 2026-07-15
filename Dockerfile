FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY . .

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_super_admin.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
