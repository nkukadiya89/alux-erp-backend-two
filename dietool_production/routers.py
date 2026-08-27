from rest_framework.routers import DefaultRouter
from .views import (
    ActivityMasterViewSet,
    AnalysisMethodViewSet,
    CorrectionTypeViewSet, 
    DieProductionLogViewSet, 
    DieMaintenanceLogViewSet, 
    DieNitridingBatchViewSet,
    DieNitridingBatchDetailViewSet,
    DieTrialLogViewSet, 
    MaintananceTypeViewSet, 
    CorrectionHistoryViewSet, 
    DieFailureLogViewSet,
    ReasonForCorrectionViewSet,
    CorrectionInspectionTypeViewSet,
    ReasonForMaintenanceViewSet
)

dieproductionlog_routers = DefaultRouter()
dieproductionlog_routers.register(
    "die-tool-production", viewset=DieProductionLogViewSet, basename="dieproductionlog")

dieproductionlog_routers.register(
    "die-maintanance-log", viewset=DieMaintenanceLogViewSet, basename="diemaintanancelog")

dieproductionlog_routers.register(
    "die-nitriding-batch", viewset=DieNitridingBatchViewSet, basename="dienitridingbatch")

dieproductionlog_routers.register(
    "die-nitriding-batch-detail", viewset=DieNitridingBatchDetailViewSet, basename="dienitridingbatchdetail")

dieproductionlog_routers.register(
    "die-trial-log", viewset=DieTrialLogViewSet, basename="dietriallog"
)
dieproductionlog_routers.register(
    "die-maintanance-type", viewset=MaintananceTypeViewSet, basename="diemaintanancetype"
)
dieproductionlog_routers.register(
    "reason-for-correction", viewset=ReasonForCorrectionViewSet, basename="diereasonforcorrection"
)
dieproductionlog_routers.register(
    "correction-inspection-type", viewset=CorrectionInspectionTypeViewSet, basename="diecorrectioninspectiontype"
)
dieproductionlog_routers.register(
    "die-correction-type", viewset=CorrectionTypeViewSet, basename="diecorrectiontype"
)
dieproductionlog_routers.register(
    "die-correction-activity", viewset=ActivityMasterViewSet, basename="diecorrectioncategory"
)
dieproductionlog_routers.register(
    "die-correction-log", viewset=CorrectionHistoryViewSet, basename="diecorrectionhistory"
)
dieproductionlog_routers.register(
    "die-analysis-method", viewset=AnalysisMethodViewSet, basename="diecorrectionmaster"
)
dieproductionlog_routers.register(
    "die-failure-log", viewset=DieFailureLogViewSet, basename="diefailurelog"  
)
dieproductionlog_routers.register(
    "reason-for-maintenance", viewset=ReasonForMaintenanceViewSet, basename="diereasonformaintenance"
)

