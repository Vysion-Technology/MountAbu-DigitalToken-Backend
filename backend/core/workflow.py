"""
Application workflow state machine.

Defines valid transitions: (current_status, action, app_type, required_role) -> next_status

This is the single source of truth for what actions are allowed and by whom.
"""

from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    UserRole,
    WorkflowAction,
)

# (current_status, action, app_type) -> (next_status, allowed_roles)
TRANSITIONS: dict[
    tuple[ApplicationStatus, WorkflowAction, ApplicationType],
    tuple[ApplicationStatus, list[UserRole]],
] = {
    # =====================================================================
    # NEW CONSTRUCTION FLOW
    # =====================================================================
    # 1. Citizen submits -> Nodal Officer sees it (SUBMITTED)
    # 2. Nodal Officer approves -> JEN inspection
    (ApplicationStatus.SUBMITTED, WorkflowAction.APPROVE, ApplicationType.NEW): (
        ApplicationStatus.APPROVED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 2a. Nodal Officer rejects
    (ApplicationStatus.SUBMITTED, WorkflowAction.REJECT, ApplicationType.NEW): (
        ApplicationStatus.REJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 2b. Nodal Officer objects (citizen must respond)
    (ApplicationStatus.SUBMITTED, WorkflowAction.OBJECT, ApplicationType.NEW): (
        ApplicationStatus.OBJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 3. After citizen responds to objection, Nodal can re-approve
    (ApplicationStatus.OBJECTED, WorkflowAction.APPROVE, ApplicationType.NEW): (
        ApplicationStatus.APPROVED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    (ApplicationStatus.OBJECTED, WorkflowAction.REJECT, ApplicationType.NEW): (
        ApplicationStatus.REJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    (ApplicationStatus.OBJECTED, WorkflowAction.OBJECT, ApplicationType.NEW): (
        ApplicationStatus.OBJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 4. After JEN inspection + material entry, Nodal generates tokens
    (ApplicationStatus.APPROVED, WorkflowAction.GENERATE_TOKENS, ApplicationType.NEW): (
        ApplicationStatus.TOKEN_GENERATED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 4a. Allow sequential token generation when status is TOKEN_GENERATED
    (ApplicationStatus.TOKEN_GENERATED, WorkflowAction.GENERATE_TOKENS, ApplicationType.NEW): (
        ApplicationStatus.TOKEN_GENERATED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 4b. Nodal Officer can also reject at this stage
    (ApplicationStatus.APPROVED, WorkflowAction.REJECT, ApplicationType.NEW): (
        ApplicationStatus.REJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 4c. Nodal Officer can object at this stage
    (ApplicationStatus.APPROVED, WorkflowAction.OBJECT, ApplicationType.NEW): (
        ApplicationStatus.OBJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),

    # =====================================================================
    # RENOVATION FLOW
    # =====================================================================
    # 1. Citizen submits -> Commissioner sees it (SUBMITTED)
    # 2. Commissioner forwards to depts (JEN/ATP/LAND/LEGAL)
    (ApplicationStatus.SUBMITTED, WorkflowAction.FORWARD, ApplicationType.RENOVATION): (
        ApplicationStatus.FORWARDED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    # 2a. Commissioner rejects
    (ApplicationStatus.SUBMITTED, WorkflowAction.REJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.REJECTED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    # 2b. Commissioner objects
    (ApplicationStatus.SUBMITTED, WorkflowAction.OBJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.OBJECTED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    # 3. After citizen responds to objection, Commissioner can forward or reject
    (ApplicationStatus.OBJECTED, WorkflowAction.FORWARD, ApplicationType.RENOVATION): (
        ApplicationStatus.FORWARDED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    (ApplicationStatus.OBJECTED, WorkflowAction.REJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.REJECTED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    (ApplicationStatus.OBJECTED, WorkflowAction.OBJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.OBJECTED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    # 4. After all 4 depts comment, Commissioner approves/rejects/objects
    (ApplicationStatus.FORWARDED, WorkflowAction.APPROVE, ApplicationType.RENOVATION): (
        ApplicationStatus.APPROVED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    (ApplicationStatus.FORWARDED, WorkflowAction.REJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.REJECTED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    (ApplicationStatus.FORWARDED, WorkflowAction.OBJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.OBJECTED,
        [UserRole.COMMISSIONER, UserRole.SUPERADMIN],
    ),
    # 5. After Commissioner approves, Nodal Officer generates tokens
    (ApplicationStatus.APPROVED, WorkflowAction.GENERATE_TOKENS, ApplicationType.RENOVATION): (
        ApplicationStatus.TOKEN_GENERATED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 5a. Allow sequential token generation when status is TOKEN_GENERATED
    (ApplicationStatus.TOKEN_GENERATED, WorkflowAction.GENERATE_TOKENS, ApplicationType.RENOVATION): (
        ApplicationStatus.TOKEN_GENERATED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 5a. Nodal Officer can also reject at this stage
    (ApplicationStatus.APPROVED, WorkflowAction.REJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.REJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
    # 5b. Nodal Officer can object at this stage
    (ApplicationStatus.APPROVED, WorkflowAction.OBJECT, ApplicationType.RENOVATION): (
        ApplicationStatus.OBJECTED,
        [UserRole.NODAL_OFFICER, UserRole.SUPERADMIN],
    ),
}


def get_transition(
    current_status: ApplicationStatus,
    action: WorkflowAction,
    app_type: ApplicationType,
) -> tuple[ApplicationStatus, list[UserRole]] | None:
    """Look up a transition. Returns (next_status, allowed_roles) or None if invalid."""
    return TRANSITIONS.get((current_status, action, app_type))


def validate_transition(
    current_status: ApplicationStatus,
    action: WorkflowAction,
    app_type: ApplicationType,
    user_role: UserRole,
) -> ApplicationStatus:
    """
    Validate and return the next status for a workflow transition.
    Raises ValueError with a descriptive message if the transition is invalid.
    """
    result = get_transition(current_status, action, app_type)
    if result is None:
        raise ValueError(
            f"Invalid transition: cannot perform '{action.value}' on a "
            f"'{app_type.value}' application in '{current_status.value}' status."
        )

    next_status, allowed_roles = result
    if user_role not in allowed_roles:
        raise ValueError(
            f"Role '{user_role.value}' is not permitted to perform '{action.value}' "
            f"on a '{app_type.value}' application in '{current_status.value}' status. "
            f"Allowed roles: {[r.value for r in allowed_roles]}"
        )

    return next_status


# Department roles that must comment on RENOVATION before Commissioner can act
RENOVATION_DEPT_ROLES = frozenset([
    UserRole.JEN,
    UserRole.DEPT_ATP,
    UserRole.DEPT_LAND,
    UserRole.DEPT_LEGAL,
])
