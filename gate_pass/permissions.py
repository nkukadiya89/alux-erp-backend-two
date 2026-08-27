from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsGatePassCreatorOrReadOnly(BasePermission):
    """
    Allow read-only access for all authenticated users.
    Write operations are restricted to creator or staff.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(obj, "created_by_id", None) == user.id:
            return True
        if user.is_staff:
            return True
        return False
