import pytest
from django.urls import reverse
from rest_framework import status

from quotation.models import Quotation
from tests.model_factory.quotation_factories import QuotationFactory


@pytest.mark.django_db
class TestQuotationViewSet:
    def test_list_quotations(self, authenticated_api_client):
        # Create some test quotations
        QuotationFactory.create_batch(3)
        url = reverse("quotation-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_quotations_with_search(self, authenticated_api_client):
        # Create some test quotations
        QuotationFactory(quotation_no="Quotation1")
        QuotationFactory.create_batch(2)
        url = reverse("quotation-list") + "?search=Quotation1"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 1

    def test_list_quotations_with_ordering(self, authenticated_api_client):
        # Create some test quotations
        QuotationFactory(quotation_no="Quotation1")
        QuotationFactory(quotation_no="Quotation2")
        QuotationFactory(quotation_no="Quotation3")

        url = reverse("quotation-list") + "?ordering=-quotation_no"
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"]["data"][0]["quotation_no"] == "Quotation3"

    def test_create_quotation(self, authenticated_api_client):
        url = reverse("quotation-list")
        data = {
            "quotation_no": "Quotation4",
            "payment_terms": "Direct payment",
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Quotation.objects.filter(quotation_no="Quotation4").exists()

    def test_update_quotation(self, authenticated_api_client):
        quotation = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        url = reverse("quotation-detail", args=[quotation.id])  # type: ignore
        data = {
            "quotation_no": "Quotation1 Updated",
            "payment_terms_id": "Direct payment",
        }
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert Quotation.objects.filter(quotation_no="Quotation1 Updated").exists()

    def test_delete_quotation(self, authenticated_api_client):
        quotation = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        url = reverse("quotation-detail", args=[quotation.id])  # type: ignore
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Quotation.objects.filter(
            quotation_no="Quotation1", deleted=0
        ).exists()
