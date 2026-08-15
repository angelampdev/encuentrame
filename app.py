import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_connection, init_db

try:
    from PIL import Image
    PILLOW_DISPONIBLE = True
except ImportError:
    PILLOW_DISPONIBLE = False

app = Flask(__name__)
app.secret_key = "encuentrame-secret-2024"

init_db()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_IMAGE_SIZE = (800, 800)
CIUDADES = ["Armenia", "Pereira", "Dosquebradas", "Cali", "Chocó"]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_photo(file):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    if PILLOW_DISPONIBLE:
        img = Image.open(file)
        img.thumbnail(MAX_IMAGE_SIZE)
        img.save(path, optimize=True, quality=85)
    else:
        file.save(path)
    return filename


@app.route("/")
def index():
    ciudad = request.args.get("ciudad", "")
    tipo = request.args.get("tipo", "")
    animal = request.args.get("animal", "")

    conn = get_connection()
    query = "SELECT * FROM mascotas WHERE 1=1"
    params = []

    if ciudad:
        query += " AND ciudad = ?"
        params.append(ciudad)
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    if animal:
        query += " AND animal = ?"
        params.append(animal)

    query += " ORDER BY estado ASC, fecha DESC"
    mascotas = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("index.html", mascotas=mascotas, ciudades=CIUDADES,
                           ciudad=ciudad, tipo=tipo, animal=animal)


@app.route("/reportar", methods=["GET", "POST"])
def reportar():
    if request.method == "POST":
        tipo = request.form.get("tipo")
        animal = request.form.get("animal")
        ciudad = request.form.get("ciudad")
        descripcion = request.form.get("descripcion", "").strip()
        contacto = request.form.get("contacto", "").strip()
        foto_file = request.files.get("foto")

        if not all([tipo, animal, ciudad, descripcion, contacto]):
            flash("Por favor completa todos los campos.", "error")
            return render_template("reportar.html", ciudades=CIUDADES)

        filename = save_photo(foto_file)

        conn = get_connection()
        conn.execute(
            "INSERT INTO mascotas (tipo, animal, ciudad, descripcion, contacto, foto) VALUES (?,?,?,?,?,?)",
            (tipo, animal, ciudad, descripcion, contacto, filename)
        )
        conn.commit()
        conn.close()

        flash("¡Reporte publicado exitosamente!", "success")
        return redirect(url_for("index"))

    return render_template("reportar.html", ciudades=CIUDADES)


@app.route("/mascota/<int:id>")
def detalle(id):
    conn = get_connection()
    mascota = conn.execute("SELECT * FROM mascotas WHERE id = ?", (id,)).fetchone()
    conn.close()
    if mascota is None:
        return "No encontrado", 404
    return render_template("detalle.html", mascota=mascota)


@app.route("/mascota/<int:id>/encontrado", methods=["POST"])
def marcar_encontrado(id):
    desc_cierre = request.form.get("desc_cierre", "").strip()
    conn = get_connection()
    conn.execute(
        "UPDATE mascotas SET estado = 'encontrado', desc_cierre = ? WHERE id = ?",
        (desc_cierre, id)
    )
    conn.commit()
    conn.close()
    flash("¡Qué alegría! Mascota marcada como encontrada.", "success")
    return redirect(url_for("detalle", id=id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
