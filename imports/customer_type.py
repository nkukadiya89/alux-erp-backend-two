import csv
import io
import pandas as pd
from django.http import HttpResponse
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from customer.models import CustomerType
from rest_framework.permissions import AllowAny

class CustomerTypeSampleDownloadAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customer_type_sample.csv"'

        writer = csv.writer(response)
        writer.writerow(["Name"])

        sample_data = [
            ["Retail"],
            ["Wholesale"],
            ["Distributor"],
            ["Corporate"],
            ["Online"],
        ]

        for row in sample_data:
            writer.writerow(row)

        return response
    
class CustomerTypeBulkImportAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"success": False, "message": "File is required"}, status=status.HTTP_400_BAD_REQUEST)

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
            input_names = set()

            for index, row in enumerate(data, start=1):
                total_rows += 1
                try:
                    name = row.get("Name")

                    if pd.isna(name):
                        name = None

                    if not name or not name.strip():
                        failed_count += 1
                        row_errors.append({
                            "row_number": index,
                            "errors": [
                                {
                                    "field": "name",
                                    "message": "Name is field is Required",
                                    "value": row.get("Name")
                                }
                            ]
                        })
                        continue

                    cleaned_name = name.strip().lower()

                    if cleaned_name in input_names:
                        skipped_count += 1
                        row_errors.append({
                            "row_number": index,
                            "errors": [
                                {
                                    "field": "name",
                                    "message": "Duplicate name in file",
                                    "value": row.get("Name")
                                }
                            ]
                        })
                        continue

                    input_names.add(cleaned_name)

                except Exception as e:
                    failed_count += 1
                    row_errors.append({
                        "row_number": index,
                        "row_data": row,
                        "errors": [
                            {
                                "field": "general",
                                "message": str(e),
                                "value": None
                            }
                        ]
                    })

            if not input_names:
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

            existing_names = set(CustomerType.objects.values_list("name", flat=True))
            existing_names = {name.strip().lower() for name in existing_names}

            new_names = input_names - existing_names
            skipped_existing = input_names & existing_names

            skipped_count += len(skipped_existing)

            objects_to_create = [CustomerType(name=name.title(), created_by=request.user)for name in new_names]

            with transaction.atomic():
                CustomerType.objects.bulk_create(objects_to_create, batch_size=1000)

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