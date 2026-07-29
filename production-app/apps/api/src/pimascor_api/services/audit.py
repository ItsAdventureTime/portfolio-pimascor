from sqlalchemy.orm import Session

from ..models import AuditEvent


def record_audit(
    db: Session,
    *,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    correlation_id: str | None = None,
    reason: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        reason=reason,
    )
    db.add(event)
    return event
