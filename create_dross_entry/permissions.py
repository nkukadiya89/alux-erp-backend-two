from rest_framework.permissions import BasePermission


class DrossEntryPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_drossentry").exists()
                or user.groups.filter(permissions__codename="view_drossentry").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_group_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_group_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_drossentry").exists()
                or user.groups.filter(permissions__codename="add_drossentry").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_drossentry").exists()
                or user.groups.filter(permissions__codename="change_drossentry").exists()
            )
                    
        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_drossentry").exists()
                or user.groups.filter(
                    permissions__codename="delete_drossentry"
                ).exists()
            )

        return False
    
    
class DrossDetailPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_drossdetail").exists()
                or user.groups.filter(permissions__codename="view_drossdetail").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_group_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_group_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_drossdetail").exists()
                or user.groups.filter(permissions__codename="add_drossdetail").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_drossdetail").exists()
                or user.groups.filter(permissions__codename="change_drossdetail").exists()
            )
                    
        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_drossdetail").exists()
                or user.groups.filter(
                    permissions__codename="delete_drossdetail"
                ).exists()
            )

        return False