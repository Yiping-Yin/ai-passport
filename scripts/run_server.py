#!/usr/bin/env python3
"""Run the local wiki-first AI Knowledge Passport server."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.server import Application, build_context
from app.storage.migrate import DEFAULT_DB_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    context = build_context(db_path=Path(args.database))
    app = Application(context)
    with make_server(args.host, args.port, app) as server:
        print(f"Serving on http://{args.host}:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
