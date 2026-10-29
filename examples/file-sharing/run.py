"""Run the repaired file-sharing application and its native state/rule executor."""
import argparse
from pathlib import Path
from app.web import create_app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8879)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    app = create_app(Path(__file__).resolve().parent)
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
