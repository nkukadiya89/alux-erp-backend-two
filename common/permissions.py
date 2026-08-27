from rest_framework.permissions import BasePermission

class PackingModePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_packingmode").exists()
                or user.groups.filter(permissions__codename="view_packingmode").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_packing_mode_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_packing_mode_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore"]:
            return (
                user.user_permissions.filter(codename="add_packingmode").exists()
                or user.groups.filter(permissions__codename="add_packingmode").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_packingmode").exists()
                or user.groups.filter(permissions__codename="change_packingmode").exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_packingmode").exists()
                or user.groups.filter(permissions__codename="delete_packingmode").exists()
            )

        return False



