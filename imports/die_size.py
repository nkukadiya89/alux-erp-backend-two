import csv
import io
import pandas as pd
from decimal import Decimal
from django.db import transaction
from die.models import DieSize
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

class DieSizeBulkImportAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"success": False, "message": "File is required"}, status=400)

        try:
            if file.name.endswith(".csv"):
                decoded_file = file.read().decode("utf-8-sig")
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                data = list(reader)

            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file)
                data = df.to_dict(orient="records")

            else:
                return Response({
                    "success": False,
                    "message": "Only CSV or Excel (.xlsx) file allowed"
                }, status=400)

            total_rows = 0
            inserted_count = 0
            skipped_count = 0
            failed_count = 0

            row_errors = []
            valid_data = set()

            for index, row in enumerate(data, start=1):
                total_rows += 1
                try:
                    thickness = row.get("Die Thickness")
                    diameter = row.get("Die Diameter")

                    if pd.isna(thickness):
                        thickness = None
                    if pd.isna(diameter):
                        diameter = None

                    if not thickness or not diameter or str(thickness).strip() == "" or str(diameter).strip() == "":
                        failed_count += 1
                        row_errors.append({"row": index, "error": "Thickness or Diameter missing"})
                        continue

                    try:
                        thickness_val = Decimal(thickness)
                        diameter_val = Decimal(diameter)
                    except Exception:
                        failed_count += 1
                        row_errors.append({"row": index, "error": "Invalid decimal value"})
                        continue

                    key = (thickness_val, diameter_val)

                    if key in valid_data:
                        skipped_count += 1
                        row_errors.append({"row": index, "error": "Duplicate in file"})
                        continue

                    valid_data.add(key)

                except Exception as e:
                    failed_count += 1
                    row_errors.append({"row": index, "error": str(e)})

            if not valid_data:
                return Response({
                    "success": False,
                    "message": "No valid data found",
                    "data": {
                        "total_records": total_rows,
                        "inserted": 0,
                        "skipped": skipped_count,
                        "failed": failed_count,
                        "success_count": 0,
                        "error_count": failed_count,
                        "import_log_id": "",
                        "row_errors": row_errors,
                    }
                }, status=400)

            existing = set(DieSize.objects.values_list("thickness", "diameter"))

            new_records = valid_data - existing
            skipped_existing = valid_data & existing

            skipped_count += len(skipped_existing)

            objects_to_create = [
                DieSize(thickness=h, diameter=w, created_by=request.user)
                for (h, w) in new_records
            ]

            with transaction.atomic():
                DieSize.objects.bulk_create(objects_to_create, batch_size=1000)

            inserted_count = len(objects_to_create)

            message_parts = []
            if inserted_count:
                message_parts.append(f"{inserted_count} inserted")
            if skipped_count:
                message_parts.append(f"{skipped_count} skipped")
            if failed_count:
                message_parts.append(f"{failed_count} failed")

            return Response({
                "success": bool(inserted_count or skipped_count),
                "message": " | ".join(message_parts) if message_parts else "No records processed",
                "data": {
                    "total_records": total_rows,
                    "inserted": inserted_count,
                    "skipped": skipped_count,
                    "failed": failed_count,
                    "success_count": inserted_count,
                    "error_count": failed_count,
                    "import_log_id": "",
                    "row_errors": row_errors,
                }
            }, status=200)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Something went wrong",
                "data": {
                    "total_records": 0,
                    "inserted": 0,
                    "skipped": 0,
                    "failed": 1,
                    "success_count": 0,
                    "error_count": 1,
                    "import_log_id": "",
                    "row_errors": [
                        {"row": None, "error": str(e)}
                    ],
                }
            }, status=500)