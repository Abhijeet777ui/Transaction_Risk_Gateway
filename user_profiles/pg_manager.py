"""
PostgreSQL-backed User Profile Manager.
Replaces user_profiles/manager.py (SQLite) with async SQLAlchemy operations.
The public interface (get_user, create_user, record_transaction,
increment_failed_attempt) is unchanged so main.py requires minimal edits.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User

logger = logging.getLogger(__name__)


class PGUserProfileManager:
    """Async user profile manager backed by PostgreSQL."""

    async def get_user(self, session: AsyncSession, user_id: str) -> dict | None:
        """Fetch a user profile as a dict. Returns None if not found."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None

    async def create_user(self, session: AsyncSession, user_id: str, residence_country: str = "XX") -> dict:
        """Create a new user profile and persist it."""
        user = User(
            id=user_id,
            created_at=datetime.utcnow(),
            residence_country=residence_country,
            known_recipients=[],
            known_countries=[],
            transaction_history=[],
            failed_attempts=0,
        )
        session.add(user)
        await session.flush()
        return user.to_dict()

    async def record_transaction(self, session: AsyncSession, user_id: str, transaction: dict, decision: str):
        """
        Update the user's known lists and transaction history.
        Only 'allow' decisions add recipients/countries to known lists.
        """
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"record_transaction: user {user_id} not found")
            return

        if decision == "allow":
            recipient = transaction.get("recipient_id")
            country = transaction.get("destination_country")
            timestamp = transaction.get("timestamp")

            known_recipients = list(user.known_recipients or [])
            known_countries = list(user.known_countries or [])
            history = list(user.transaction_history or [])

            if recipient and recipient not in known_recipients:
                known_recipients.append(recipient)

            if country and country not in known_countries:
                known_countries.append(country)

            tx_record: dict = {"amount": transaction.get("amount", 0)}
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    tx_record["hour"] = dt.hour
                except Exception:
                    pass

            history.append(tx_record)
            # Cap history at 500 entries to avoid unbounded JSONB growth
            history = history[-500:]

            user.known_recipients = known_recipients
            user.known_countries = known_countries
            user.transaction_history = history
            user.failed_attempts = 0  # Reset on successful allow

        await session.flush()

    async def increment_failed_attempt(self, session: AsyncSession, user_id: str):
        """Increment failed attempt counter for a user."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            await session.flush()
        else:
            logger.warning(f"increment_failed_attempt: user {user_id} not found")
