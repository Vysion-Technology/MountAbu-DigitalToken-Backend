import unittest
from unittest.mock import MagicMock
from backend.dao.application import ApplicationDAO
from backend.meta import ApplicationStatus, ApplicationType, ApplicationFlags

class TestAllDeptFlag(unittest.TestCase):
    def setUp(self):
        # Pass None as the database session since get_required_flags is synchronous and does not use db
        self.dao = ApplicationDAO(None)

    def test_new_construction_approved_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.APPROVED
        app.inspections = []
        app.materials = []
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_new_construction_submitted_does_not_have_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.SUBMITTED
        app.inspections = []
        app.materials = []
        
        flags = self.dao.get_required_flags(app)
        self.assertNotIn(ApplicationFlags.ALL_DEPT, flags)

    def test_renovation_forwarded_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        app.inspections = []
        app.materials = []
        app.comments = []
        app.action_logs = []
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_renovation_submitted_does_not_have_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.SUBMITTED
        app.inspections = []
        app.materials = []
        app.comments = []
        app.action_logs = []
        
        flags = self.dao.get_required_flags(app)
        self.assertNotIn(ApplicationFlags.ALL_DEPT, flags)

    def test_new_construction_token_generated_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.TOKEN_GENERATED
        app.phases = []
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_renovation_approved_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.APPROVED
        app.inspections = []
        app.materials = []
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_renovation_token_generated_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.TOKEN_GENERATED
        app.phases = []
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_new_construction_once_approved_now_withdrawn_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.WITHDRAWN
        
        log = MagicMock()
        log.to_status = ApplicationStatus.APPROVED
        app.action_logs = [log]
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_renovation_once_forwarded_now_withheld_has_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.WITHHELD
        
        log = MagicMock()
        log.to_status = ApplicationStatus.FORWARDED
        app.action_logs = [log]
        
        flags = self.dao.get_required_flags(app)
        self.assertIn(ApplicationFlags.ALL_DEPT, flags)

    def test_pending_new_construction_does_not_have_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.PENDING
        
        log = MagicMock()
        log.to_status = ApplicationStatus.APPROVED
        app.action_logs = [log]
        
        flags = self.dao.get_required_flags(app)
        self.assertNotIn(ApplicationFlags.ALL_DEPT, flags)

    def test_pending_renovation_does_not_have_all_dept_flag(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.PENDING
        
        log = MagicMock()
        log.to_status = ApplicationStatus.FORWARDED
        app.action_logs = [log]
        
        flags = self.dao.get_required_flags(app)
        self.assertNotIn(ApplicationFlags.ALL_DEPT, flags)
