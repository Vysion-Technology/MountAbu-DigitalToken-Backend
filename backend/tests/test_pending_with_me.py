import unittest
from unittest.mock import MagicMock
from backend.dao.application import ApplicationDAO
from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationFlags,
    UserRole,
    CommentType,
)

class TestPendingWithMeFlag(unittest.TestCase):
    def setUp(self):
        self.dao = ApplicationDAO(None)

    def test_superadmin_and_admin_have_no_pending_with_me(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.SUBMITTED
        
        # Superadmin
        flags_super = self.dao.get_required_flags(app, UserRole.SUPERADMIN)
        self.assertNotIn(ApplicationFlags.PENDING_WITH_ME, flags_super)

        # Admin
        flags_admin = self.dao.get_required_flags(app, UserRole.ADMIN)
        self.assertNotIn(ApplicationFlags.PENDING_WITH_ME, flags_admin)

    def test_nodal_officer_new_submitted(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.SUBMITTED
        
        flags = self.dao.get_required_flags(app, UserRole.NODAL_OFFICER)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_nodal_officer_new_approved_needing_token(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.APPROVED
        app.inspections = [MagicMock()]
        app.phase_materials = [MagicMock()]
        
        flags = self.dao.get_required_flags(app, UserRole.NODAL_OFFICER)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_nodal_officer_renovation_forwarded_not_pending(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        
        flags = self.dao.get_required_flags(app, UserRole.NODAL_OFFICER)
        self.assertNotIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_commissioner_renovation_submitted(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.SUBMITTED
        
        flags = self.dao.get_required_flags(app, UserRole.COMMISSIONER)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_commissioner_renovation_forwarded_incomplete_comments(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        app.comments = []
        app.inspections = [MagicMock()]
        
        flags = self.dao.get_required_flags(app, UserRole.COMMISSIONER)
        self.assertNotIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_commissioner_renovation_forwarded_complete_comments_and_inspected(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        app.inspections = [MagicMock()]
        
        # Comments from all depts
        c1 = MagicMock()
        c1.commenter.role = UserRole.DEPT_ATP
        c1.comment_type = CommentType.DEPT_REVIEW
        c2 = MagicMock()
        c2.commenter.role = UserRole.DEPT_LAND
        c2.comment_type = CommentType.DEPT_REVIEW
        c3 = MagicMock()
        c3.commenter.role = UserRole.DEPT_LEGAL
        c3.comment_type = CommentType.DEPT_REVIEW
        app.comments = [c1, c2, c3]
        
        flags = self.dao.get_required_flags(app, UserRole.COMMISSIONER)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_jen_new_approved_needing_inspection(self):
        app = MagicMock()
        app.type = ApplicationType.NEW
        app.status = ApplicationStatus.APPROVED
        app.inspections = []
        app.phase_materials = []
        
        flags = self.dao.get_required_flags(app, UserRole.JEN)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_jen_renovation_forwarded_needing_inspection(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        app.inspections = []
        app.phase_materials = []
        
        flags = self.dao.get_required_flags(app, UserRole.JEN)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_dept_role_renovation_forwarded_not_commented(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        app.comments = []
        
        flags = self.dao.get_required_flags(app, UserRole.DEPT_LAND)
        self.assertIn(ApplicationFlags.PENDING_WITH_ME, flags)

    def test_dept_role_renovation_forwarded_already_commented(self):
        app = MagicMock()
        app.type = ApplicationType.RENOVATION
        app.status = ApplicationStatus.FORWARDED
        
        c = MagicMock()
        c.commenter.role = UserRole.DEPT_LAND
        c.comment_type = CommentType.DEPT_REVIEW
        app.comments = [c]
        
        flags = self.dao.get_required_flags(app, UserRole.DEPT_LAND)
        self.assertNotIn(ApplicationFlags.PENDING_WITH_ME, flags)
