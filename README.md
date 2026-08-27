# Alux ERP Backend

Django REST API for the **Alux Aluminum Extrusion ERP**.

| Item | Value |
|------|-------|
| Folder | `alux-erp-backend-two` |
| Project package | `alux_erp` |
| API prefix | `/api/v1/` |
| Auth | JWT — `POST /get-token/`, `POST /refresh-token/` |

For full monorepo architecture, domain modules, API contracts, and end-to-end runbooks, see the root [README.md](../README.md).

---

## Stack

- Django 5.1.1 + Django REST Framework 3.15
- PostgreSQL + Redis + Celery 5.4
- SimpleJWT, django-filter, django-axes, simple-history, cors-headers
- AWS S3 (boto3), Excel/PDF tooling (openpyxl, reportlab, xhtml2pdf, …)

---

## Prerequisites

- Python 3.11+ (recommended)
- PostgreSQL 14+
- Redis (for Celery)
- Virtual environment

---

## Setup

```bash
cd alux-erp-backend-two
```

### 1. Create and activate virtualenv

**Windows:**

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv env
source env/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Copy and fill required variables (never commit real secrets):

```env
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
APP_URL=http://localhost:8000
LOG_FILE_LOCATION=msg_logger/django_logging.log

DB_NAME=aluka_local
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

INIT_EMAIL=admin@example.com
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me

AWS_ACCESS_KEY=
AWS_SECRET_KEY=
REGION_NAME=ap-south-1
BUCKET_NAME=

SMTP_EMAIL_SERVER=smtp.gmail.com
EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_COMPANY_NAME=AluxERP
```

### 4. Migrate database

```bash
python manage.py migrate
```

### 5. Optional seed / init data

```bash
python manage.py init_data
```

Targeted examples:

```bash
python manage.py init_plant_data
python manage.py init_uom_data
python manage.py init_alloy_data
python manage.py init_die_data
python manage.py init_furnace_data
```

CSV sources: `core/management/source/`

### 6. Run development server

```bash
python manage.py runserver
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | API root |
| http://127.0.0.1:8000/admin/ | Django admin |

### 7. Celery (separate terminals)

```bash
celery -A alux_erp -l info
celery -A alux_erp beat -l info
```

---

## Auth quick test

```http
POST /get-token/
Content-Type: application/json

{
  "email": "your@email.com",
  "password": "your-password"
}
```

```http
Authorization: Bearer <access_token>
```

---

## Architecture snapshot

| Layer | Location |
|-------|----------|
| Settings / Celery | `alux_erp/` |
| Aggregated routers | `alux_erp/routers.py` → `/api/v1/` |
| Shared models / archive | `common/` (`BaseModel`, `ArchiveMixin`, `BaseModelViewSet`) |
| Company settings base | `settings/models.py` (`BaseModule`) |
| Utilities | `utils/` (pagination, errors, S3, mail, Excel, PDF, activity log) |
| Custom user | `user/` (email login) |
| Domain apps | One Django app per business module (die, workorder, production, …) |

### Patterns to follow

- ViewSets + serializers; reuse `Pagination`, `custom_exception`, soft-delete/archive
- Permissions via Django groups/codenames or custom `BasePermission`
- Response errors: `{ "success": false, "message": "…" }`
- Prefer extending existing apps over new parallel frameworks

---

## Testing & quality

```bash
pytest -s
pytest --reuse-db

black .
flake8 --exclude=env

pip install autoflake
autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place .
```

- Pytest: `pytest.ini`
- Flake8 ignores: `tox.ini` (`E501`, `W503`)

---

## Key URLs

| Path | Purpose |
|------|---------|
| `/` | Root status |
| `/get-token/` | JWT obtain |
| `/refresh-token/` | JWT refresh |
| `/api/v1/` | Versioned APIs |
| `/dashboard` | Dashboard API |
| `/admin/` | Django admin |
| `/api/v1/silk/` | Silk profiler |

---

## Related

- Monorepo docs: [../README.md](../README.md)
- Imports: [imports/README.md](imports/README.md)
- Frontend: [../alux-erp-frontend-new-two/README.md](../alux-erp-frontend-new-two/README.md)
