from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from mintmemo.config import Settings
from mintmemo.web import create_app


def test_smoke_create_search_export():
    with TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        app = create_app(Settings(db_path=db_path))
        client = TestClient(app)

        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        r = client.post(
            "/notes",
            data={"title": "Hello", "content": "# Hi\nThis is a test note.", "tags": "study, demo"},
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert "Hello" in r.text

        r = client.get("/search?q=Hello")
        assert r.status_code == 200
        assert "Hello" in r.text

        r = client.get("/export.json")
        assert r.status_code == 200
        data = r.json()
        assert "notes" in data
        assert len(data["notes"]) == 1
        assert data["notes"][0]["title"] == "Hello"
