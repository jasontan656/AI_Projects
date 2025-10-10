from .mongodb_connector import DatabaseOperations

def ensure_core_indexes() -> None:
    DatabaseOperations().ensure_indexes()

__all__ = ["ensure_core_indexes"]


