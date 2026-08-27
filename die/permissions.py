from rest_framework.permissions import BasePermission


class DieGroupPermission(BasePermission):
   
    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_diegroup").exists()
                or user.groups.filter(permissions__codename="view_diegroup").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_group_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_group_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_diegroup").exists()
                or user.groups.filter(permissions__codename="add_diegroup").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_diegroup").exists()
                or user.groups.filter(permissions__codename="change_diegroup").exists()
            )
                    
        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_diegroup").exists()
                or user.groups.filter(
                    permissions__codename="delete_diegroup"
                ).exists()
            )

        return False


class SectionCategoriesPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_diecategory").exists()
                or user.groups.filter(permissions__codename="view_diecategory").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_category_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_category_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_diecategory").exists()
                or user.groups.filter(permissions__codename="add_diecategory").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_diecategory").exists()
                or user.groups.filter(permissions__codename="change_diecategory").exists()
            )

        if view.action in ["destroy", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="delete_diecategory").exists()
                or user.groups.filter(permissions__codename="delete_diecategory").exists()
            )

        return False


class SectionSubCategoriesPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_diesubcategory").exists()
                or user.groups.filter(permissions__codename="view_diesubcategory").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_sub_category_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_sub_category_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_diesubcategory").exists()
                or user.groups.filter(permissions__codename="add_diesubcategory").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_diesubcategory").exists()
                or user.groups.filter(permissions__codename="change_diesubcategory").exists()
            )

        if view.action in ["destroy", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="delete_diesubcategory").exists()
                or user.groups.filter(permissions__codename="delete_diesubcategory").exists()
            )

        return False


    
class DieSizePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_diesize").exists()
                or user.groups.filter(permissions__codename="view_diesize").exists()
            )
        
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_size_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_size_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_diesize").exists()
                or user.groups.filter(permissions__codename="add_diesize").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_diesize").exists()
                or user.groups.filter(permissions__codename="change_diesize").exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_section").exists()
                or user.groups.filter(
                    permissions__codename="delete_diesize"
                ).exists()
            )

        return False
    

class SectionPressPermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if view.action in ["list", "retrieve"]:
            return (
                user.user_permissions.filter(codename="view_diepress").exists()
                or user.groups.filter(permissions__codename="view_diepress").exists()
            )
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_profile_press_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_profile_press_excel_copy").exists()
            )
        
        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_diepress").exists()
                or user.groups.filter(permissions__codename="add_diepress").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_diepress").exists()
                or user.groups.filter(permissions__codename="change_diepress").exists()
            )

        if view.action == "destroy":
            return (
                user.user_permissions.filter(codename="delete_diepress").exists()
                or user.groups.filter(permissions__codename="delete_diepress").exists()
            )

        return False


class DiePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        
        if not user or not user.is_authenticated:
            return False

        if view.action in ["list", "retrieve", "archive_list"]:
            return (
                user.user_permissions.filter(codename="view_die").exists()
                or user.groups.filter(permissions__codename="view_die").exists()
            )
    
        if view.action == "export_excel":
            return (
                user.user_permissions.filter(codename="download_die_excel_copy").exists()
                or user.groups.filter(permissions__codename="download_die_excel_copy").exists()
            )

        if view.action in ["create", "bulk_restore", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="add_die").exists()
                or user.groups.filter(permissions__codename="add_die").exists()
            )

        if view.action in ["update", "partial_update"]:
            return (
                user.user_permissions.filter(codename="change_die").exists()
                or user.groups.filter(permissions__codename="change_die").exists()
            )

        if view.action in ["destroy", "bulk_archive"]:
            return (
                user.user_permissions.filter(codename="delete_die").exists()
                or user.groups.filter(permissions__codename="delete_die").exists()
            )

        return False


