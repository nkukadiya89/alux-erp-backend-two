# Gate Entry Module – ERP Standards Audit

**Module:** Gate Entry (Inward – Leci No)  
**Domain:** Aluminum Extrusion ERP  
**Audit date:** Applied per ERP global API standards.

---

## STEP 1 – Global ERP Standards Compliance

| Requirement | Status | Notes |
|-------------|--------|--------|
| UUID primary key | ⚠️ Partial | **GateEntry** uses integer PK (BaseModule); **GateEntryItem** uses UUID. Changing GateEntry to UUID would require a breaking migration. |
| Soft delete | ✅ | `deleted` (BaseModule) + **is_archived** added. |
| Audit fields | ✅ | created_at, created_by, updated_at, updated_by (BaseModule). |
| Pagination in list | ✅ | `Pagination` class; list returns paginated data. |
| Search & filtering | ✅ | search_fields, filterset_fields, date_from/date_to. |
| Consistent response format | ✅ | `{"success": true, "data": ...}`. |
| Permission classes | ✅ | IsAuthenticated. |
| transaction.atomic for write APIs | ✅ | create, update, partial_update, destroy, close, bulk_archive, bulk_restore. |
| Service-based business logic | ✅ | **services.py**: create_gate_entry, update_gate_entry, close_gate_entry, bulk_archive, bulk_restore. |
| No business logic in views | ✅ | Views delegate to services and serializers. |
| Indexes | ✅ | gate_entry_no, status, date, vendor_id, transporter_id, vehicle_no, (deleted, is_archived). |
| select_related / prefetch_related | ✅ | select_related("vendor", "transporter", "created_by", "updated_by"), prefetch_related("items"), annotate(items_count). |
| No .all() in production APIs | ✅ | Queryset uses .filter(deleted=False). |

---

## STEP 2 – Models

**GateEntry:** id (integer), gate_entry_no (unique), date, vendor (FK), driver_name, transporter (FK), driver_mobile_no, challan_no, invoice_no, vehicle_no, inward_time, outward_time, empty_vehicle_weight, status (in_company / close), **is_archived**, audit fields.  
**GateEntryItem:** id (UUID), gate_entry (FK), description (material), unit (uom), qty, purpose.

- Unique constraint on gate_entry_no: ✅  
- Prevent edit if status = close: ✅ (views + services)  
- Cannot close without outward_time and empty_vehicle_weight: ✅ (services.validate_can_close + close_gate_entry)  
- Qty > 0: ✅ (serializer + MinValueValidator on model)

---

## STEP 3 – APIs Implemented

| API | Method | URL | Status |
|-----|--------|-----|--------|
| List | GET | /api/v1/gate-entries/ | ✅ |
| Retrieve | GET | /api/v1/gate-entries/{id}/ | ✅ |
| Create | POST | /api/v1/gate-entries/ | ✅ |
| Update | PUT | /api/v1/gate-entries/{id}/ | ✅ |
| Partial update | PATCH | /api/v1/gate-entries/{id}/ | ✅ |
| Soft delete | DELETE | /api/v1/gate-entries/{id}/ | ✅ |
| Close | POST | /api/v1/gate-entries/{id}/close/ | ✅ |
| Change status | POST | /api/v1/gate-entries/{id}/change-status/ | ✅ |
| Dropdown | GET | /api/v1/gate-entries/dropdown/ | ✅ |
| Next number | GET | /api/v1/gate-entries/next-number/ | ✅ |
| Bulk archive | POST | /api/v1/gate-entries/bulk-archive/ | ✅ |
| Bulk restore | POST | /api/v1/gate-entries/bulk-restore/ | ✅ |
| Archived list | GET | /api/v1/gate-entries/archived/ | ✅ |
| Archived detail | GET | /api/v1/gate-entries/archived/{id}/ | ✅ |
| Bulk import | POST | /api/v1/gate-entries/bulk-import/ | ✅ Stub (501) |
| Import logs | GET | /api/v1/gate-entries/import-logs/ | ✅ |
| Import errors | GET | /api/v1/gate-entries/{import_log_id}/import-errors/ | ✅ |
| Error report download | GET | /api/v1/gate-entries/{import_log_id}/download-error-report/ | ✅ |

---

## STEP 4 – Filtering

List supports: **date_from**, **date_to**, **vendor**, **vehicle_no**, **status**, **gate_entry_no**, **driver_name** (filterset_fields + get_queryset for date range).

---

## STEP 5 – Validations

- Cannot close without outward_time and empty_vehicle_weight: ✅ (services + close/change-status)  
- Cannot edit/delete closed record: ✅ (update/partial_update/destroy)  
- Qty > 0: ✅  
- At least one item required: ✅ (write serializer + services)  
- Vendor must exist: ✅ (FK + serializer)  
- Archived excluded from dropdown: ✅ (dropdown filters is_archived=False)

---

## STEP 6 – Performance

- DB indexes: ✅  
- select_related('vendor', ...), prefetch_related('items'): ✅  
- N+1 avoided via annotate(items_count) and prefetch: ✅  
- Logging: ✅ (logger.exception in views, logger.info in services)  
- Structured error handling: ✅ (custom_exception, Django ValidationError → 400)

---

## Files Touched / Added

- **models.py** – Added `is_archived`, index (deleted, is_archived).  
- **migrations/0003_gateentry_is_archived.py** – New.  
- **services.py** – New (create, update, close, bulk_archive, bulk_restore, _sync_items).  
- **serializers.py** – Refactored: GateEntryDetailSerializer, GateEntryWriteSerializer (delegate to services), GateEntryListSerializer (+ is_archived), close validation (outward_time).  
- **views.py** – Service delegation, close action, bulk-archive/restore, archived viewset, filters (gate_entry_no, driver_name), prefetch, dropdown is_archived=False, import-logs/import-errors/download-error-report, ValidationError handling.  
- **routers.py** – Registered GateEntryArchiveViewSet at gate-entries/archived.  
- **permissions.py** – New (IsAuthenticatedGateEntry).  
- **admin.py** – is_archived in list_display and list_filter.  
- **tests/gate_entry/test_gate_entry.py** – New API tests.  
- **AUDIT_ERP_STANDARDS.md** – This file.

---

## Postman / Load Testing

- Add requests for: **close** (POST .../close/), **bulk-archive**, **bulk-restore**, **archived** list/detail, **import-logs**, **import-errors**, **download-error-report** using existing Gate Pass / Plant Master collection patterns.  
- Load testing: list and retrieve with prefetch/select_related; target &lt; 300 ms per request with typical page size.

---

## Bulk Import

- **bulk-import** currently returns 501 with a message. To implement: add an importer (e.g. `imports/services/gate_entry_importer.py`) following `gate_pass_importer.py`, then call it from the bulk_import action and log to ImportLog with module_name="GateEntry".
