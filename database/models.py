"""
SQLAlchemy ORM models for PostgreSQL.

Tables:
  - users        : User profiles and behavioral history
  - transactions : Lightweight record of processed transactions
  - audit_logs   : Full immutable audit trail of every decision
                   (partitioned by month in production via manual SQL)
"""
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Text, DateTime, Boolean,
    ForeignKey, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    residence_country: Mapped[str] = mapped_column(String(2), default="XX")

    # Arrays stored as JSONB for flexibility (avoids PostgreSQL array type complexity)
    known_recipients: Mapped[dict] = mapped_column(JSONB, default=list)
    known_countries: Mapped[dict] = mapped_column(JSONB, default=list)
    transaction_history: Mapped[dict] = mapped_column(JSONB, default=list)

    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    account_locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="noload")

    __table_args__ = (
        Index("idx_users_country", "residence_country"),
        Index("idx_users_locked", "account_locked_until"),
    )

    def to_dict(self) -> dict:
        """Returns the dict structure expected by rules/ml/lm layers."""
        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        created = self.created_at.replace(tzinfo=None) if self.created_at.tzinfo else self.created_at
        account_age = max((now - created).days, 0)

        history = self.transaction_history or []
        typical_hours = list({tx["hour"] for tx in history if "hour" in tx})

        return {
            "id": self.id,
            "account_age": account_age,
            "created_at": self.created_at.isoformat(),
            "known_recipients": self.known_recipients or [],
            "known_countries": self.known_countries or [],
            "residence_country": self.residence_country,
            "typical_transaction_hours": typical_hours,
            "failed_attempts_in_last_hour": self.failed_attempts,
            "transaction_history": history,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Full transaction payload
    transaction: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # All layer signals (rules, ml, lm, fallbacks)
    signals: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Decision output
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    combined_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    required_actions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Post-decision human review (filled in later)
    human_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appeal_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    system_version: Mapped[str] = mapped_column(String(20), default="2.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "timestamp"),
        Index("idx_audit_decision", "decision"),
        Index("idx_audit_timestamp", "timestamp"),
    )
