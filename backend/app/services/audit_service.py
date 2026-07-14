from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    async def log_event(
        session: AsyncSession,
        *,
        actor_user_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        metadata: dict | None = None,
        metadata_json: dict | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata if metadata is not None else metadata_json,
        )
        session.add(audit_log)
        await session.flush()
        return audit_log
