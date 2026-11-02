import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    UserRole,
    ObjectionStatus,
)
from backend.core.overdue import compute_overdue_info


def test_submitted_application_never_overdue():
    """Ensure applications in SUBMITTED state are NEVER counted as overdue."""
    app = MagicMock()
    app.status = ApplicationStatus.SUBMITTED
    app.type = ApplicationType.RENOVATION
    app.created_at = datetime.now() - timedelta(days=100)
    app.action_logs = []
    app.comments = []
    app.inspections = []
    app.phase_materials = []
    app.objections = []

    is_overdue, depts, max_days = compute_overdue_info(app)
    assert not is_overdue
    assert depts == []
    assert max_days is None


def test_renovation_forwarded_overdue_land():
    """Ensure renovation forwarded for > 21 days without land comment is overdue."""
    now = datetime.now()
    app = MagicMock()
    app.status = ApplicationStatus.FORWARDED
    app.type = ApplicationType.RENOVATION
    app.created_at = now - timedelta(days=25)
    app.action_logs = []
    app.comments = []  # No comments from Land, Legal, or ATP
    app.inspections = [MagicMock()]
    app.phase_materials = [MagicMock()]
    app.objections = []

    is_overdue, depts, max_days = compute_overdue_info(app, now=now)
    assert is_overdue
    assert "Land" in depts
    assert "Legal" in depts
    assert "ATP" in depts
    assert max_days == 25


def test_renovation_forwarded_with_all_dept_comments():
    """When all depts have commented, and JEN has inspected, application is not overdue."""
    now = datetime.now()
    app = MagicMock()
    app.status = ApplicationStatus.FORWARDED
    app.type = ApplicationType.RENOVATION
    app.created_at = now - timedelta(days=25)
    app.action_logs = []
    
    # Comments from all 3 depts
    c_land = MagicMock()
    c_land.commenter.role = UserRole.DEPT_LAND
    c_legal = MagicMock()
    c_legal.commenter.role = UserRole.DEPT_LEGAL
    c_atp = MagicMock()
    c_atp.commenter.role = UserRole.DEPT_ATP
    app.comments = [c_land, c_legal, c_atp]

    app.inspections = [MagicMock()]
    app.phase_materials = [MagicMock()]
    app.objections = []

    is_overdue, depts, max_days = compute_overdue_info(app, now=now)
    assert not is_overdue
    assert depts == []
    assert max_days is None


def test_approved_pending_jen_inspection_overdue():
    """When application is APPROVED but JEN has not inspected for > 21 days, JEN is overdue."""
    now = datetime.now()
    app = MagicMock()
    app.status = ApplicationStatus.APPROVED
    app.type = ApplicationType.NEW
    app.created_at = now - timedelta(days=22)
    app.action_logs = []
    app.comments = []
    app.inspections = []  # Missing inspection
    app.phase_materials = []
    app.objections = []

    is_overdue, depts, max_days = compute_overdue_info(app, now=now)
    assert is_overdue
    assert depts == ["JEN"]
    assert max_days == 22


def test_under_21_days_not_overdue():
    """Applications under 21 days should not be flagged as overdue."""
    now = datetime.now()
    app = MagicMock()
    app.status = ApplicationStatus.FORWARDED
    app.type = ApplicationType.RENOVATION
    app.created_at = now - timedelta(days=15)
    app.action_logs = []
    app.comments = []
    app.inspections = []
    app.phase_materials = []
    app.objections = []

    is_overdue, depts, max_days = compute_overdue_info(app, now=now)
    assert not is_overdue
    assert depts == []
    assert max_days is None
