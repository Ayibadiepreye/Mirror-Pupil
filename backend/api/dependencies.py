"""
Mirror Pupil v5.1 - API Dependencies
Shared dependency injection functions to avoid circular imports.
"""

from ..database import DatabaseManager
from ..core.trade_executor import TradeExecutor

# Global instances (initialized in main.py lifespan)
_db: DatabaseManager = None
_executor: TradeExecutor = None


def set_db(database: DatabaseManager):
    """Set the global database instance."""
    global _db
    _db = database


def set_executor(executor: TradeExecutor):
    """Set the global executor instance."""
    global _executor
    _executor = executor


def get_db() -> DatabaseManager:
    """Get database instance for dependency injection."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


def get_executor() -> TradeExecutor:
    """Get executor instance for dependency injection."""
    if _executor is None:
        raise RuntimeError("Executor not initialized")
    return _executor
