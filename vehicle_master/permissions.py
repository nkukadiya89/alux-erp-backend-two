from rest_framework.permissions import BasePermission

_VIEW_ACTIONS = frozenset(
    ["list", "retrieve", "get_vehicle_type_by_vehicle", "get_vehicle_by_party", "get_vehicle_by_type", "dropdown", "archive_list"]
)

_POST_ACTIONS = frozenset(
    ["create", "unarchive", "bulk_archive", "bulk_restore"]
)

_ACTION_PERM_MAP = {
    "create": "vehicle_master.add_vehiclemaster",
    "update": "vehicle_master.change_vehiclemaster",
    "partial_update": "vehicle_master.change_vehiclemaster",
    "destroy": "vehicle_master.delete_vehiclemaster",
}

class VehicleMasterPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if view.action in _VIEW_ACTIONS:
            return user.has_perm("vehicle_master.view_vehiclemaster")

        if view.action in _POST_ACTIONS:
            return user.has_perm("vehicle_master.add_vehiclemaster")

        perm = _ACTION_PERM_MAP.get(view.action)
        if perm:
            return user.has_perm(perm)

        return False
