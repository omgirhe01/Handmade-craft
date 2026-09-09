"""
Safe, automatic migration generator.

Whenever you change a model (add a new field/column), run this script.
It connects to your CURRENT database (whatever is set in .env), compares
it against your SQLAlchemy models, and -- if anything is missing -- writes
a brand-new numbered migration file containing ONLY safe, additive
statements (ALTER TABLE ... ADD COLUMN ...). It NEVER drops a table and
NEVER deletes a column, so your existing data is always preserved.

Usage:
    python database/generate_migration.py

Then apply it the normal way:
    python database/migrate.py

If nothing has changed, it simply tells you the schema is already in sync
and does not create an empty file.
"""

import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, inspect

from backend.config import Config
from backend.extensions import db
from backend import create_app
import backend.models  # noqa: F401  (imports every model so metadata is populated)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

# Map SQLAlchemy column types to MySQL column definitions for ALTER statements.
def sql_type_for(column):
    t = column.type
    type_name = type(t).__name__

    if type_name == "Integer":
        return "INT"
    if type_name == "String":
        length = getattr(t, "length", None) or 255
        return f"VARCHAR({length})"
    if type_name == "Text":
        return "TEXT"
    if type_name == "Numeric":
        precision = getattr(t, "precision", 10) or 10
        scale = getattr(t, "scale", 2) or 2
        return f"DECIMAL({precision},{scale})"
    if type_name == "Boolean":
        return "BOOLEAN"
    if type_name == "DateTime":
        return "DATETIME"
    if type_name == "Float":
        return "FLOAT"
    # Fallback -- safe default that fits most cases
    return "VARCHAR(255)"


def default_clause(column):
    if column.default is not None and column.default.is_scalar:
        val = column.default.arg
        if isinstance(val, bool):
            return f" DEFAULT {1 if val else 0}"
        if isinstance(val, (int, float)):
            return f" DEFAULT {val}"
        if isinstance(val, str):
            escaped = val.replace("'", "''")
            return f" DEFAULT '{escaped}'"
    return ""


def next_migration_number():
    existing = [f for f in os.listdir(MIGRATIONS_DIR) if re.match(r"^\d+_", f)]
    if not existing:
        return "001"
    numbers = [int(f.split("_")[0]) for f in existing]
    return f"{max(numbers) + 1:03d}"


def run():
    if Config.USE_SQLITE:
        print(
            "USE_SQLITE=1 is set in your .env file.\n"
            "This tool generates MySQL-specific ALTER TABLE statements and is meant to run "
            "against your real MySQL database.\n"
            "Set USE_SQLITE=0 with your MySQL credentials in .env, then run this again."
        )
        return

    app = create_app()
    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        statements = []
        summary_lines = []

        for table in db.metadata.sorted_tables:
            table_name = table.name

            if table_name not in existing_tables:
                # A brand new table -- safe to CREATE, nothing to lose.
                from sqlalchemy.schema import CreateTable
                create_sql = str(CreateTable(table).compile(engine)).strip() + ";"
                statements.append(create_sql)
                summary_lines.append(f"  + new table '{table_name}'")
                continue

            live_columns = {c["name"] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in live_columns:
                    continue
                # Column missing on the live table -- add it without touching
                # any existing rows or columns.
                col_type = sql_type_for(column)
                nullability = "" if column.nullable else " NOT NULL"
                default = default_clause(column)
                stmt = (
                    f"ALTER TABLE {table_name} ADD COLUMN {column.name} "
                    f"{col_type}{default}{nullability};"
                )
                statements.append(stmt)
                summary_lines.append(f"  + {table_name}.{column.name}")

        if not statements:
            print("Schema is already in sync with your models -- nothing to do.")
            return

        number = next_migration_number()
        timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{number}_auto_sync_schema_{timestamp_suffix}.sql"
        path = os.path.join(MIGRATIONS_DIR, filename)

        header = (
            f"-- Auto-generated migration ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
            "-- Adds missing columns/tables detected between your models and the live "
            "database.\n"
            "-- Additive only: no DROP, no DELETE -- existing data is never touched.\n\n"
        )

        with open(path, "w") as f:
            f.write(header)
            f.write("\n".join(statements) + "\n")

        print(f"Created migration: database/migrations/{filename}")
        print("Changes detected:")
        print("\n".join(summary_lines))
        print("\nNow run:  python database/migrate.py")


if __name__ == "__main__":
    run()
