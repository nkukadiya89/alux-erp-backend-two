from rest_framework.permissions import BasePermission

class PurchaseOrderPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_purchaseorder").exists()
                or user.groups.filter(permissions__codename="view_purchaseorder").exists()
            )

        if view.action in ["create", "unarchive"]:
            return (
                user.user_permissions.filter(codename="add_purchaseorder").exists()
                or user.groups.filter(permissions__codename="add_purchaseorder").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_purchaseorder").exists()
                or user.groups.filter(
                    permissions__codename="change_purchaseorder"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_purchaseorder").exists()
                or user.groups.filter(
                    permissions__codename="delete_purchaseorder"
                ).exists()
            )

        return False
    
    
    
class PurchaseOrderDetailPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_purchaseorderitem").exists()
                or user.groups.filter(permissions__codename="view_purchaseorderitem").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_purchaseorderitem").exists()
                or user.groups.filter(permissions__codename="add_purchaseorderitem").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_purchaseorderitem").exists()
                or user.groups.filter(
                    permissions__codename="change_purchaseorderitem"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_purchaseorderitem").exists()
                or user.groups.filter(
                    permissions__codename="delete_purchaseorderitem"
                ).exists()
            )

        return False