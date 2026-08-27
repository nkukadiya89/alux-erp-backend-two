from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "cleanup-outstanding-tokens": {
        "task": "common.tasks.clean_outstanding_tokens",
        "schedule": crontab(hour=0, minute=0),  # Run at midnight every day
    },
    "logout-every-night-9pm": {
        "task": "common.tasks.logout_all_users",
        "schedule": crontab(minute="*/2"),
    },
    "update-workorderdetail-priority": {
        "task": "common.tasks.update_workorderdetail_priority",
        "schedule": crontab(minute=0),  # 1 AM daily
    },
}
