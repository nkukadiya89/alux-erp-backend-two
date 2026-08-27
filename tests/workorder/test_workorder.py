import pytest
from django.urls import reverse
from rest_framework import status

from tests.model_factory.workorder_factories import WorkOrderFactory
from workorder.models import WorkOrder


@pytest.mark.django_db
class TestWorkOrderViewSet:
    def test_list_workorders(self, authenticated_api_client):
        # Create some test workorders
        WorkOrderFactory.create_batch(3)
        url = reverse("workorder-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_workorders_with_search(self, authenticated_api_client):
        # Create some test workorders
        WorkOrderFactory(workorder_no="WorkOrder1")
        WorkOrderFactory(workorder_no="WorkOrder2")
        WorkOrderFactory(workorder_no="WorkOrder3")

        url = reverse("workorder-list") + "?search=WorkOrder1"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 1

    def test_list_workorders_with_ordering(self, authenticated_api_client):
        # Create some test workorders
        WorkOrderFactory(workorder_no="WorkOrder1")
        WorkOrderFactory(workorder_no="WorkOrder2")
        WorkOrderFactory(workorder_no="WorkOrder3")

        url = reverse("workorder-list") + "?ordering=-workorder_no"
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"]["data"][0]["workorder_no"] == "WorkOrder3"

    def test_create_workorder(self, authenticated_api_client):
        url = reverse("workorder-list")
        data = {
            "workorder_no": "WorkOrder4",
            "purchase_order_no": "PO_NO_001",
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert WorkOrder.objects.filter(workorder_no="WorkOrder4").exists()

    def test_update_workorder(self, authenticated_api_client):
        workorder = WorkOrderFactory(
            workorder_no="WorkOrder1", purchase_order_no="PO_NO_001"
        )
        url = reverse("workorder-detail", args=[workorder.id])  # type: ignore
        data = {
            "workorder_no": "WorkOrder1 Updated",
            "purchase_order_no_id": "PO_NO_001",
        }
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert WorkOrder.objects.filter(workorder_no="WorkOrder1 Updated").exists()

    def test_delete_workorder(self, authenticated_api_client):
        workorder = WorkOrderFactory(
            workorder_no="WorkOrder1", purchase_order_no="PO_NO_001"
        )
        url = reverse("workorder-detail", args=[workorder.id])  # type: ignore
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not WorkOrder.objects.filter(
            workorder_no="WorkOrder1", deleted=0
        ).exists()
