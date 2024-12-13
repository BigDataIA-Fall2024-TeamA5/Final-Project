# Stage 1: Build
FROM python:3.12-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main
# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/poetry /usr/local/bin/poetry
COPY . .
RUN useradd -m appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]