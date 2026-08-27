import pytest
from django.urls import reverse
from rest_framework import status

from tests.model_factory.workorder_factories import (
    WorkOrderDetailFactory,
    WorkOrderFactory,
)
from workorder.models import WorkOrder, WorkOrderDetail


@pytest.mark.django_db
class TestWorkOrderDetailViewSet:
    def test_list_workorder_details(self, authenticated_api_client):
        WorkOrderDetailFactory.create_batch(3)
        url = reverse("workorder_detail-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_workorder_details_with_search(self, authenticated_api_client):
        workorder = WorkOrderFactory(workorder_no="WorkOrder121")
        # Create some test workorder_details
        WorkOrderDetailFactory(workorder=workorder)
        WorkOrderDetailFactory(workorder=workorder)
        WorkOrderDetailFactory(workorder=workorder)

        url = reverse("workorder_detail-list") + "?search=WorkOrder121"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_workorder_details_with_ordering(self, authenticated_api_client):
        # Create some test workorder_details
        WorkOrderDetailFactory(length=256)
        WorkOrderDetailFactory(length=356)
        WorkOrderDetailFactory(length=556)

        url = reverse("workorder_detail-list") + "?ordering=-length"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"]["data"][0]["length"] == 556.0

    def test_create_workorder_detail(self, authenticated_api_client):
        worder = WorkOrder.objects.create(
            workorder_no="WorkOrder1", purchase_order_no="PO_NO_001"
        )
        url = reverse("workorder_detail-list")
        data = {
            "workorder": worder.id,  # type: ignore
            "pieces": 100,
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert WorkOrderDetail.objects.filter(workorder=worder).exists()

    def test_update_workorder_detail(self, authenticated_api_client):
        workorder = WorkOrderFactory()
        workorder_detail = WorkOrderDetailFactory()
        url = reverse("workorder_detail-detail", args=[workorder_detail.id])  # type: ignore
        data = {"workorder": workorder.id, "length": 35}  # type: ignore
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert WorkOrderDetail.objects.filter(workorder=workorder).exists()

    def test_delete_workorder_detail(self, authenticated_api_client):
        workorder = WorkOrderFactory()
        workorder_detail = WorkOrderDetailFactory(workorder=workorder)
        url = reverse("workorder_detail-detail", args=[workorder_detail.id])  # type: ignore
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not WorkOrderDetail.objects.filter(
            workorder=workorder, deleted=0
        ).exists()
