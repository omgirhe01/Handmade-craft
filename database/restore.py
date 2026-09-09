"""
Restores data from a backup JSON file created by database/backup.py.

Only INSERTs rows that don't already exist (matched by primary key), so it's
safe to run even if some data is already present -- it will not duplicate
rows or touch anything not in the backup file.

Usage:
    python database/restore.py database/backups/backup_2026-09-08_14-30.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import create_app
from backend.extensions import db


def run(backup_path):
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return

    with open(backup_path) as f:
        data = json.load(f)

    app = create_app()
    with app.app_context():
        db.create_all()  # make sure tables exist before restoring into them

        tables_by_name = {t.name: t for t in db.metadata.sorted_tables}

        for table_name, rows in data.items():
            table = tables_by_name.get(table_name)
            if table is None:
                print(f"Skipping unknown table: {table_name}")
                continue

            pk_cols = [c.name for c in table.primary_key.columns]
            restored = 0

            for row in rows:
                if pk_cols:
                    pk_filter = {c: row[c] for c in pk_cols if c in row}
                    exists = db.session.execute(
                        table.select().filter_by(**pk_filter)
                    ).first()
                    if exists:
                        continue  # already there -- don't duplicate or overwrite

                db.session.execute(table.insert().values(**row))
                restored += 1

            db.session.commit()
            print(f"{table_name}: restored {restored} of {len(rows)} rows "
                  f"(rest already existed)")

    print("\nRestore complete.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python database/restore.py <path-to-backup.json>")
        sys.exit(1)
    run(sys.argv[1])
