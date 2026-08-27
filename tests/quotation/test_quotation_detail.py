import pytest
from django.urls import reverse
from rest_framework import status

from quotation.models import Quotation, QuotationDetail


@pytest.mark.django_db
class TestQuotationDetailViewSet:
    def test_list_quotation_details(self, authenticated_api_client):
        quote = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        # Create some test quotation_details
        QuotationDetail.objects.bulk_create(
            [
                QuotationDetail(quotation=quote, pieces=25),
                QuotationDetail(quotation=quote, pieces=26),
                QuotationDetail(quotation=quote, pieces=27),
            ]
        )

        url = reverse("quotation_detail-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_quotation_details_with_search(self, authenticated_api_client):
        quote = Quotation.objects.create(
            quotation_no="Quotation121", payment_terms="Direct payment"
        )
        # Create some test quotation_details
        QuotationDetail.objects.bulk_create(
            [
                QuotationDetail(quotation=quote, pieces=25),
                QuotationDetail(quotation=quote, pieces=27),
                QuotationDetail(quotation=quote, pieces=28),
            ]
        )

        url = reverse("quotation_detail-list") + "?search=Quotation121"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]["data"]) == 3

    def test_list_quotation_details_with_ordering(self, authenticated_api_client):
        quote = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        # Create some test quotation_details
        QuotationDetail.objects.bulk_create(
            [
                QuotationDetail(quotation=quote, pieces=25),
                QuotationDetail(quotation=quote, pieces=29),
                QuotationDetail(quotation=quote, pieces=32),
            ]
        )

        url = reverse("quotation_detail-list") + "?ordering=-pieces"
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"]["data"][0]["pieces"] == 32

    def test_create_quotation_detail(self, authenticated_api_client):
        quote = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        url = reverse("quotation_detail-list")
        data = {
            "quotation": quote.id,  # type: ignore
            "pieces": 100,
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert QuotationDetail.objects.filter(quotation=quote).exists()

    def test_update_quotation_detail(self, authenticated_api_client):
        quote = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        quotation_detail = QuotationDetail.objects.create(quotation=quote, pieces=25)
        url = reverse("quotation_detail-detail", args=[quotation_detail.id])  # type: ignore
        data = {"quotation": quote.id, "pieces": 35}  # type: ignore
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert QuotationDetail.objects.filter(quotation=quote).exists()

    def test_delete_quotation_detail(self, authenticated_api_client):
        quote = Quotation.objects.create(
            quotation_no="Quotation1", payment_terms="Direct payment"
        )
        quotation_detail = QuotationDetail.objects.create(quotation=quote, pieces=25)
        url = reverse("quotation_detail-detail", args=[quotation_detail.id])  # type: ignore
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not QuotationDetail.objects.filter(quotation=quote, deleted=0).exists()
