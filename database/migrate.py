"""
Simple numbered migration runner (like Laravel/Rails migrations, but plain SQL).

Applies every .sql file inside database/migrations/ in filename order
(001_..., 002_..., etc.) that hasn't been applied yet. Keeps track of what
has already run in a `schema_migrations` table so it's safe to re-run.

Usage:
    python database/migrate.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text

from backend.config import Config

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def run():
    if Config.USE_SQLITE:
        print(
            "USE_SQLITE=1 is set in your .env file.\n"
            "This migrate.py script contains MySQL-specific SQL and is meant for a real "
            "MySQL database only.\n\n"
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
            path = os.path.join(MIGRATIONS_DIR, filename)
            with open(path, "r") as f:
                sql = f.read()

            print(f"Applying {filename} ...")
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))

            conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:filename)"),
                {"filename": filename},
            )
            print(f"  -> done")

    print(f"Applied {len(pending)} migration(s) successfully.")


if __name__ == "__main__":
    run()
