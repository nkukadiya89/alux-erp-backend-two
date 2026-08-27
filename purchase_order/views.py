from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from django.db import transaction
from common.master_views import BaseModelViewSet
from .models import (PurchaseOrder, PurchaseOrderDetail)
from .serializers import (PurchaseOrderSerializer, PurchaseOrderDetailSerializer)
from .permissions import (PurchaseOrderPermission, PurchaseOrderDetailPermission)
from common.models import ArchiveMixin

class PurchaseOrderViewSet(BaseModelViewSet, ArchiveMixin):    
    queryset = PurchaseOrder.objects.all().order_by("-id")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [PurchaseOrderPermission]
    
    search_fields = ["po_no"]
    ordering_fields = ["id", "po_no", "po_date"]

    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(created_by=request.user)

            return Response(
                {
                    "success": True,
                    "message": "PurchaseOrder Created Successfully",
                    "data" : instance.id
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

class PurchaseOrderDetailViewSet(BaseModelViewSet):
    queryset = PurchaseOrderDetail.objects.all().order_by("-id")
    serializer_class = PurchaseOrderDetailSerializer
    permission_classes = [PurchaseOrderDetailPermission]
    
    filter_backends = [] 
    search_fields = ["rate"]
    ordering_fields = ["id"]

    def get_queryset(self):
        return PurchaseOrderDetail.objects.filter(deleted=False).order_by("-id")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(created_by=request.user)

            return Response(
                {
                    "success": True,
                    "message": "PurchaseOrderDetail Created Successfully",
                    "data" : instance.id
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )