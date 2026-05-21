from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.returns import build_aligned_returns


if __name__ == "__main__":
    count = build_aligned_returns()
    print(f"Aligned news return rows: {count}")
