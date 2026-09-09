"""
Backs up ALL data from your database into a single timestamped JSON file.

Run this BEFORE any risky change (schema updates, manual database edits,
or just as a regular safety habit -- e.g. once a week).

Usage:
    python database/backup.py

Creates a file like: database/backups/backup_2026-09-08_14-30.json
"""

import json
import os
import sys
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect, select

from backend import create_app
from backend.extensions import db

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backups")


def json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def run():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        live_tables = set(inspector.get_table_names())

        data = {}
        for table in db.metadata.sorted_tables:
            if table.name not in live_tables:
                # Model defines a table that doesn't exist on the live DB yet
                # (e.g. a brand-new feature not migrated in) -- nothing to back up.
                data[table.name] = []
                continue

            # Only select columns that actually exist on the LIVE table right
            # now. If a model has a newer column that hasn't been migrated in
            # yet, this backup still succeeds -- it just won't include that
            # column (there's nothing to back up for it anyway).
            live_column_names = {c["name"] for c in inspector.get_columns(table.name)}
            columns_to_select = [c for c in table.columns if c.name in live_column_names]

            if not columns_to_select:
                data[table.name] = []
                continue

            stmt = select(*columns_to_select)
            rows = db.session.execute(stmt).mappings().all()
            data[table.name] = [
                {k: json_safe(v) for k, v in dict(row).items()} for row in rows
            ]

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        total_rows = sum(len(v) for v in data.values())
        print(f"Backup saved to: {path}")
        print(f"Tables backed up: {len(data)}, total rows: {total_rows}")
        for table_name, rows in data.items():
            print(f"  {table_name}: {len(rows)} rows")


if __name__ == "__main__":
    run()
