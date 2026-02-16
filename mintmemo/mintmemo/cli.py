from __future__ import annotations

import argparse

import uvicorn

from .config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="mintmemo", description="MintMemo - local-first Markdown note vault.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run the web server")
    run.add_argument("--host", default=None, help="Bind host (override MINTMEMO_HOST)")
    run.add_argument("--port", type=int, default=None, help="Bind port (override MINTMEMO_PORT)")

    args = parser.parse_args()
    settings = load_settings()

    host = args.host or settings.host
    port = args.port or settings.port

    uvicorn.run("mintmemo.web:app", host=host, port=port, reload=False, log_level="info")
