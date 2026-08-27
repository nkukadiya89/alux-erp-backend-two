import io
import csv
import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from die.models import DieGroup
from django.db import transaction
import logging

logger = logging.getLogger("file")

class DieGroupBulkImportAPIView(APIView):
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
            valid_data = []

            for index, row in enumerate(data, start=1):
                total_rows += 1
                try:
                    name = row.get("name")
                    description = row.get("description")

                    if pd.isna(name):
                        name = None
                    if pd.isna(description):
                        description = None

                    valid_data.append({
                        "name": name.strip(),
                        "description": description.strip() if description else None
                    })

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

            existing_names = set(DieGroup.objects.values_list("name", flat=True))
            existing_names = {name.strip().lower() for name in existing_names}

            objects_to_create = []
            for item in valid_data:
                if item["name"].lower() in existing_names:
                    skipped_count += 1
                else:
                    objects_to_create.append(
                        DieGroup(
                            name=item["name"],
                            description=item["description"],
                            created_by=request.user
                        )
                    )

            with transaction.atomic():
                DieGroup.objects.bulk_create(objects_to_create, batch_size=1000)

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
                "data": {"total_records": 0, "inserted": 0, "skipped": 0, "failed": 1,
                        "success_count": 0, "error_count": 1, "import_log_id": "",
                        "row_errors": [{"row": None, "error": str(e)}],}}, 
                    status=500)