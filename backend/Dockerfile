# Imagen base con Python (compilada desde un Ubuntu server)
#FROM python:3.11-slim
FROM --platform=linux/amd64 python:3.11-slim

# Instalar dependencias básicas del sistema
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*


# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PATH="/root/.local/bin:$PATH"

# Crear directorio de la app
WORKDIR /app

# Copiar archivos de proyecto
COPY pyproject.toml uv.lock ./
COPY app ./app
# Remover el directorio .venv para eliminar posibles binarios confictivos
#RUN rm -rf .venv

# Instalar dependencias (según pyproject.toml / uv.lock)
RUN uv sync --frozen
EXPOSE 8000

# Ejecutar servidor de desarrollo
CMD ["uv", "run", "main.py"]