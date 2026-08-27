from rest_framework.permissions import BasePermission


class MaterialIndentPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_materialindent").exists()
                or user.groups.filter(permissions__codename="view_materialindent").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_materialindent").exists()
                or user.groups.filter(permissions__codename="add_materialindent").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_materialindent").exists()
                or user.groups.filter(
                    permissions__codename="change_materialindent"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_materialindent").exists()
                or user.groups.filter(
                    permissions__codename="delete_materialindent"
                ).exists()
            )

        return False
    

class MaterialDetailPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_materialdetail").exists()
                or user.groups.filter(permissions__codename="view_materialdetail").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_materialdetail").exists()
                or user.groups.filter(permissions__codename="add_materialdetail").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_materialdetail").exists()
                or user.groups.filter(
                    permissions__codename="change_materialdetail"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_materialdetail").exists()
                or user.groups.filter(
                    permissions__codename="delete_materialdetail"
                ).exists()
            )

        return False