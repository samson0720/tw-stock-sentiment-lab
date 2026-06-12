from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import execute_script
from app.db.migrations import migrate


def main() -> None:
    if os.getenv("DATABASE_URL"):
        schema_path = ROOT / "app" / "db" / "schema_pg.sql"
        execute_script(schema_path.read_text(encoding="utf-8"))
        print("Initialized PostgreSQL database.")
    else:
        from app.db.database import get_db_path
        schema_path = ROOT / "app" / "db" / "schema.sql"
        execute_script(schema_path.read_text(encoding="utf-8"))
        migrate()
        print(f"Initialized SQLite database: {get_db_path()}")


if __name__ == "__main__":
    main()
