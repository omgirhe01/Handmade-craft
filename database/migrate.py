"""
Safe, idempotent migration runner.

Applies every .sql file inside database/migrations/ in filename order that
hasn't been marked as applied yet, tracked in a `schema_migrations` table.

Unlike a plain SQL runner, this one actually LOOKS at your live database
before running each piece of a migration:
  - CREATE TABLE ... -> skipped if the table already exists
  - ALTER TABLE ... ADD COLUMN ... (one or many, comma-separated) -> each
    column is checked individually; only the columns that are actually
    missing get added
  - CREATE INDEX ... ON ... -> skipped if that index already exists
  - Anything else runs as written, but if MySQL reports "already exists" /
    "duplicate column" / "duplicate key", it's treated as already-done and
    skipped instead of crashing the whole run.

This means:
  - You can write plain `ADD COLUMN` / `CREATE INDEX` statements without
    worrying about `IF NOT EXISTS` support (which varies between MySQL and
    MariaDB versions and was causing syntax errors here).
  - If a migration partially applied because of an earlier crash, simply
    re-running `python database/migrate.py` will finish the rest safely --
    it will never try to re-add something that's already there, and it
    will never touch or delete existing data/rows.

Usage:
    python database/migrate.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError, OperationalError

from backend.config import Config

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

# MySQL/MariaDB error codes that mean "this already exists" -- safe to skip.
ALREADY_EXISTS_CODES = {1050, 1060, 1061, 1091}  # table/column/index exists, or can't DROP (doesn't exist)

CREATE_TABLE_RE = re.compile(r"^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?", re.IGNORECASE)
ALTER_TABLE_RE = re.compile(r"^\s*ALTER\s+TABLE\s+`?(\w+)`?\s+(.*)$", re.IGNORECASE | re.DOTALL)
ADD_COLUMN_RE = re.compile(
    r"ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s+(.*)", re.IGNORECASE | re.DOTALL
)
CREATE_INDEX_RE = re.compile(
    r"^\s*CREATE\s+(?:UNIQUE\s+)?INDEX\s+`?(\w+)`?\s+ON\s+`?(\w+)`?", re.IGNORECASE
)


def split_top_level(text_block, sep=","):
    """Split on `sep` but ignore any that are inside parentheses, e.g. DECIMAL(10,2)."""
    parts = []
    depth = 0
    current = ""
    for ch in text_block:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)
    return [p.strip() for p in parts]


def existing_columns(inspector, table_name):
    try:
        return {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return set()


def existing_indexes(inspector, table_name):
    try:
        return {i["name"] for i in inspector.get_indexes(table_name)}
    except Exception:
        return set()


def run_alter_table(conn, inspector, table_name, clauses_text):
    """Filter an ALTER TABLE's ADD COLUMN clauses down to only the missing columns."""
    live_columns = existing_columns(inspector, table_name)
    clauses = split_top_level(clauses_text)

    to_add = []
    added_names = []
    for clause in clauses:
        match = ADD_COLUMN_RE.match(clause.strip())
        if not match:
            # Not an ADD COLUMN clause (e.g. DROP COLUMN, MODIFY, etc.) --
            # keep it as-is and let the database validate it.
            to_add.append(clause.strip())
            continue

        col_name = match.group(1)
        if col_name in live_columns:
            print(f"    - column '{col_name}' already exists on '{table_name}', skipping")
            continue

        # Rebuild the clause without "IF NOT EXISTS" (not universally supported)
        rest = match.group(2)
        to_add.append(f"ADD COLUMN {col_name} {rest}")
        added_names.append(col_name)

    if not to_add:
        print(f"    (nothing to add -- '{table_name}' already up to date)")
        return

    statement = f"ALTER TABLE {table_name} " + ", ".join(to_add)
    conn.execute(text(statement))
    print(f"    -> added: {', '.join(added_names) if added_names else '(non-column changes)'}")


def run_statement(conn, inspector, statement):
    statement = statement.strip()
    if not statement:
        return

    create_match = CREATE_TABLE_RE.match(statement)
    if create_match:
        table_name = create_match.group(1)
        if table_name in inspector.get_table_names():
            print(f"  - table '{table_name}' already exists, skipping")
            return
        conn.execute(text(statement))
        print(f"  -> created table '{table_name}'")
        return

    alter_match = ALTER_TABLE_RE.match(statement)
    if alter_match:
        table_name, clauses_text = alter_match.group(1), alter_match.group(2)
        run_alter_table(conn, inspector, table_name, clauses_text)
        return

    index_match = CREATE_INDEX_RE.match(statement)
    if index_match:
        index_name, table_name = index_match.group(1), index_match.group(2)
        if index_name in existing_indexes(inspector, table_name):
            print(f"  - index '{index_name}' already exists, skipping")
            return
        conn.execute(text(statement))
        print(f"  -> created index '{index_name}'")
        return

    # Fallback for anything else (DROP TABLE, INSERT, custom SQL, etc.)
    # -- run it, but don't crash the whole migration if it turns out to
    # already be done.
    try:
        conn.execute(text(statement))
        print("  -> done")
    except (ProgrammingError, OperationalError) as e:
        orig_args = getattr(e.orig, "args", ())
        code = orig_args[0] if orig_args else None
        if code in ALREADY_EXISTS_CODES:
            print(f"  - already applied (MySQL error {code}), skipping")
        else:
            raise


def run():
    if Config.USE_SQLITE:
        print(
            "USE_SQLITE=1 is set in your .env file.\n"
            "This migrate.py script is meant for a real MySQL database only.\n\n"
            "For the SQLite quick-demo mode, you don't need to run this at all -- just run:\n"
            "    python database/seed.py\n"
            "It creates the correct SQLite tables automatically.\n\n"
            "If you want to use MySQL instead, set USE_SQLITE=0 in your .env file and fill in "
            "your MYSQL_* credentials, then run this script again."
        )
        return

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))

        applied = {
            row[0] for row in conn.execute(text("SELECT filename FROM schema_migrations"))
        }

        migration_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
        pending = [f for f in migration_files if f not in applied]

        if not pending:
            print("No pending migrations. Database is up to date.")
            return

        for filename in pending:
            inspector = inspect(conn)  # re-inspect fresh each file, since the schema may have changed
            path = os.path.join(MIGRATIONS_DIR, filename)
            with open(path, "r", newline="") as f:
                sql = f.read().replace("\r\n", "\n").replace("\r", "\n")

            print(f"Applying {filename} ...")

            # Strip full-line SQL comments before splitting on ';' so a
            # comment containing a semicolon-like character never confuses
            # the statement splitter.
            lines = [ln for ln in sql.split("\n") if not ln.strip().startswith("--")]
            cleaned_sql = "\n".join(lines)

            for statement in cleaned_sql.split(";"):
                run_statement(conn, inspector, statement)
                inspector = inspect(conn)  # refresh after each statement (columns/tables may have changed)

            conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:filename)"),
                {"filename": filename},
            )
            print("  \u2713 migration recorded as applied\n")

    print(f"Applied {len(pending)} migration(s) successfully.")


if __name__ == "__main__":
    run()