import logging
from .models import VehicleMaster

logger = logging.getLogger("file")

def get_vehicles_by_party(party_id: int):
    return (
        VehicleMaster.objects.filter(party_name_id=party_id, deleted=False)
        .only("id", "vehicle_no")
        .order_by("vehicle_no")
    )


def get_vehicles_by_type(vehicle_type_id: int):
    return (
        VehicleMaster.objects.filter(vehicle_type_id=vehicle_type_id, deleted=False)
        .only("id", "vehicle_no")
        .order_by("vehicle_no")
    )


def get_vehicle_detail(pk) -> VehicleMaster:
    return (
        VehicleMaster.objects.select_related("vehicle_type", "party_name")
        .get(pk=pk, deleted=False)
    )


def serialize_vehicle_no(vehicle_no: str | None) -> str:
    return vehicle_no.strip() if vehicle_no else "No Vehicle Number"
