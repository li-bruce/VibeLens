"""Export SQLAlchemy metadata without opening or changing the application database."""

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"observer_runtime")]
from app.models import metadata
from bo_observer.data.catalog import export_sqlalchemy_metadata

if __name__=="__main__":
    print(json.dumps(export_sqlalchemy_metadata(metadata,"application")))
