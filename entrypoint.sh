#!/bin/sh
set -e

echo "Initialisation de l'application..."

echo "Application des migrations..."
uv run python manage.py migrate --noinput

echo "Vérification du superuser..."

if [ "${RUN_CREATE_SUPERUSER:-0}" = "1" ]; then
    uv run python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()

email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if not email or not password:
    print("DJANGO_SUPERUSER_EMAIL ou DJANGO_SUPERUSER_PASSWORD non défini.")
    print("Aucun superuser ne sera créé.")
else:
    user = User.objects.filter(email=email).first()

    if user:
        print(f"Le superuser {email} existe déjà.")
    else:
        User.objects.create_superuser(email=email, password=password)
        print(f"Superuser {email} créé.")

PY
else
    echo "Création du superuser ignorée pour ce service."
fi

echo "Démarrage du serveur..."
exec "$@"
