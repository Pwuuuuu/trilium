from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    host: str = "127.0.0.1"
    port: int = 8000
    auth_user: str | None = None
    auth_pass: str | None = None

    @property
    def auth_enabled(self) -> bool:
        return bool(self.auth_user and self.auth_pass)


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    env = environ or os.environ
    db_path = Path(env.get("MINTMEMO_DB_PATH", "./mintmemo.db")).expanduser()
    host = env.get("MINTMEMO_HOST", "127.0.0.1")
    port_raw = env.get("MINTMEMO_PORT", "8000")
    try:
        port = int(port_raw)
    except ValueError as e:
        raise ValueError(f"Invalid MINTMEMO_PORT: {port_raw}") from e

    auth_user = env.get("MINTMEMO_AUTH_USER") or None
    auth_pass = env.get("MINTMEMO_AUTH_PASS") or None

    return Settings(db_path=db_path, host=host, port=port, auth_user=auth_user, auth_pass=auth_pass)
