import os

from celery import Celery

# Définit le module de paramètres par défaut de Django pour le programme celery.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crée l'instance de l'application Celery
app = Celery('config')

# Charge la configuration depuis les paramètres de Django.
# Le namespace='CELERY' signifie que toutes les configurations de Celery dans settings.py 
# devront commencer par 'CELERY_' (ex: CELERY_BROKER_URL).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Demande à Celery de découvrir automatiquement les tâches (les fichiers tasks.py)
# dans toutes les applications Django installées.
app.autodiscover_tasks()
