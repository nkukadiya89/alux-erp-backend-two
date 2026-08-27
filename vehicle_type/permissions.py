from rest_framework.permissions import BasePermission


class VehicleTypePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_vehicletype").exists()
                or user.groups.filter(permissions__codename="view_vehicletype").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_vehicletype").exists()
                or user.groups.filter(permissions__codename="add_vehicletype").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_vehicletype").exists()
                or user.groups.filter(
                    permissions__codename="change_vehicletype"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_vehicletype").exists()
                or user.groups.filter(
                    permissions__codename="delete_vehicletype"
                ).exists()
            )

        return False
