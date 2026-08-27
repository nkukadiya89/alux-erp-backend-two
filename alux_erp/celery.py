import os

from celery import Celery

from alux_erp import celery_config

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alux_erp.settings")

app = Celery("alux_erp")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.beat_schedule = celery_config.CELERY_BEAT_SCHEDULE

app.autodiscover_tasks()
