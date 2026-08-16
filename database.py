import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pets.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mascotas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo          TEXT NOT NULL,
            animal        TEXT NOT NULL,
            ciudad        TEXT NOT NULL,
            descripcion   TEXT NOT NULL,
            contacto      TEXT NOT NULL,
            contacto_tipo TEXT NOT NULL DEFAULT 'numero',
            foto          TEXT,
            estado        TEXT NOT NULL DEFAULT 'activo',
            desc_cierre   TEXT,
            fecha         TEXT NOT NULL DEFAULT (date('now'))
        )
    """)

    columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(mascotas)")}
    if "contacto_tipo" not in columnas:
        conn.execute("ALTER TABLE mascotas ADD COLUMN contacto_tipo TEXT NOT NULL DEFAULT 'numero'")

    conn.commit()
    conn.close()
