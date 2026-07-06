import unittest
from pydantic import ValidationError
from backend.controllers.superadmin import CreateUserRequest
from backend.meta import UserRole, JurisdictionZone

class TestUserValidators(unittest.TestCase):
    def test_exempt_roles_auto_null_jurisdiction(self):
        # Exempt roles: CITIZEN, SUPERADMIN, ADMIN, NODAL_OFFICER, NAKA_INCHARGE
        for role in (UserRole.CITIZEN, UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.NODAL_OFFICER, UserRole.NAKA_INCHARGE):
            # Even if we pass a zone, it should be auto-set to None
            req = CreateUserRequest(
                mobile="1234567890",
                name="Exempt User",
                role=role,
                jurisdiction_zone=JurisdictionZone.ULB
            )
            self.assertIsNone(req.jurisdiction_zone)

    def test_non_exempt_roles_require_jurisdiction(self):
        # Non-exempt roles: JEN, DEPT_ATP, DEPT_LAND, DEPT_LEGAL, etc.
        for role in (UserRole.JEN, UserRole.DEPT_ATP, UserRole.DEPT_LAND, UserRole.DEPT_LEGAL):
            # Passing ULB is valid
            req = CreateUserRequest(
                mobile="1234567890",
                name="Official User",
                role=role,
                jurisdiction_zone=JurisdictionZone.ULB
            )
            self.assertEqual(req.jurisdiction_zone, JurisdictionZone.ULB)
            
            # Passing None raises ValidationError
            with self.assertRaises(ValidationError):
                CreateUserRequest(
                    mobile="1234567890",
                    name="Official User",
                    role=role,
                    jurisdiction_zone=None
                )
