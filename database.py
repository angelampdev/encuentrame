import os
import pymysql
import pymysql.cursors


class ConexionCompat:
    """Adapta pymysql para que conn.execute(...) funcione como antes con sqlite3."""

    def __init__(self, conexion):
        self._conexion = conexion

    def execute(self, query, params=()):
        cursor = self._conexion.cursor()
        cursor.execute(query.replace("?", "%s"), params)
        return cursor

    def commit(self):
        self._conexion.commit()

    def close(self):
        self._conexion.close()


def get_connection():
    conexion = pymysql.connect(
        host=os.environ["MYSQLHOST"],
        port=int(os.environ.get("MYSQLPORT", 3306)),
        user=os.environ["MYSQLUSER"],
        password=os.environ["MYSQLPASSWORD"],
        database=os.environ["MYSQLDATABASE"],
        cursorclass=pymysql.cursors.DictCursor,
    )
    return ConexionCompat(conexion)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mascotas (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            tipo          VARCHAR(50) NOT NULL,
            animal        VARCHAR(50) NOT NULL,
            ciudad        VARCHAR(100) NOT NULL,
            descripcion   TEXT NOT NULL,
            contacto      VARCHAR(255) NOT NULL,
            contacto_tipo VARCHAR(20) NOT NULL DEFAULT 'numero',
            foto          VARCHAR(255),
            estado        VARCHAR(20) NOT NULL DEFAULT 'activo',
            desc_cierre   TEXT,
            fecha         DATE NOT NULL
        )
    """)

    columnas = {fila["Field"] for fila in conn.execute("SHOW COLUMNS FROM mascotas").fetchall()}
    if "contacto_tipo" not in columnas:
        conn.execute("ALTER TABLE mascotas ADD COLUMN contacto_tipo VARCHAR(20) NOT NULL DEFAULT 'numero'")

    conn.commit()
    conn.close()
