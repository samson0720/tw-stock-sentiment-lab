from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import execute_script, get_db_path
from app.db.migrations import migrate


def main() -> None:
    schema_path = ROOT / "app" / "db" / "schema.sql"
    execute_script(schema_path.read_text(encoding="utf-8"))
    migrate()
    print(f"Initialized database: {get_db_path()}")


if __name__ == "__main__":
    main()
