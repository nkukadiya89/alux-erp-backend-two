from rest_framework.permissions import BasePermission

class ReturnToVendorPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_rtv").exists()
                or user.groups.filter(permissions__codename="view_rtv").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_rtv").exists()
                or user.groups.filter(permissions__codename="add_rtv").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_rtv").exists()
                or user.groups.filter(
                    permissions__codename="change_rtv"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_rtv").exists()
                or user.groups.filter(
                    permissions__codename="delete_rtv"
                ).exists()
            )

        return False
    
    
    
