# Plant Capability-Driven Architecture

## Overview

This document describes the **Plant Capability-Driven Architecture** for the ALUX ERP system. This architecture replaces hardcoded boolean flags (like `is_production_enabled`, `is_inventory_enabled`) with a flexible, configuration-driven approach.

## Architecture Principles

1. **No Hardcoded Behavior**: All plant behavior is controlled by configuration, not code
2. **Capability-Driven Logic**: Business rules check capabilities, not plant types directly
3. **Flexible Configuration**: Capabilities can be assigned/removed from plant types without code changes
4. **Data Integrity**: Database constraints ensure consistency

## Database Models

### 1. PlantType
Defines types of plants (EXTRUSION, WAREHOUSE, SITE, OFFICE, etc.)

**Fields**:
- `id` (UUID, PK)
- `code` (unique, uppercase, indexed)
- `name`
- `status` (Active/Inactive)
- `created_at`, `updated_at`
- `is_deleted` (boolean)

### 2. PlantCapability
Defines WHAT ACTIONS are allowed (PRODUCTION, INVENTORY, DISPATCH, etc.)

**Fields**:
- `id` (UUID, PK)
- `code` (unique, uppercase, indexed)
- `name`
- `description` (optional)
- `status` (Active/Inactive)
- `created_at`, `updated_at`
- `is_deleted` (boolean)

**Default Capabilities**:
- `PRODUCTION` - Can create and manage production orders
- `INVENTORY` - Can manage inventory stock, GRN, and material issues
- `DISPATCH` - Can dispatch goods and manage shipments
- `CONSUMPTION` - Can consume materials (for sites/projects)
- `FINANCE` - Can manage financial transactions and accounting
- `PURCHASE` - Can create and manage purchase orders
- `QUALITY` - Can perform quality checks and testing

### 3. PlantTypeCapability
Many-to-Many mapping between PlantType and PlantCapability

**Fields**:
- `id` (UUID, PK)
- `plant_type` (FK → PlantType, PROTECT)
- `capability` (FK → PlantCapability, PROTECT)
- `status` (Active/Inactive)
- `created_at`
- `created_by` (FK → User)
- `is_deleted` (boolean)

**Constraints**:
- Unique (plant_type, capability) when not deleted
- Cannot delete capability if mapped
- Cannot deactivate mapping if active plants exist

### 4. Plant (Updated)
Updated to use FK to PlantType instead of CharField

**Changes**:
- `plant_type` changed from `CharField` to `ForeignKey(PlantType)`
- All behavior derived via `PlantTypeCapability` mappings

## Default Mappings

### EXTRUSION Plant Type
- PRODUCTION
- INVENTORY
- QUALITY

### WAREHOUSE Plant Type
- INVENTORY
- DISPATCH

### SITE Plant Type
- CONSUMPTION

### OFFICE Plant Type
- FINANCE

## Service Layer

### `common/services/plant_capability_service.py`

Provides helper functions for capability checks:

#### `has_capability(plant, capability_code) -> bool`
Check if a plant has a specific capability.

```python
from common.services.plant_capability_service import has_capability

if has_capability(plant, "PRODUCTION"):
    # Allow production order creation
    create_production_order(plant, ...)
else:
    raise ValidationError("Plant does not have PRODUCTION capability")
```

#### `get_plant_capabilities(plant) -> List[str]`
Get all active capability codes for a plant.

```python
capabilities = get_plant_capabilities(plant)
# Returns: ["PRODUCTION", "INVENTORY", "QUALITY"]
```

#### `get_plants_with_capability(capability_code, active_only=True) -> List[Plant]`
Get all plants that have a specific capability.

```python
production_plants = get_plants_with_capability("PRODUCTION")
```

#### `can_assign_capability(plant_type, capability) -> Tuple[bool, Optional[str]]`
Check if a capability can be assigned to a plant type.

#### `can_deactivate_capability_mapping(mapping) -> Tuple[bool, Optional[str]]`
Check if a capability mapping can be deactivated.

#### `can_delete_capability(capability) -> Tuple[bool, Optional[str]]`
Check if a capability can be deleted.

## API Endpoints

### Plant Capability APIs

**Base URL**: `/api/v1/masters/plant-capabilities/`

1. **List Capabilities**
   - `GET /api/v1/masters/plant-capabilities/`
   - Query params: `search`, `ordering`, `status`

2. **Get Capability Details**
   - `GET /api/v1/masters/plant-capabilities/{id}/`

3. **Create Capability**
   - `POST /api/v1/masters/plant-capabilities/`
   - Body: `{ "code": "PRODUCTION", "name": "Production", "description": "...", "status": "Active" }`

4. **Update Capability**
   - `PUT /api/v1/masters/plant-capabilities/{id}/`
   - `PATCH /api/v1/masters/plant-capabilities/{id}/`

5. **Change Status**
   - `POST /api/v1/masters/plant-capabilities/{id}/change-status/`
   - Body: `{ "status": "Inactive" }`

6. **Delete Capability**
   - `DELETE /api/v1/masters/plant-capabilities/{id}/`
   - Soft delete (sets `is_deleted=True`)

### Plant Type Capability Mapping APIs

**Base URL**: `/api/v1/masters/plant-type-capabilities/`

1. **Assign Capability to Plant Type**
   - `POST /api/v1/masters/plant-type-capabilities/`
   - Body: `{ "plant_type": "<uuid>", "capability": "<uuid>", "status": "Active" }`

2. **List All Mappings**
   - `GET /api/v1/masters/plant-type-capabilities/`
   - Query params: `plant_type`, `capability`, `status`, `search`, `ordering`

3. **List Capabilities for Plant Type**
   - `GET /api/v1/masters/plant-type-capabilities/plant-type/{plant_type_id}/capabilities/`

4. **Update Mapping**
   - `PUT /api/v1/masters/plant-type-capabilities/{id}/`
   - `PATCH /api/v1/masters/plant-type-capabilities/{id}/`

5. **Remove Mapping**
   - `DELETE /api/v1/masters/plant-type-capabilities/{id}/`
   - Soft delete (sets `is_deleted=True`)

## Usage Examples

### In Production Module

```python
from common.services.plant_capability_service import has_capability

def create_production_order(plant, ...):
    if not has_capability(plant, "PRODUCTION"):
        raise ValidationError(
            f"Plant {plant.plant_code} does not have PRODUCTION capability"
        )
    # Create production order
    ...
```

### In Inventory Module

```python
from common.services.plant_capability_service import has_capability

def create_grn(plant, ...):
    if not has_capability(plant, "INVENTORY"):
        raise ValidationError(
            f"Plant {plant.plant_code} does not have INVENTORY capability"
        )
    # Create GRN
    ...
```

### In Dispatch Module

```python
from common.services.plant_capability_service import has_capability

def create_dispatch(plant, ...):
    if not has_capability(plant, "DISPATCH"):
        raise ValidationError(
            f"Plant {plant.plant_code} does not have DISPATCH capability"
        )
    # Create dispatch
    ...
```

## Business Rules

1. **No Hardcoded Checks**: Never check `plant.plant_type.code` directly in business logic
2. **Always Use Service**: Always use `has_capability()` service function
3. **Capability Validation**: All critical operations must validate capabilities
4. **Mapping Constraints**: Cannot delete capability if mapped to plant types
5. **Active Plant Protection**: Cannot deactivate mapping if active plants exist

## Migration Strategy

1. **Schema Migration** (`0009_plant_capability_models.py`): Creates new models
2. **Data Migration** (`0010_migrate_plant_to_plant_type_fk.py`): Migrates Plant.plant_type from CharField to FK
3. **Default Data** (`0011_default_plant_capabilities.py`): Creates default capabilities and mappings

## Testing

Comprehensive test suite in `common/tests/test_plant_capability.py`:

- Model tests (PlantType, PlantCapability, PlantTypeCapability)
- Service function tests
- API endpoint tests
- Business rule validation tests

## Benefits

1. **Flexibility**: Add new capabilities without code changes
2. **Maintainability**: Single source of truth for plant behavior
3. **Scalability**: Easy to add new plant types and capabilities
4. **Configuration-Driven**: Business users can configure capabilities
5. **Type Safety**: Database constraints ensure data integrity

## Future Enhancements

- Capability-based permissions
- Capability versioning
- Capability inheritance
- Audit trail for capability changes

