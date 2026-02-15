# MintMemo

Local-first Markdown notes with instant full-text search (SQLite FTS5) and a clean FastAPI web UI.

## Features

- Create / edit / delete notes
- Markdown rendering (safe mode, HTML disabled)
- Instant full-text search via SQLite FTS5
- Tags, pinned notes
- JSON API (`/api/notes`, `/api/notes/{id}`)
- One-file database, easy backup
- Optional HTTP Basic Auth via env vars
- Docker / GitHub Actions CI / tests included

## Quickstart (Local)

Requirements: Python 3.10+

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
mintmemo run
```

Open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Configuration

Environment variables:

* `MINTMEMO_DB_PATH` (default: `./mintmemo.db`)
* `MINTMEMO_HOST` (default: `127.0.0.1`)
* `MINTMEMO_PORT` (default: `8000`)
* `MINTMEMO_AUTH_USER` and `MINTMEMO_AUTH_PASS` (optional)

Example:

```bash
export MINTMEMO_DB_PATH=~/mintmemo.db
export MINTMEMO_AUTH_USER=admin
export MINTMEMO_AUTH_PASS=change-me
mintmemo run
```

## Docker

```bash
docker compose up --build
```

Open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## API

* `GET /api/notes`
* `GET /api/notes/{id}`
* `GET /export.json` (download all notes)

## Security Notes

Default is intended for localhost usage. If you expose it to a network:

* Enable Basic Auth (env vars)
* Put behind a reverse proxy
* Use HTTPS

## License

MIT
