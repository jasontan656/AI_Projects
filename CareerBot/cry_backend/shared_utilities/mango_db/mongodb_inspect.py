#!/usr/bin/env python3
import sys
from pathlib import Path

from hub.logger import info

LOG_CONTEXT = {
    'trace_id': 'system-maintenance',
    'request_id': 'system-maintenance',
    'route_path': 'maintenance/db-inspect',
}

def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from shared_utilities.mango_db.mongodb_connector import DatabaseOperations, COLLECTIONS
    db = DatabaseOperations().db
    info('maintenance.inspect.db', database=db.name, **LOG_CONTEXT)
    for name in COLLECTIONS:
        cnt = db[name].count_documents({})
        info('maintenance.inspect.collection', collection=name, document_count=cnt, **LOG_CONTEXT)

if __name__ == "__main__":
    main()


