import psycopg
from config import DB_CONFIG

try:
    with psycopg.connect(**DB_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre, precio, stock FROM productos ORDER BY id"
            )

            productos = cursor.fetchall()

            print("\nCONEXIÓN EXITOSA")
            print("-" * 55)

            for producto in productos:
                print(
                    f"ID: {producto[0]} | "
                    f"Producto: {producto[1]} | "
                    f"Precio: ${producto[2]} | "
                    f"Stock: {producto[3]}"
                )

except psycopg.Error as error:
    print(f"Error de PostgreSQL: {error}")