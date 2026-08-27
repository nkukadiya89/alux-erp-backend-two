from rest_framework.routers import DefaultRouter

from user.group_and_permission import (
    AssignPermissionGroupViewSet,
    AssignUserGroupViewSet,
    CreateGroupWithPermissionsViewSet,
    DeleteGroupWithPermissionsViewSet,
    GetAllPermissionViewSet,
    GetGroupPermissionViewSet,
    GroupViewSet,
    PermissionViewSet,
)
from user.views import (
    ChangePasswordViewSet,
    LogoutViewSet,
    UserRegistrationViewSet,
    UserViewSet,
)

user_routers = DefaultRouter()

user_routers.register(
    "register", viewset=UserRegistrationViewSet, basename="register_user"
)
user_routers.register("logout", viewset=LogoutViewSet, basename="logout_api")
user_routers.register("create-group", GroupViewSet, basename="create_new_group"),
user_routers.register("get-group", GroupViewSet, basename="list_group"),
user_routers.register(
    "assign-user-group", AssignUserGroupViewSet, basename="assign_user_group"
),
user_routers.register(
    "create-group-permissions",
    CreateGroupWithPermissionsViewSet,
    basename="create_group_with_permissions",
)
user_routers.register(
    "delete-group-permissions",
    DeleteGroupWithPermissionsViewSet,
    basename="delete_group_with_permissions",
)

# Permission
user_routers.register(
    "get-all-permission-list", GetAllPermissionViewSet, basename="list_all_permissions"
)

# Permission Releated
user_routers.register("list-permission", PermissionViewSet, basename="list_permission")
user_routers.register(
    "get-group-permission", GetGroupPermissionViewSet, basename="get_group_permission"
)
user_routers.register(
    "assign-permission-group",
    AssignPermissionGroupViewSet,
    basename="assign_permission_group",
)

user_routers.register(r"users", UserViewSet, basename="user")
user_routers.register(
    "user-password-change", ChangePasswordViewSet, basename="user_password_change"
)
