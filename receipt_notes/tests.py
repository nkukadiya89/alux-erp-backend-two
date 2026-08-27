from django.test import TestCase

from .models import GoodsReceiptNote
from .serializers import GoodsReceiptNoteSerializer


class GoodsReceiptNoteSerializerTests(TestCase):
    def test_create_with_details(self):
        payload = {
            "details": [
                {
                    "item_name": "Steel",
                    "ordered_qty": "10",
                    "accepted_qty": "10",
                }
            ]
        }

        serializer = GoodsReceiptNoteSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        grn = serializer.save()

        self.assertTrue(grn.grn_no.startswith("GRN/"))
        self.assertEqual(grn.details.count(), 1)
        self.assertEqual(grn.details.first().item_name, "Steel")
