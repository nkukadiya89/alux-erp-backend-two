from rest_framework.permissions import BasePermission


class FurnaceMasterPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_furnacemaster").exists()
                or user.groups.filter(permissions__codename="view_furnacemaster").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_group_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_group_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive", "unarchive"]:
            return (
                user.user_permissions.filter(codename="add_furnacemaster").exists()
                or user.groups.filter(permissions__codename="add_furnacemaster").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_furnacemaster").exists()
                or user.groups.filter(permissions__codename="change_furnacemaster").exists()
            )
                    
        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_furnacemaster").exists()
                or user.groups.filter(
                    permissions__codename="delete_furnacemaster"
                ).exists()
            )

        return False