"""
PostgreSQL-backed Audit Logger.
Replaces the SQLite audit/logger.py with async SQLAlchemy writes.
The public interface (log, query_by_user, query_by_transaction) is unchanged
so main.py requires minimal edits.
"""
import json
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from audit.schema import AuditLog as AuditLogSchema
from database.models import AuditLog as AuditLogModel

logger = logging.getLogger(__name__)


class PGAuditLogger:
    """Async audit logger backed by PostgreSQL."""

    async def log(self, session: AsyncSession, entry: AuditLogSchema) -> int | None:
        """
        Persist a decision audit record.
        Returns the new row ID, or None if the transaction_id already exists.
        """
        record = AuditLogModel(
            transaction_id=entry.transaction_id,
            user_id=entry.user_id,
            timestamp=entry.timestamp,
            transaction=entry.transaction,
            signals=entry.signals,
            decision=entry.decision,
            combined_risk_score=entry.combined_risk_score,
            required_actions=entry.required_actions,
            reasoning=entry.reasoning,
        )
        try:
            session.add(record)
            await session.flush()   # Assigns the auto-generated id
            return record.id
        except Exception as e:
            # Duplicate transaction_id or other constraint violation
            logger.warning(f"Audit log skipped for {entry.transaction_id}: {e}")
            await session.rollback()
            return None

    async def query_by_user(self, session: AsyncSession, user_id: str, limit: int = 100) -> list[dict]:
        """Return the most recent audit records for a user."""
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]

    async def query_by_transaction(self, session: AsyncSession, transaction_id: str) -> dict | None:
        """Return the audit record for a specific transaction."""
        stmt = select(AuditLogModel).where(AuditLogModel.transaction_id == transaction_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_dict(row) if row else None

    def _to_dict(self, row: AuditLogModel) -> dict:
        return {
            "id": row.id,
            "transaction_id": row.transaction_id,
            "user_id": row.user_id,
            "timestamp": row.timestamp.isoformat(),
            "decision": row.decision,
            "combined_risk_score": row.combined_risk_score,
            "required_actions": row.required_actions,
            "reasoning": row.reasoning,
            "signals": row.signals,
            "transaction": row.transaction,
            "human_decision": row.human_decision,
            "reviewer_id": row.reviewer_id,
            "appeal_status": row.appeal_status,
        }
