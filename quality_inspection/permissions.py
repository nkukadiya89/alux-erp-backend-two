from rest_framework.permissions import BasePermission


class QualityInspectionPermission(BasePermission):
   
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_qualityinspection").exists()
                or user.groups.filter(permissions__codename="view_qualityinspection").exists()
            )

        if view.action in ["create", "unarchive"]:
            return (
                user.user_permissions.filter(codename="add_qualityinspection").exists()
                or user.groups.filter(permissions__codename="add_qualityinspection").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_qualityinspection").exists()
                or user.groups.filter(
                    permissions__codename="change_qualityinspection"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_qualityinspection").exists()
                or user.groups.filter(
                    permissions__codename="delete_qualityinspection"
                ).exists()
            )

        return False
    