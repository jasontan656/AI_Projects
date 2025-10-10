#!/usr/bin/env python3
import sys
from pathlib import Path

from hub.logger import info, warning, error

LOG_CONTEXT = {
    'trace_id': 'system-maintenance',
    'request_id': 'system-maintenance',
    'route_path': 'maintenance/db-cleanup',
}

def cleanup_database() -> bool:
    info('maintenance.cleanup.start', **LOG_CONTEXT)
    try:
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from shared_utilities.mango_db.mongodb_connector import DatabaseOperations, COLLECTIONS
        db_ops = DatabaseOperations()
        db = db_ops.db
        info('maintenance.cleanup.db_connected', database=db.name, **LOG_CONTEXT)
        info('maintenance.cleanup.collections', collections=COLLECTIONS, **LOG_CONTEXT)
        for name in COLLECTIONS:
            try:
                res = db[name].delete_many({})
                info('maintenance.cleanup.collection_cleared', collection=name, deleted_count=res.deleted_count, **LOG_CONTEXT)
            except Exception as e:
                warning('maintenance.cleanup.collection_failed', collection=name, error=str(e), **LOG_CONTEXT)
        try:
            db_ops.ensure_indexes()
            info('maintenance.cleanup.indexes_ok', **LOG_CONTEXT)
        except Exception as e:
            warning('maintenance.cleanup.indexes_failed', error=str(e), **LOG_CONTEXT)
        return True
    except Exception as e:
        error('maintenance.cleanup.failed', error=str(e), **LOG_CONTEXT)
        return False

if __name__ == "__main__":
    sys.exit(0 if cleanup_database() else 1)


