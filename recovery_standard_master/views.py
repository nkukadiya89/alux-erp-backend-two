from rest_framework.response import Response
from rest_framework import status
from common.master_views import BaseModelViewSet
from .models import RecoveryStandardMaster
from .serializers import RecoveryStandardMasterSerializers
from .permissions import RecoveryStandardMasterPermission


class RecoveryStandardMasterViewSet(BaseModelViewSet):
    queryset = RecoveryStandardMaster.objects.all()
    serializer_class = RecoveryStandardMasterSerializers
    permission_classes = [RecoveryStandardMasterPermission]
    
    serching_fields = (
          BaseModelViewSet.serching_fields + [
             "furnace_type",
             "material_type",
         ]
     )

    ordering_fields = (
          BaseModelViewSet.ordering_fields + [
            "id",
            "furnace_type",
            "material_type",
        ]
     )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            {
                "success": True,
                "message": "RecoveryStandardMaster Created Successfully",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(
            {
                "success": True,
                "message": "RecoveryStandardMaster Updated Successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
