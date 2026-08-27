from rest_framework.permissions import BasePermission

class GoodsReceiptNotePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_grnheader").exists()
                or user.groups.filter(permissions__codename="view_grnheader").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_grnheader").exists()
                or user.groups.filter(permissions__codename="add_grnheader").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_grnheader").exists()
                or user.groups.filter(
                    permissions__codename="change_grnheader"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_grnheader").exists()
                or user.groups.filter(
                    permissions__codename="delete_grnheader"
                ).exists()
            )

        return False
    
    
    
class GoodsReceiptNoteDetailPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "export_pdf"]:
            return (
                user.user_permissions.filter(codename="view_grnheaderdetail").exists()
                or user.groups.filter(permissions__codename="view_grnheaderdetail").exists()
            )

        if view.action == "create":
            return (
                user.user_permissions.filter(codename="add_grnheaderdetail").exists()
                or user.groups.filter(permissions__codename="add_grnheaderdetail").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_grnheaderdetail").exists()
                or user.groups.filter(
                    permissions__codename="change_grnheaderdetail"
                ).exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_grnheaderdetail").exists()
                or user.groups.filter(
                    permissions__codename="delete_grnheaderdetail"
                ).exists()
            )

        return False