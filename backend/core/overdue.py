from datetime import datetime
from typing import Optional, Any
from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    UserRole,
    ObjectionStatus,
)

DEPT_DISPLAY_NAMES = {
    UserRole.DEPT_LAND: "Land",
    UserRole.DEPT_LEGAL: "Legal",
    UserRole.DEPT_ATP: "ATP",
    UserRole.JEN: "JEN",
}

OVERDUE_THRESHOLD_DAYS = 21


def get_app_last_updated_at(app: Any) -> datetime:
    """Return latest action log timestamp or created_at."""
    action_logs = getattr(app, "action_logs", None)
    if not action_logs and isinstance(app, dict):
        action_logs = app.get("action_logs")
    if action_logs:
        log_ts = []
        for log in action_logs:
            ts = getattr(log, "performed_at", None) if not isinstance(log, dict) else log.get("performed_at")
            if ts:
                log_ts.append(ts)
        if log_ts:
            return max(log_ts)
    created_at = getattr(app, "created_at", None) if not isinstance(app, dict) else app.get("created_at")
    return created_at or datetime.now()


def compute_overdue_info(app: Any, now: Optional[datetime] = None) -> tuple[bool, list[str], Optional[int]]:
    """
    Check if an application is pending with Land, Legal, ATP, or JEN for > 21 days.
    NOTE: Applications in SUBMITTED state are NEVER counted as overdue.

    Returns:
        (is_overdue, overdue_departments, max_overdue_days)
    """
    status = getattr(app, "status", None) if not isinstance(app, dict) else app.get("status")
    if hasattr(status, "value"):
        status = status.value

    # Explicit requirement: Do not count applications in SUBMITTED state
    if status == ApplicationStatus.SUBMITTED.value or status == "SUBMITTED":
        return False, [], None

    app_type = getattr(app, "type", None) if not isinstance(app, dict) else app.get("type")
    if hasattr(app_type, "value"):
        app_type = app_type.value

    if not now:
        now = datetime.now()

    overdue_depts: list[str] = []
    max_days: int = 0

    # 1. Check JEN
    jen_pending_ts = None
    inspections = getattr(app, "inspections", None) if not isinstance(app, dict) else app.get("inspections")
    phase_materials = getattr(app, "phase_materials", None) if not isinstance(app, dict) else app.get("phase_materials")

    if status in (ApplicationStatus.FORWARDED.value, ApplicationStatus.APPROVED.value, "FORWARDED", "APPROVED"):
        if not inspections or not phase_materials:
            jen_pending_ts = get_app_last_updated_at(app)
    elif status in (ApplicationStatus.OBJECTED.value, "OBJECTED"):
        objections = getattr(app, "objections", None) if not isinstance(app, dict) else app.get("objections")
        if objections:
            pending_objs = [
                o for o in objections
                if (getattr(o, "status", None) == ObjectionStatus.PENDING or (isinstance(o, dict) and o.get("status") in (ObjectionStatus.PENDING, "PENDING")))
                and (getattr(o, "objected_to_role", None) == UserRole.JEN or (isinstance(o, dict) and o.get("objected_to_role") in (UserRole.JEN, "JEN")))
            ]
            if pending_objs:
                jen_pending_ts = min([
                    (getattr(o, "created_at", None) if not isinstance(o, dict) else o.get("created_at"))
                    for o in pending_objs
                    if (getattr(o, "created_at", None) if not isinstance(o, dict) else o.get("created_at")) is not None
                ], default=None)

    if jen_pending_ts:
        if jen_pending_ts.tzinfo and not now.tzinfo:
            curr_now = datetime.now(jen_pending_ts.tzinfo)
        elif not jen_pending_ts.tzinfo and now.tzinfo:
            curr_now = now.replace(tzinfo=None)
        else:
            curr_now = now
        elapsed = (curr_now - jen_pending_ts).days
        if elapsed > OVERDUE_THRESHOLD_DAYS:
            overdue_depts.append("JEN")
            if elapsed > max_days:
                max_days = elapsed

    # 2. Check DEPT_LAND, DEPT_LEGAL, DEPT_ATP
    dept_roles = [
        (UserRole.DEPT_LAND, "Land"),
        (UserRole.DEPT_LEGAL, "Legal"),
        (UserRole.DEPT_ATP, "ATP"),
    ]

    comments = getattr(app, "comments", None) if not isinstance(app, dict) else app.get("comments")
    commented_roles = set()
    if comments:
        for c in comments:
            commenter = getattr(c, "commenter", None) if not isinstance(c, dict) else c.get("commenter")
            role = getattr(commenter, "role", None) if not isinstance(commenter, dict) else (commenter.get("role") if commenter else None)
            if hasattr(role, "value"):
                role = role.value
            if role:
                commented_roles.add(role)

    objections = getattr(app, "objections", None) if not isinstance(app, dict) else app.get("objections")

    for dept_role, dept_name in dept_roles:
        dept_pending_ts = None
        role_val = dept_role.value if hasattr(dept_role, "value") else dept_role

        if (
            (app_type == ApplicationType.RENOVATION.value or app_type == "RENOVATION")
            and status in (ApplicationStatus.FORWARDED.value, "FORWARDED")
        ):
            if role_val not in commented_roles and dept_role not in commented_roles:
                dept_pending_ts = get_app_last_updated_at(app)
        elif status in (ApplicationStatus.OBJECTED.value, "OBJECTED"):
            if objections:
                pending_objs = [
                    o for o in objections
                    if (getattr(o, "status", None) == ObjectionStatus.PENDING or (isinstance(o, dict) and o.get("status") in (ObjectionStatus.PENDING, "PENDING")))
                    and (getattr(o, "objected_to_role", None) == dept_role or (isinstance(o, dict) and o.get("objected_to_role") in (dept_role, role_val)))
                ]
                if pending_objs:
                    dept_pending_ts = min([
                        (getattr(o, "created_at", None) if not isinstance(o, dict) else o.get("created_at"))
                        for o in pending_objs
                        if (getattr(o, "created_at", None) if not isinstance(o, dict) else o.get("created_at")) is not None
                    ], default=None)

        if dept_pending_ts:
            if dept_pending_ts.tzinfo and not now.tzinfo:
                curr_now = datetime.now(dept_pending_ts.tzinfo)
            elif not dept_pending_ts.tzinfo and now.tzinfo:
                curr_now = now.replace(tzinfo=None)
            else:
                curr_now = now
            elapsed = (curr_now - dept_pending_ts).days
            if elapsed > OVERDUE_THRESHOLD_DAYS:
                overdue_depts.append(dept_name)
                if elapsed > max_days:
                    max_days = elapsed

    is_overdue = len(overdue_depts) > 0
    return is_overdue, overdue_depts, (max_days if is_overdue else None)
