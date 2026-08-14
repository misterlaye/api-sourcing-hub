# Utilisation d'une image Python légère et officielle
FROM python:3.14-slim

# Variables d'environnement pour optimiser Python dans Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Définition du répertoire de travail
WORKDIR /app

# Installer uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Installation des dépendances Python
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

# Copie du code source du projet
COPY . /app/

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# On expose le port 8000 pour Django
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
