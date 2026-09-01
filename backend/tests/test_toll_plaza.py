import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import VehicleEntry, VehicleMaterial, Material


class TestTollPlazaVerification(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_session = AsyncMock()
        self.dao = ApplicationDAO(self.mock_session)

    async def test_verification_success(self):
        """Success validation stamps plaza_verified_at and returns detail list."""
        app_id = 10
        phase_num = 2
        vehicle_num = "RJ-24-UA-1234"

        # Mock VehicleEntry (unverified, entered 10 mins ago)
        mock_entry = MagicMock(spec=VehicleEntry)
        mock_entry.id = 101
        mock_entry.vehicle_number = "RJ 24 UA 1234"
        mock_entry.entry_at = datetime.now() - timedelta(minutes=10)
        mock_entry.plaza_verified_at = None

        # Mock VehicleMaterial & Material relationships
        mock_vm = MagicMock(spec=VehicleMaterial)
        mock_vm.material_id = 5
        mock_vm.custom_name = None
        mock_vm.custom_unit = None
        mock_vm.quantity = 15.0

        mock_material = MagicMock(spec=Material)
        mock_material.name = "Gravel"
        mock_material.unit = "Tons"

        # Setup mock db query responses
        async def mock_execute(stmt):
            res = MagicMock()
            sql_str = str(stmt).lower()
            if "vehicle_materials" in sql_str:
                res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_vm])))
            else:
                res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_entry])))
            return res

        async def mock_get(model_class, pk):
            if model_class == Material and pk == 5:
                return mock_material
            return None

        self.mock_session.execute = AsyncMock(side_effect=mock_execute)
        self.mock_session.get = AsyncMock(side_effect=mock_get)

        # Run
        response = await self.dao.verify_toll_plaza_entry(
            application_id=app_id,
            phase=phase_num,
            vehicle_number=vehicle_num
        )

        # Assertions
        self.assertTrue(response["verified"])
        self.assertEqual(response["naka_entry_id"], 101)
        self.assertIsNotNone(mock_entry.plaza_verified_at)
        self.assertEqual(len(response["materials"]), 1)
        self.assertEqual(response["materials"][0]["material_name"], "Gravel")
        self.assertEqual(response["materials"][0]["quantity"], 15.0)
        self.mock_session.commit.assert_awaited_once()

    async def test_verification_not_found(self):
        """Raises 404 when no matching vehicle plate entry is found."""
        app_id = 10
        phase_num = 2
        vehicle_num = "RJ-24-UA-1234"

        # Mock no entries returned
        mock_res = MagicMock()
        mock_res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as context:
            await self.dao.verify_toll_plaza_entry(
                application_id=app_id,
                phase=phase_num,
                vehicle_number=vehicle_num
            )
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("No Naka vehicle entry found", context.exception.detail)

    async def test_verification_already_verified(self):
        """Raises 400 when Naka entry has already been verified at Toll Plaza."""
        app_id = 10
        phase_num = 2
        vehicle_num = "RJ-24-UA-1234"

        # Mock already verified entry
        mock_entry = MagicMock(spec=VehicleEntry)
        mock_entry.id = 102
        mock_entry.vehicle_number = "RJ-24-UA-1234"
        mock_entry.plaza_verified_at = datetime.now() - timedelta(minutes=5)

        mock_res = MagicMock()
        mock_res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_entry])))
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as context:
            await self.dao.verify_toll_plaza_entry(
                application_id=app_id,
                phase=phase_num,
                vehicle_number=vehicle_num
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("already been verified", context.exception.detail)

    async def test_verification_expired(self):
        """Raises 400 when Naka entry was created more than 2 hours ago."""
        app_id = 10
        phase_num = 2
        vehicle_num = "RJ-24-UA-1234"

        # Mock expired entry (3 hours ago)
        mock_entry = MagicMock(spec=VehicleEntry)
        mock_entry.id = 103
        mock_entry.vehicle_number = "RJ-24-UA-1234"
        mock_entry.entry_at = datetime.now() - timedelta(hours=3)
        mock_entry.plaza_verified_at = None

        mock_res = MagicMock()
        mock_res.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_entry])))
        self.mock_session.execute = AsyncMock(return_value=mock_res)

        with self.assertRaises(HTTPException) as context:
            await self.dao.verify_toll_plaza_entry(
                application_id=app_id,
                phase=phase_num,
                vehicle_number=vehicle_num
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("verification window has expired", context.exception.detail)
