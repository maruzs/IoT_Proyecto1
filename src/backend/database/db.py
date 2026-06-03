import os
import sqlite3
from pathlib import Path

_DB_PATH = os.environ.get("DB_PATH", "/app/data/access_control.db")
_conn: sqlite3.Connection | None = None


def _get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


def init_db() -> None:
    """Create tables if they do not already exist."""
    conn = _get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            autorizado BOOLEAN NOT NULL DEFAULT 1,
            rostro_encoding BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER REFERENCES usuarios(id),
            evento TEXT NOT NULL CHECK(evento IN (
                'Entrada Automática',
                'Apertura Manual',
                'Desconocido Detectado',
                'Sin Rostro'
            ))
        );
        """
    )
    conn.commit()


def get_all_users() -> list[dict]:
    conn = _get_connection()
    cur = conn.execute("SELECT id, nombre, autorizado, rostro_encoding FROM usuarios")
    rows = cur.fetchall()
    return [
        {"id": r[0], "nombre": r[1], "autorizado": bool(r[2]), "rostro_encoding": r[3]}
        for r in rows
    ]


def insert_user(nombre: str, encoding_blob: bytes) -> int:
    conn = _get_connection()
    cur = conn.execute(
        "INSERT INTO usuarios (nombre, rostro_encoding) VALUES (?, ?)",
        (nombre, encoding_blob),
    )
    conn.commit()
    return cur.lastrowid


def insert_event(tipo: str, usuario_id: int | None = None) -> int:
    conn = _get_connection()
    cur = conn.execute(
        "INSERT INTO historial (evento, usuario_id) VALUES (?, ?)",
        (tipo, usuario_id),
    )
    conn.commit()
    return cur.lastrowid


def get_history(limit: int = 50) -> list[dict]:
    conn = _get_connection()
    cur = conn.execute(
        """
        SELECT h.id, h.timestamp, h.evento, u.nombre
        FROM historial h
        LEFT JOIN usuarios u ON h.usuario_id = u.id
        ORDER BY h.timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    return [
        {"id": r[0], "timestamp": r[1], "evento": r[2], "usuario": r[3]}
        for r in rows
    ]


def get_last_event() -> dict | None:
    conn = _get_connection()
    cur = conn.execute(
        """
        SELECT h.id, h.timestamp, h.evento, u.nombre
        FROM historial h
        LEFT JOIN usuarios u ON h.usuario_id = u.id
        ORDER BY h.timestamp DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "timestamp": row[1], "evento": row[2], "usuario": row[3]}
