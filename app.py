import io
import os
import uuid
from datetime import date
import boto3
from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_connection, init_db

try:
    from PIL import Image
    PILLOW_DISPONIBLE = True
except ImportError:
    PILLOW_DISPONIBLE = False

app = Flask(__name__)
app.secret_key = "encuentrame-secret-2024"

BUCKET = os.environ.get("BUCKET")
s3 = boto3.client(
    "s3",
    region_name=os.environ.get("REGION"),
    endpoint_url=os.environ.get("ENDPOINT"),
    aws_access_key_id=os.environ.get("ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("SECRET_ACCESS_KEY"),
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
FORMATOS_PILLOW = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "webp": "WEBP"}
MAX_IMAGE_SIZE = (800, 800)
DEPARTAMENTOS = {
    "Quindío": ["Armenia", "Calarcá", "Circasia", "Otras"],
    "Risaralda": ["Pereira", "Dosquebradas", "Otras"],
    "Valle del Cauca": ["Cali", "Otras"],
}
OTRAS_CIUDADES = ["Chocó"]

CIUDADES = [c for ciudades in DEPARTAMENTOS.values() for c in ciudades] + OTRAS_CIUDADES


CONTACTO_TIPOS = {"numero", "instagram", "tiktok", "facebook"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_photo(file):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    if PILLOW_DISPONIBLE:
        img = Image.open(file)
        img.thumbnail(MAX_IMAGE_SIZE)
        buffer = io.BytesIO()
        img.save(buffer, format=FORMATOS_PILLOW[ext], optimize=True, quality=85)
        buffer.seek(0)
        s3.upload_fileobj(buffer, BUCKET, filename)
    else:
        file.stream.seek(0)
        s3.upload_fileobj(file.stream, BUCKET, filename)
    return filename


@app.route("/uploads/<path:filename>")
def uploads(filename):
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": filename}, ExpiresIn=3600
    )
    return redirect(url)


@app.route("/")
def index():
    init_db()
    ciudad = request.args.get("ciudad", "")
    departamento = request.args.get("departamento", "")
    tipo = request.args.get("tipo", "")
    animal = request.args.get("animal", "")

    conn = get_connection()
    query = "SELECT * FROM mascotas WHERE 1=1"
    params = []

    if ciudad:
        query += " AND ciudad = ?"
        params.append(ciudad)
    elif departamento:
        ciudades_dep = DEPARTAMENTOS.get(departamento) or (OTRAS_CIUDADES if departamento == "Otras" else [])
        if ciudades_dep:
            placeholders = ",".join(["?"] * len(ciudades_dep))
            query += f" AND ciudad IN ({placeholders})"
            params.extend(ciudades_dep)
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
                           departamentos=DEPARTAMENTOS, otras_ciudades=OTRAS_CIUDADES,
                           ciudad=ciudad, departamento=departamento, tipo=tipo, animal=animal)


@app.route("/reportar", methods=["GET", "POST"])
def reportar():
    init_db()
    if request.method == "POST":
        tipo = request.form.get("tipo")
        animal = request.form.get("animal")
        ciudad = request.form.get("ciudad")
        descripcion = request.form.get("descripcion", "").strip()
        contacto = request.form.get("contacto", "").strip()
        contacto_tipo = request.form.get("contacto_tipo", "numero")
        if contacto_tipo not in CONTACTO_TIPOS:
            contacto_tipo = "numero"
        foto_file = request.files.get("foto")

        if not all([tipo, animal, ciudad, descripcion]):
            flash("Por favor completa todos los campos.", "error")
            return render_template("reportar.html", ciudades=CIUDADES,
                                   departamentos=DEPARTAMENTOS, otras_ciudades=OTRAS_CIUDADES)

        filename = save_photo(foto_file)

        conn = get_connection()
        conn.execute(
            "INSERT INTO mascotas (tipo, animal, ciudad, descripcion, contacto, contacto_tipo, foto, fecha) VALUES (?,?,?,?,?,?,?,?)",
            (tipo, animal, ciudad, descripcion, contacto, contacto_tipo, filename, date.today())
        )
        conn.commit()
        conn.close()

        flash("¡Reporte publicado exitosamente!", "success")
        return redirect(url_for("index"))

    return render_template("reportar.html", ciudades=CIUDADES,
                           departamentos=DEPARTAMENTOS, otras_ciudades=OTRAS_CIUDADES)


@app.route("/mascota/<int:id>")
def detalle(id):
    init_db()
    conn = get_connection()
    mascota = conn.execute("SELECT * FROM mascotas WHERE id = ?", (id,)).fetchone()
    conn.close()
    if mascota is None:
        return "No encontrado", 404
    return render_template("detalle.html", mascota=mascota)


@app.route("/mascota/<int:id>/encontrado", methods=["POST"])
def marcar_encontrado(id):
    init_db()
    desc_cierre = request.form.get("desc_cierre", "").strip()
    if not desc_cierre:
        flash("Por favor cuéntanos cómo fue el reencuentro antes de marcarlo como encontrado.", "error")
        return redirect(url_for("detalle", id=id))

    conn = get_connection()
    conn.execute(
        "UPDATE mascotas SET estado = 'encontrado', desc_cierre = ? WHERE id = ?",
        (desc_cierre, id)
    )
    conn.commit()
    conn.close()
    flash("¡Qué alegría! Mascota marcada como encontrada.", "success")
    return redirect(url_for("detalle", id=id))


@app.route("/mascota/<int:id>/eliminar", methods=["POST"])
def eliminar(id):
    init_db()
    conn = get_connection()
    mascota = conn.execute("SELECT foto FROM mascotas WHERE id = ?", (id,)).fetchone()
    conn.execute("DELETE FROM mascotas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    if mascota and mascota["foto"]:
        s3.delete_object(Bucket=BUCKET, Key=mascota["foto"])

    flash("Reporte eliminado.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

