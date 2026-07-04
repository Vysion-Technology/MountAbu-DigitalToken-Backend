import unittest
from unittest.mock import AsyncMock, MagicMock
from backend.dao.application import ApplicationDAO
from backend.dbmodels.application import Application, ApplicationPhaseMaterial

class TestUpdatePhaseMaterials(unittest.IsolatedAsyncioTestCase):
    async def test_update_phase_materials_deletes_and_inserts(self):
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock() # session.add is synchronous
        dao = ApplicationDAO(mock_session)

        # Mock session.get to return a mock Application
        mock_app = MagicMock(spec=Application)
        mock_session.get.return_value = mock_app

        # Prepare mock input data
        pm1 = MagicMock()
        pm1.phase = 1
        pm1.material_id = 8
        pm1.custom_name = None
        pm1.custom_unit = None
        pm1.quantity = 5

        pm2 = MagicMock()
        pm2.phase = 2
        pm2.material_id = 7
        pm2.custom_name = "custom"
        pm2.custom_unit = "box"
        pm2.quantity = 10

        phase_materials_input = [pm1, pm2]

        # Execute
        await dao.update_phase_materials(148, phase_materials_input)

        # Verify session.get was called to fetch the application
        mock_session.get.assert_awaited_once_with(Application, 148)

        # Verify that execute was called to run the delete statement
        mock_session.execute.assert_awaited_once()
        
        # Verify that session.add was called for both new phase materials
        self.assertEqual(mock_session.add.call_count, 2)
        
        # Verify session.commit was called
        mock_session.commit.assert_awaited_once()
