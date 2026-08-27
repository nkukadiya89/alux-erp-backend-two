from rest_framework.permissions import BasePermission


class TransporterPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_transporter").exists()
                or user.groups.filter(permissions__codename="view_transporter").exists()
            )

        if view.action in ["create", "unarchive"]:
            return (
                user.user_permissions.filter(codename="add_transporter").exists()
                or user.groups.filter(permissions__codename="add_transporter").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_transporter").exists()
                or user.groups.filter(
                    permissions__codename="change_transporter"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_transporter").exists()
                or user.groups.filter(
                    permissions__codename="delete_transporter"
                ).exists()
            )

        if view.action == "export_pdf":
            return user.has_perm("transporter.download_transporter_pdf_copy")

        return False
