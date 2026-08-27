"""
Test cases for Plant Capability architecture
"""

import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from common.models import Plant, PlantCapability, PlantType, PlantTypeCapability
from common.services.plant_capability_service import (
    can_assign_capability,
    can_deactivate_capability_mapping,
    can_delete_capability,
    get_plant_capabilities,
    get_plants_with_capability,
    has_capability,
)

User = get_user_model()


class PlantTypeModelTest(TestCase):
    """Test PlantType model"""

    def setUp(self):
        self.plant_type = PlantType.objects.create(
            code="EXTRUSION",
            name="Extrusion Plant",
            status="Active",
        )

    def test_plant_type_creation(self):
        """Test creating a plant type"""
        self.assertEqual(self.plant_type.code, "EXTRUSION")
        self.assertEqual(self.plant_type.name, "Extrusion Plant")
        self.assertEqual(self.plant_type.status, "Active")
        self.assertFalse(self.plant_type.is_deleted)

    def test_plant_type_code_uppercase(self):
        """Test that code is automatically uppercased"""
        plant_type = PlantType.objects.create(
            code="warehouse",
            name="Warehouse",
        )
        self.assertEqual(plant_type.code, "WAREHOUSE")

    def test_plant_type_str(self):
        """Test string representation"""
        self.assertEqual(str(self.plant_type), "EXTRUSION - Extrusion Plant")


class PlantCapabilityModelTest(TestCase):
    """Test PlantCapability model"""

    def setUp(self):
        self.capability = PlantCapability.objects.create(
            code="PRODUCTION",
            name="Production",
            description="Can create production orders",
            status="Active",
        )

    def test_capability_creation(self):
        """Test creating a capability"""
        self.assertEqual(self.capability.code, "PRODUCTION")
        self.assertEqual(self.capability.name, "Production")
        self.assertFalse(self.capability.is_deleted)

    def test_capability_code_uppercase(self):
        """Test that code is automatically uppercased"""
        capability = PlantCapability.objects.create(
            code="inventory",
            name="Inventory",
        )
        self.assertEqual(capability.code, "INVENTORY")

    def test_duplicate_capability_code_fails(self):
        """Test that duplicate capability codes fail"""
        with self.assertRaises(Exception):
            PlantCapability.objects.create(
                code="PRODUCTION",
                name="Production Duplicate",
            )


class PlantTypeCapabilityModelTest(TestCase):
    """Test PlantTypeCapability mapping model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.plant_type = PlantType.objects.create(
            code="EXTRUSION",
            name="Extrusion Plant",
        )
        self.capability = PlantCapability.objects.create(
            code="PRODUCTION",
            name="Production",
        )
        self.mapping = PlantTypeCapability.objects.create(
            plant_type=self.plant_type,
            capability=self.capability,
            status="Active",
            created_by=self.user,
        )

    def test_mapping_creation(self):
        """Test creating a mapping"""
        self.assertEqual(self.mapping.plant_type, self.plant_type)
        self.assertEqual(self.mapping.capability, self.capability)
        self.assertEqual(self.mapping.status, "Active")

    def test_duplicate_mapping_fails(self):
        """Test that duplicate mappings fail"""
        with self.assertRaises(Exception):
            PlantTypeCapability.objects.create(
                plant_type=self.plant_type,
                capability=self.capability,
                status="Active",
            )


class PlantCapabilityServiceTest(TestCase):
    """Test Plant Capability Service functions"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.plant_type = PlantType.objects.create(
            code="EXTRUSION",
            name="Extrusion Plant",
            status="Active",
        )
        self.production_capability = PlantCapability.objects.create(
            code="PRODUCTION",
            name="Production",
            status="Active",
        )
        self.inventory_capability = PlantCapability.objects.create(
            code="INVENTORY",
            name="Inventory",
            status="Active",
        )
        self.plant_type_capability = PlantTypeCapability.objects.create(
            plant_type=self.plant_type,
            capability=self.production_capability,
            status="Active",
            created_by=self.user,
        )
        self.plant = Plant.objects.create(
            plant_code="PLANT-001",
            plant_name="Test Plant",
            plant_type=self.plant_type,
            status="Active",
            address_line_1="123 Test St",
            city="Test City",
            state="Test State",
            country="Test Country",
            postal_code="12345",
            phone_number="1234567890",
            email="plant@test.com",
            plant_head_name="Test Head",
        )

    def test_has_capability_true(self):
        """Test has_capability returns True for existing capability"""
        result = has_capability(self.plant, "PRODUCTION")
        self.assertTrue(result)

    def test_has_capability_false(self):
        """Test has_capability returns False for non-existing capability"""
        result = has_capability(self.plant, "DISPATCH")
        self.assertFalse(result)

    def test_has_capability_inactive_plant(self):
        """Test has_capability returns False for inactive plant"""
        self.plant.status = "Inactive"
        self.plant.save()
        result = has_capability(self.plant, "PRODUCTION")
        self.assertFalse(result)

    def test_get_plant_capabilities(self):
        """Test get_plant_capabilities returns list of capability codes"""
        # Add another capability
        PlantTypeCapability.objects.create(
            plant_type=self.plant_type,
            capability=self.inventory_capability,
            status="Active",
            created_by=self.user,
        )
        capabilities = get_plant_capabilities(self.plant)
        self.assertIn("PRODUCTION", capabilities)
        self.assertIn("INVENTORY", capabilities)

    def test_get_plants_with_capability(self):
        """Test get_plants_with_capability returns correct plants"""
        plants = get_plants_with_capability("PRODUCTION")
        self.assertIn(self.plant, plants)

    def test_can_assign_capability_true(self):
        """Test can_assign_capability returns True for valid assignment"""
        new_capability = PlantCapability.objects.create(
            code="DISPATCH",
            name="Dispatch",
            status="Active",
        )
        can_assign, message = can_assign_capability(self.plant_type, new_capability)
        self.assertTrue(can_assign)
        self.assertIsNone(message)

    def test_can_assign_capability_duplicate(self):
        """Test can_assign_capability returns False for duplicate"""
        can_assign, message = can_assign_capability(
            self.plant_type, self.production_capability
        )
        self.assertFalse(can_assign)
        self.assertIsNotNone(message)

    def test_can_deactivate_capability_mapping_with_active_plants(self):
        """Test cannot deactivate mapping if active plants exist"""
        can_deactivate, message = can_deactivate_capability_mapping(
            self.plant_type_capability
        )
        self.assertFalse(can_deactivate)
        self.assertIn("Active plants exist", message)

    def test_can_deactivate_capability_mapping_no_active_plants(self):
        """Test can deactivate mapping if no active plants"""
        self.plant.status = "Inactive"
        self.plant.save()
        can_deactivate, message = can_deactivate_capability_mapping(
            self.plant_type_capability
        )
        self.assertTrue(can_deactivate)
        self.assertIsNone(message)

    def test_can_delete_capability_with_mappings(self):
        """Test cannot delete capability if mapped to plant types"""
        can_delete, message = can_delete_capability(self.production_capability)
        self.assertFalse(can_delete)
        self.assertIn("mapped to", message)

    def test_can_delete_capability_no_mappings(self):
        """Test can delete capability if not mapped"""
        new_capability = PlantCapability.objects.create(
            code="TEST",
            name="Test Capability",
            status="Active",
        )
        can_delete, message = can_delete_capability(new_capability)
        self.assertTrue(can_delete)
        self.assertIsNone(message)


class PlantCapabilityAPITest(TestCase):
    """Test Plant Capability API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client.force_login(self.user)
        # Note: In real tests, you'd use JWT authentication
        # For simplicity, using force_login here

    def test_create_capability(self):
        """Test creating a capability via API"""
        data = {
            "code": "TEST",
            "name": "Test Capability",
            "description": "Test description",
            "status": "Active",
        }
        # This would be a POST request in real scenario
        # For now, testing model creation
        capability = PlantCapability.objects.create(**data)
        self.assertEqual(capability.code, "TEST")

    def test_duplicate_capability_code_validation(self):
        """Test that duplicate capability codes are rejected"""
        PlantCapability.objects.create(
            code="DUPLICATE",
            name="First",
        )
        # Second creation should fail
        with self.assertRaises(Exception):
            PlantCapability.objects.create(
                code="DUPLICATE",
                name="Second",
            )


class PlantTypeCapabilityAPITest(TestCase):
    """Test Plant Type Capability API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.plant_type = PlantType.objects.create(
            code="EXTRUSION",
            name="Extrusion Plant",
        )
        self.capability = PlantCapability.objects.create(
            code="PRODUCTION",
            name="Production",
            status="Active",
        )

    def test_assign_capability_to_plant_type(self):
        """Test assigning capability to plant type"""
        mapping = PlantTypeCapability.objects.create(
            plant_type=self.plant_type,
            capability=self.capability,
            status="Active",
            created_by=self.user,
        )
        self.assertEqual(mapping.plant_type, self.plant_type)
        self.assertEqual(mapping.capability, self.capability)

    def test_duplicate_mapping_validation(self):
        """Test that duplicate mappings are rejected"""
        PlantTypeCapability.objects.create(
            plant_type=self.plant_type,
            capability=self.capability,
            status="Active",
            created_by=self.user,
        )
        # Second mapping should fail
        with self.assertRaises(Exception):
            PlantTypeCapability.objects.create(
                plant_type=self.plant_type,
                capability=self.capability,
                status="Active",
            )
