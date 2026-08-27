import json
import uuid
from collections.abc import Mapping
from datetime import datetime

from django.db.models import Model
from django.utils import timezone
from django.utils.timezone import is_aware

from msg_logger.models import LogActivity


def log_user_activity(
    user, action, module_name, description, request=None, payload=None
):
    ip_address = None
    if request:
        ip_address = request.META.get("REMOTE_ADDR")

    if hasattr(payload, "dict"):
        payload = payload.dict()
    elif hasattr(payload, "items"):
        payload = dict(payload)

    def serialize_value(value):
        if isinstance(value, datetime):
            return (
                value.isoformat()
                if is_aware(value)
                else timezone.make_aware(value).isoformat()
            )
        elif isinstance(value, Model):
            return str(value)
        elif isinstance(value, uuid.UUID):
            return str(value)
        elif hasattr(value, "name") and hasattr(value, "read"):  # File-like object
            return value.name
        elif isinstance(value, list):
            return [serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        return value

    if isinstance(payload, dict):
        payload = {k: serialize_value(v) for k, v in payload.items()}

    LogActivity.objects.create(
        action=action,
        action_by=user,
        module_name=module_name,
        discription=description,
        ip_address=ip_address,
        payload=payload,
    )


def clean_payload(data):
    if hasattr(data, "dict"):
        data = data.dict()
    elif isinstance(data, Mapping):
        data = dict(data)
    else:
        try:
            data = dict(data)
        except Exception:
            data = {}

    cleaned = {}
    for key, value in data.items():
        if hasattr(value, "name"):
            cleaned[key] = value.name
        elif isinstance(value, uuid.UUID):
            cleaned[key] = str(value)
        elif isinstance(value, str) and value.strip().startswith("{"):
            try:
                parsed_json = json.loads(value)
                cleaned[key] = parsed_json
            except json.JSONDecodeError:
                cleaned[key] = value
        else:
            cleaned[key] = value

    return cleaned
