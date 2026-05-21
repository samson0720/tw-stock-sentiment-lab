from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.daily_sentiment import build_daily_sentiment


if __name__ == "__main__":
    count = build_daily_sentiment()
    print(f"Daily sentiment rows: {count}")
