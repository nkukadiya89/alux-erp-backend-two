# Gate Pass Module – Coding Standards Compliance

Checklist against ERP global API standards, database & query optimization, API design, and validation rules.

---

## STEP 1 – Global ERP Standards

| Requirement | Status | Notes |
|-------------|--------|--------|
| **UUID primary key** | ✅ | `GatePass.id`, `GatePassItem.id` are UUIDField. |
| **Soft delete (is_archived)** | ✅ | `is_archived` on GatePass; DELETE sets deleted=True + is_archived=True. |
| **Audit fields** | ✅ | created_at, created_by, updated_at, updated_by; GatePassItem has created_at. |
| **Pagination in list APIs** | ✅ | Main list, archived list, import-logs use Pagination. |
| **Search & filtering** | ✅ | filterset_fields: type, status, vehicle_no, gate_pass_no, po_id, party_name; date_from/date_to in get_queryset; search_fields. |
| **Consistent response structure** | ✅ | `{"success": true, "data": ...}`; errors: `{"success": false, "message": "..."}`. |
| **Permission classes** | ✅ | IsAuthenticated, IsGatePassCreatorOrReadOnly. |
| **transaction.atomic for write APIs** | ✅ | create, update, destroy, bulk_archive, bulk_restore, submit, mark_in_process, mark_returned. |
| **Service-layer business logic** | ✅ | create_gate_pass, update_gate_pass, submit_gate_pass, mark_* in services.py. |
| **No business logic in views** | ✅ | Views delegate to serializers/services; thin views. |
| **Indexes** | ✅ | gate_pass_no, status, date, type, po_id, party_name, vehicle_no, (deleted, is_archived). |
| **select_related / prefetch_related** | ✅ | select_related("created_by", "updated_by"); prefetch_related("items"); annotate(items_count). |
| **No .all() in production** | ✅ | queryset = GatePass.objects.filter(deleted=False).order_by(...); get_queryset applies filters. |

---

## STEP 2 – Models

| Requirement | Status | Notes |
|-------------|--------|--------|
| **GatePass: id, gate_pass_no, date, type, po_id, party_name, vehicle_no, remarks, status, is_archived, audit** | ✅ | All present. |
| **GatePassItem: id, gate_pass FK, description, unit, qty, purpose, audit** | ✅ | created_at on GatePassItem. |
| **Unique constraint gate_pass_no** | ✅ | unique=True on field. |
| **Qty > 0** | ✅ | MinValueValidator(Decimal("0.0001")) on GatePassItem.qty; serializer validate_qty. |
| **At least one item** | ✅ | Serializer and service validate. |
| **Prevent edit if status = CLOSED** | ✅ | update_gate_pass and serializer validate. |
| **RETURNABLE lifecycle** | ✅ | PENDING → IN_PROCESS → CLOSED via submit, mark-in-process, mark-returned. |
| **NON_RETURNABLE auto CLOSED after submit** | ✅ | submit_gate_pass sets status=CLOSED for NON_RETURNABLE. |

---

## STEP 3 – Required APIs

| API | Status | Notes |
|-----|--------|--------|
| GET /api/gate-passes/ | ✅ | List with pagination, filters, search. |
| GET /api/gate-passes/{id}/ | ✅ | Retrieve. |
| POST /api/gate-passes/ | ✅ | Create; gate_pass_no auto-generated if omitted. |
| PUT/PATCH /api/gate-passes/{id}/ | ✅ | Update; CLOSED blocked. |
| DELETE /api/gate-passes/{id}/ | ✅ | Soft delete (draft only). |
| POST submit, mark-in-process, mark-returned | ✅ | Status actions. |
| GET dropdown | ✅ | Lightweight; excludes archived. |
| GET load-po-items/?po_id= | ✅ | PO item load. |
| GET {id}/print-data/ | ✅ | Print serializer. |
| POST bulk-archive, bulk-restore | ✅ | Archive only CLOSED; restore. |
| GET archived/, archived/{id}/ | ✅ | GatePassArchiveViewSet. |
| POST bulk-import, GET import-logs, GET import-errors, GET error-report/download | ✅ | bulk-import, import-logs (paginated), import-errors (pk=import_log_id), error-report/download. |

---

## STEP 4 – Filtering

List supports: date_from, date_to, type, status, vehicle_no, gate_pass_no, po_id, party_name.

---

## STEP 5 – Validation Rules

| Rule | Status |
|------|--------|
| Cannot edit CLOSED gate pass | ✅ |
| RETURNABLE: PENDING → IN_PROCESS → CLOSED | ✅ |
| NON_RETURNABLE auto CLOSED after submit | ✅ |
| Qty > 0, at least one item | ✅ |
| Prevent archive if status != CLOSED | ✅ (only CLOSED archived) |
| Archived excluded from dropdown | ✅ |
| Validate PO existence if selected | ✅ (in load_po_items when PurchaseOrder available) |

---

## STEP 6 – Performance

| Requirement | Status |
|-------------|--------|
| DB indexes | ✅ |
| select_related / prefetch_related / annotate | ✅ |
| No N+1 | ✅ |
| Structured logging | ✅ |
| No silent exception handling | ✅ |

---

## Quick Lint Commands

```bash
black gate_pass/
isort gate_pass/
flake8 gate_pass/ --max-line-length=88
```

---

## Files Touched for Compliance

- **models.py**: GatePassItem.created_at; indexes (type, deleted+is_archived).
- **services.py**: create_gate_pass validate items before create; bulk_archive only CLOSED; load_po_items PO existence check.
- **views.py**: queryset no .all(); next-number; create auto gate_pass_no; error-report/download url_path; bulk message when partial archive; archive viewset list/retrieve + Detail serializer.
- **serializers.py**: GatePassItemSerializer created_at; dropdown date/party_name; print created_by_detail.
- **migrations/0003_***: GatePassItem.created_at, GatePass index (deleted, is_archived).
- **tests**: next_number, bulk_archive only CLOSED, create without gate_pass_no.
