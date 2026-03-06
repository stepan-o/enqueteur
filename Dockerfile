FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY backend /app/backend
COPY scripts /app/scripts
COPY docs /app/docs

RUN pip install --no-cache-dir -e .[dev]

CMD ["python", "-m", "pytest", "backend/sim4/tests", "-q"]
