from enum import Enum as PyEnum


class AuditAction(str, PyEnum):
    CHANGED = "CHANGED"
    CREATED = "CREATED"
    VIEWED = "VIEWED"
