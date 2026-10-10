from decimal import Decimal, InvalidOperation

import psycopg
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from psycopg.rows import dict_row

from config import DB_CONFIG

app = Flask(__name__)

# Clave temporal para los mensajes de confirmación.
# La sustituiremos por una variable de entorno antes de publicar el sistema.
app.secret_key = "cambia-esta-clave-para-desarrollo"


def obtener_conexion():
    """Crear una conexión con PostgreSQL."""
    return psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row,
    )


def obtener_producto(producto_id):
    """Consultar un producto por su identificador."""
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, precio, stock, categoria, activo
                FROM productos
                WHERE id = %s;
                """,
                (producto_id,),
            )

            producto = cursor.fetchone()

    if producto is None:
        abort(404)

    return producto


def validar_producto(formulario):
    """Validar los datos recibidos desde un formulario."""
    nombre = formulario.get("nombre", "").strip()
    categoria = formulario.get("categoria", "").strip()

    if not nombre:
        raise ValueError("El nombre del producto es obligatorio.")

    if len(nombre) > 120:
        raise ValueError("El nombre no puede superar los 120 caracteres.")

    if len(categoria) > 80:
        raise ValueError("La categoría no puede superar los 80 caracteres.")

    try:
        precio = Decimal(formulario.get("precio", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("Introduce un precio válido.")

    if not precio.is_finite() or precio < 0:
        raise ValueError("El precio no puede ser negativo.")

    if precio.as_tuple().exponent < -2:
        raise ValueError("El precio admite como máximo dos decimales.")

    if precio >= Decimal("100000000"):
        raise ValueError("El precio es demasiado alto.")

    try:
        stock_texto = formulario.get("stock", "").strip()

        if not stock_texto:
            raise ValueError

        stock = int(stock_texto)

    except ValueError:
        raise ValueError("Las existencias deben ser un número entero.")

    if stock < 0:
        raise ValueError("Las existencias no pueden ser negativas.")

    if stock > 2147483647:
        raise ValueError("La cantidad de existencias es demasiado alta.")

    return {
        "nombre": nombre,
        "precio": precio,
        "stock": stock,
        "categoria": categoria or None,
    }


@app.route("/")
def inicio():
    """Mostrar el panel principal."""
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM productos
                WHERE activo = TRUE;
                """
            )
            total_productos = cursor.fetchone()["total"]

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM productos
                WHERE activo = TRUE AND stock <= 5;
                """
            )
            productos_stock_bajo = cursor.fetchone()["total"]

    return render_template(
        "index.html",
        total_productos=total_productos,
        productos_stock_bajo=productos_stock_bajo,
        ventas_hoy=Decimal("0.00"),
    )


@app.route("/productos")
def productos():
    """Consultar y buscar productos activos."""
    busqueda = request.args.get("buscar", "").strip()

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre, precio, stock, categoria
                FROM productos
                WHERE activo = TRUE
                  AND (
                      nombre ILIKE %s
                      OR COALESCE(categoria, '') ILIKE %s
                  )
                ORDER BY nombre;
                """,
                (f"%{busqueda}%", f"%{busqueda}%"),
            )

            lista_productos = cursor.fetchall()

    return render_template(
        "productos.html",
        productos=lista_productos,
        busqueda=busqueda,
    )


@app.route("/productos/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    """Mostrar el formulario y registrar un producto."""
    if request.method == "POST":
        try:
            datos = validar_producto(request.form)

            with obtener_conexion() as conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO productos
                            (nombre, precio, stock, categoria)
                        VALUES (%s, %s, %s, %s);
                        """,
                        (
                            datos["nombre"],
                            datos["precio"],
                            datos["stock"],
                            datos["categoria"],
                        ),
                    )

            flash("Producto registrado correctamente.", "success")
            return redirect(url_for("productos"))

        except ValueError as error:
            flash(str(error), "error")

    return render_template(
        "formulario_producto.html",
        titulo="Registrar producto",
        producto=None,
    )


@app.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
def editar_producto(producto_id):
    """Editar los datos de un producto activo."""
    producto = obtener_producto(producto_id)

    if not producto["activo"]:
        abort(404)

    if request.method == "POST":
        try:
            datos = validar_producto(request.form)

            with obtener_conexion() as conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE productos
                        SET nombre = %s,
                            precio = %s,
                            stock = %s,
                            categoria = %s
                        WHERE id = %s
                          AND activo = TRUE;
                        """,
                        (
                            datos["nombre"],
                            datos["precio"],
                            datos["stock"],
                            datos["categoria"],
                            producto_id,
                        ),
                    )

                    if cursor.rowcount != 1:
                        abort(404)

            flash("Producto actualizado correctamente.", "success")
            return redirect(url_for("productos"))

        except ValueError as error:
            flash(str(error), "error")

        # Mantener los datos escritos si existe un error de validación.
        producto = {
            **producto,
            **{
                "nombre": request.form.get("nombre", ""),
                "precio": request.form.get("precio", ""),
                "stock": request.form.get("stock", ""),
                "categoria": request.form.get("categoria", ""),
            },
        }

    return render_template(
        "formulario_producto.html",
        titulo="Editar producto",
        producto=producto,
    )


@app.route("/productos/<int:producto_id>/desactivar", methods=["POST"])
def desactivar_producto(producto_id):
    """Desactivar un producto sin eliminar su registro."""
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                UPDATE productos
                SET activo = FALSE
                WHERE id = %s
                  AND activo = TRUE;
                """,
                (producto_id,),
            )

            if cursor.rowcount != 1:
                abort(404)

    flash("Producto desactivado correctamente.", "success")
    return redirect(url_for("productos"))


if __name__ == "__main__":
    app.run(debug=True)