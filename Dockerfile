# ==========================================
# Dockerfile: Python Vision & Feedback API
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema necessárias para compilação e Postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python necessárias para a API FastAPI e SQLAlchemy
RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    uvicorn[standard]>=0.22.0 \
    pydantic>=2.0.0 \
    sqlalchemy>=2.0.0 \
    psycopg2-binary>=2.9.9 \
    numpy>=1.24.0

# Copia código-fonte
COPY . .

# Expõe a porta 8000 da FastAPI
EXPOSE 8000

# Executa o servidor uvicorn apontando para o módulo feedback_api
CMD ["uvicorn", "src.feedback_loop.feedback_api:app", "--host", "0.0.0.0", "--port", "8000"]
