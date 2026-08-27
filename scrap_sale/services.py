"""
Business logic for Scrap Sale archive/restore.
"""

import logging
from typing import List

from django.db import transaction
from django.utils import timezone

from .models import ScrapSale

logger = logging.getLogger("file")


@transaction.atomic
def bulk_archive_scrap_sales(ids: List[str], user) -> int:
    """Set is_archived=True for given scrap sales (non-deleted)."""
    qs = ScrapSale.objects.filter(id__in=ids, deleted=False, is_archived=False)
    updated = qs.update(
        is_archived=True,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Bulk archived %s scrap sale(s) by %s", updated, user)
    return updated


@transaction.atomic
def bulk_restore_scrap_sales(ids: List[str], user) -> int:
    """Set is_archived=False for given scrap sales."""
    qs = ScrapSale.objects.filter(id__in=ids, deleted=False)
    updated = qs.update(
        is_archived=False,
        updated_by=user,
        updated_at=timezone.now(),
    )
    logger.info("Bulk restored %s scrap sale(s) by %s", updated, user)
    return updated
