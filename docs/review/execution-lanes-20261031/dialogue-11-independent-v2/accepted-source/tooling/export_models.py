"""Export native declarations without connecting to or initializing a database."""
from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "observer_runtime"))
from app.models import metadata
from bo_observer.data.catalog import export_sqlalchemy_metadata
if __name__ == "__main__":
    print(json.dumps(export_sqlalchemy_metadata(metadata, "team_files"), ensure_ascii=False))
