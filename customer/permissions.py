from rest_framework.permissions import BasePermission


class CustomerPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive-list"]:
            return (
                user.user_permissions.filter(codename="view_customer").exists()
                or user.groups.filter(permissions__codename="view_customer").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_customer").exists()
                or user.groups.filter(permissions__codename="add_customer").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_customer").exists()
                or user.groups.filter(permissions__codename="change_customer").exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_customer").exists()
                or user.groups.filter(permissions__codename="delete_customer").exists()
            )

        return False

class CustomerTypePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_customertype").exists()
                or user.groups.filter(permissions__codename="view_customertype").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_customer_type_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_customer_type_excel_copy").exists()
            )
        
        if view.action == "export_pdf":
            return (
                user.user_permissions.filter(codename="download_customer_type_pdf_copy").exists()
                or user.groups.filter(permissions__codename="download_customer_type_pdf_copy").exists()
            )

        if view.action in ["create", "bulk_restore"]:
            return (
                user.user_permissions.filter(codename="add_customertype").exists()
                or user.groups.filter(permissions__codename="add_customertype").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_customertype").exists()
                or user.groups.filter(permissions__codename="change_customertype").exists()
            )

        if view.action in ["destroy", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="delete_customertype").exists()
                or user.groups.filter(
                    permissions__codename="delete_customertype"
                ).exists()
            )

        return False
