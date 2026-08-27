from rest_framework.permissions import BasePermission


class ShiftMasterPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve"]:
            return (
                user.user_permissions.filter(codename="view_shiftmaster").exists()
                or user.groups.filter(permissions__codename="view_shiftmaster").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_shiftmaster").exists()
                or user.groups.filter(permissions__codename="add_shiftmaster").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_shiftmaster").exists()
                or user.groups.filter(
                    permissions__codename="change_shiftmaster"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_shiftmaster").exists()
                or user.groups.filter(
                    permissions__codename="delete_shiftmaster"
                ).exists()
            )

        return False
