# ── ETAPA 1: builder ─────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .

# Actualizar pip e instalar en /install (aislado del sistema)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── ETAPA 2: runtime ─────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copiar solo las dependencias instaladas
COPY --from=builder /install /usr/local

# Copiar código fuente
COPY app/ ./app/
COPY seed.py .

# Puerto de la aplicación
EXPOSE 8000

# Usuario sin privilegios + directorio para SQLite
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data
USER appuser

# Ruta de la BD en contenedor (sobreescribible con -e DATABASE_URL)
ENV DATABASE_URL=sqlite:////app/data/tasks.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
