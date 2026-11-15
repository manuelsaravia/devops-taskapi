# ---------- Etapa 1: builder (instala dependencias) ----------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: runtime (imagen final liviana) ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:///./data/tasks.db

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
