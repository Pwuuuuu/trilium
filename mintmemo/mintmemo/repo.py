from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    items = [t.strip().lower() for t in raw.replace("，", ",").split(",")]
    dedup: list[str] = []
    seen = set()
    for t in items:
        if not t:
            continue
        if len(t) > 32:
            t = t[:32]
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return dedup


def _ensure_tag(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    assert row is not None
    return int(row["id"])


def _set_note_tags(conn: sqlite3.Connection, note_id: int, tags: list[str]) -> None:
    conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
    for name in tags:
        tag_id = _ensure_tag(conn, name)
        conn.execute("INSERT OR IGNORE INTO note_tags(note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))


def _get_tags_for_note(conn: sqlite3.Connection, note_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT t.name
        FROM tags t
        JOIN note_tags nt ON nt.tag_id = t.id
        WHERE nt.note_id = ?
        ORDER BY t.name
        """,
        (note_id,),
    ).fetchall()
    return [str(r["name"]) for r in rows]


def create_note(conn: sqlite3.Connection, title: str, content: str, tags: list[str]) -> int:
    now = _now_iso()
    cur = conn.execute(
        "INSERT INTO notes(title, content, pinned, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
        (title.strip() or "Untitled", content or "", now, now),
    )
    note_id = int(cur.lastrowid)
    _set_note_tags(conn, note_id, tags)
    return note_id


def update_note(conn: sqlite3.Connection, note_id: int, title: str, content: str, tags: list[str]) -> None:
    now = _now_iso()
    conn.execute(
        "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
        (title.strip() or "Untitled", content or "", now, note_id),
    )
    _set_note_tags(conn, note_id, tags)


def delete_note(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def toggle_pin(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("UPDATE notes SET pinned = CASE pinned WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (note_id,))
    conn.execute("UPDATE notes SET updated_at = ? WHERE id = ?", (_now_iso(), note_id))


def get_note(conn: sqlite3.Connection, note_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, title, content, pinned, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "title": str(row["title"]),
        "content": str(row["content"]),
        "pinned": bool(row["pinned"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "tags": _get_tags_for_note(conn, int(row["id"])),
    }


def list_notes(conn: sqlite3.Connection, tag: str | None = None, limit: int = 200) -> list[dict]:
    if tag:
        rows = conn.execute(
            """
            SELECT n.id, n.title, n.content, n.pinned, n.created_at, n.updated_at
            FROM notes n
            JOIN note_tags nt ON nt.note_id = n.id
            JOIN tags t ON t.id = nt.tag_id
            WHERE t.name = ?
            ORDER BY n.pinned DESC, n.updated_at DESC
            LIMIT ?
            """,
            (tag.lower(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, title, content, pinned, created_at, updated_at
            FROM notes
            ORDER BY pinned DESC, updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    out: list[dict] = []
    for r in rows:
        content = str(r["content"] or "")
        excerpt = content.strip().replace("\n", " ")
        if len(excerpt) > 160:
            excerpt = excerpt[:160] + "…"
        nid = int(r["id"])
        out.append(
            {
                "id": nid,
                "title": str(r["title"]),
                "excerpt": excerpt,
                "pinned": bool(r["pinned"]),
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
                "tags": _get_tags_for_note(conn, nid),
            }
        )
    return out


def search_notes(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []

    # Basic query sanitation: convert spaces to AND terms
    tokens = [t for t in q.replace("　", " ").split(" ") if t]
    match = " AND ".join(tokens)

    rows = conn.execute(
        """
        SELECT n.id, n.title, n.content, n.pinned, n.created_at, n.updated_at,
               bm25(notes_fts, 1.0, 0.6) AS rank
        FROM notes_fts
        JOIN notes n ON n.id = notes_fts.rowid
        WHERE notes_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (match, limit),
    ).fetchall()

    out: list[dict] = []
    for r in rows:
        content = str(r["content"] or "")
        excerpt = content.strip().replace("\n", " ")
        if len(excerpt) > 180:
            excerpt = excerpt[:180] + "…"
        nid = int(r["id"])
        out.append(
            {
                "id": nid,
                "title": str(r["title"]),
                "excerpt": excerpt,
                "pinned": bool(r["pinned"]),
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
                "tags": _get_tags_for_note(conn, nid),
            }
        )
    return out


def list_tags(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT t.name AS name, COUNT(nt.note_id) AS cnt
        FROM tags t
        LEFT JOIN note_tags nt ON nt.tag_id = t.id
        GROUP BY t.id
        ORDER BY cnt DESC, name ASC
        """
    ).fetchall()
    return [{"name": str(r["name"]), "count": int(r["cnt"])} for r in rows]


def export_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, title, content, pinned, created_at, updated_at FROM notes ORDER BY updated_at DESC"
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        nid = int(r["id"])
        out.append(
            {
                "id": nid,
                "title": str(r["title"]),
                "content": str(r["content"]),
                "pinned": bool(r["pinned"]),
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
                "tags": _get_tags_for_note(conn, nid),
            }
        )
    return out
