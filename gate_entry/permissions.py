"""
Gate Entry permission classes.
Enforce authenticated access; optional creator-only write can be added here.
"""

from rest_framework import permissions


class IsAuthenticatedGateEntry(permissions.IsAuthenticated):
    """Gate Entry requires authenticated user. Extend for creator-only rules if needed."""

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_authenticated
