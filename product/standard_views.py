from product.models import StandardMaster
from product.serializers import StandardMasterSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from utils.pagination import Pagination

class StandardMasterViewSet(viewsets.ModelViewSet):
    queryset = StandardMaster.objects.all()
    serializer_class = StandardMasterSerializer
    pagination_class = Pagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        try:
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = self.get_serializer(queryset, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        except Exception as e:
            return custom_exception(e)