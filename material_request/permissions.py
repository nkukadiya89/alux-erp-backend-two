from rest_framework.permissions import BasePermission

class MaterialRequestPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_materialrequest").exists()
                or user.groups.filter(permissions__codename="view_materialrequest").exists()
            )

        if view.action in ["create", "unarchive"]:
            return (
                user.user_permissions.filter(codename="add_materialrequest").exists()
                or user.groups.filter(permissions__codename="add_materialrequest").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_materialrequest").exists()
                or user.groups.filter(
                    permissions__codename="change_materialrequest"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_materialrequest").exists()
                or user.groups.filter(
                    permissions__codename="delete_materialrequest"
                ).exists()
            )

        return False
    
    
    
class RequestItemPermission(BasePermission):
    

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_requestitem").exists()
                or user.groups.filter(permissions__codename="view_requestitem").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_requestitem").exists()
                or user.groups.filter(permissions__codename="add_requestitem").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_requestitem").exists()
                or user.groups.filter(
                    permissions__codename="change_requestitem"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_requestitem").exists()
                or user.groups.filter(
                    permissions__codename="delete_requestitem"
                ).exists()
            )

        return False
    