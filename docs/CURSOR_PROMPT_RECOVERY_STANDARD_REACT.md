# Cursor prompt: Recovery Standard APIs in React + Antd (minimal token)

Use in your **React + Ant Design frontend** project. Paste into Cursor chat.

---

**Short prompt (copy-paste):**

```
Integrate all Recovery Standard APIs in React+Antd. Mirror the Furnace module exactly.

Base: /api/v1/recovery-standard/ (GET list, POST create, GET/PUT/PATCH/DELETE :id, POST :id/change-status, GET dropdown, POST bulk-archive, POST bulk-restore, POST bulk-import, GET import-logs, GET :import_log_id/import-errors, GET :import_log_id/error-report/download, GET archived, GET :id/archived). Also GET /api/v1/recovery-standard-archive/ for archive list.

Auth: Bearer token. Response: { success, data?, message? }. List pagination: page, pagesize, search, ordering, filters: furnace_type, material_type, status.

Payload: furnace_type (id), material_type (id), min_recovery, max_recovery, standard_loss, effective_from?, status, remarks?. Dropdowns: furnace-type (GET), material-types (GET).

Do: list table + filters, add/edit form, dropdown usage, bulk archive/restore, change-status, bulk import + import logs + error report, archived list. Reuse Furnace folder/service/table/form pattern; only change endpoint and field names to recovery-standard and recovery standard fields.
```

---

**One-liner (max short):**

```
Add Recovery Standard UI: same as Furnace (list/form/dropdown/bulk-archive/bulk-restore/change-status/bulk-import/archived). API /api/v1/recovery-standard/ and recovery-standard-archive. Fields: furnace_type, material_type, min_recovery, max_recovery, standard_loss, effective_from, status, remarks. React+Antd.
```

---

Ref: `.cursor/rules/recovery-standard-react-integration.mdc` in backend repo for full endpoint list.
