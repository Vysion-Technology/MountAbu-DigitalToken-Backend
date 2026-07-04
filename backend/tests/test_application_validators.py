import unittest
from pydantic import ValidationError
from backend.schemas.request.application import ApplicationCreate, ApplicationMaterialRequirements
from backend.meta import ApplicationType, PropertyUsageType, StructureType, JurisdictionZone

class TestApplicationValidators(unittest.TestCase):
    def setUp(self):
        self.base_data = {
            "applicant_name": "John Doe",
            "father_name": "Senior Doe",
            "email": "john@example.com",
            "current_address": "123 Main St",
            "property_address": "456 Property Rd",
            "title": "Build House",
            "work_description": "Building a new floor",
            "contractor_name": "BuildCorp",
            "is_agriculture_land": False,
            "property_usage": PropertyUsageType.DOMESTIC,
            "ward_id": 1,
            "material_requirements": [
                {
                    "material_id": 1,
                    "material_qty": 100
                }
            ],
            "type": ApplicationType.NEW,
            "jurisdiction_zone": JurisdictionZone.ULB
        }

    def test_null_defaults_pass_validation(self):
        data = self.base_data.copy()
        data["existing_structure"] = None
        data["construction_floor"] = None
        
        # Should not raise validation error
        app = ApplicationCreate(**data)
        self.assertIsNone(app.existing_structure)
        self.assertIsNone(app.construction_floor)

    def test_new_construction_none_allows_fencing_or_g(self):
        data = self.base_data.copy()
        data["existing_structure"] = StructureType.NONE
        
        # G is valid
        data["construction_floor"] = StructureType.G
        app = ApplicationCreate(**data)
        self.assertEqual(app.construction_floor, StructureType.G)
        
        # FENCING is valid
        data["construction_floor"] = StructureType.FENCING
        app = ApplicationCreate(**data)
        self.assertEqual(app.construction_floor, StructureType.FENCING)

        # G+1 is invalid for NONE existing structure
        data["construction_floor"] = StructureType.G_1
        with self.assertRaises(ValidationError):
            ApplicationCreate(**data)

    def test_new_construction_floor_height_restrictions(self):
        data = self.base_data.copy()
        
        # Existing G -> must be G+1
        data["existing_structure"] = StructureType.G
        data["construction_floor"] = StructureType.G_1
        app = ApplicationCreate(**data)
        self.assertEqual(app.construction_floor, StructureType.G_1)
        
        # Existing G -> requesting G+2 raises error
        data["construction_floor"] = StructureType.G_2
        with self.assertRaises(ValidationError):
            ApplicationCreate(**data)

    def test_new_construction_g3_maximum_limit(self):
        data = self.base_data.copy()
        data["existing_structure"] = StructureType.G_3
        data["construction_floor"] = StructureType.G_3
        
        with self.assertRaises(ValidationError):
            ApplicationCreate(**data)

    def test_renovation_allows_equal_or_lesser_floor(self):
        data = self.base_data.copy()
        data["type"] = ApplicationType.RENOVATION
        data["existing_structure"] = StructureType.G_1
        
        # Equal (G+1) is valid
        data["construction_floor"] = StructureType.G_1
        app = ApplicationCreate(**data)
        self.assertEqual(app.construction_floor, StructureType.G_1)

        # Less than (G) is valid
        data["construction_floor"] = StructureType.G
        app = ApplicationCreate(**data)
        self.assertEqual(app.construction_floor, StructureType.G)

        # Greater than (G+2) is invalid
        data["construction_floor"] = StructureType.G_2
        with self.assertRaises(ValidationError):
            ApplicationCreate(**data)
