

import pymysql

# --- Conexión servidor ORIGEN ---
src = pymysql.connect(
    host="127.0.0.1",
    user="root",
    password="",
    port=3306,
    database="olimpo-db",
    cursorclass=pymysql.cursors.DictCursor
)

# --- Conexión servidor DESTINO ---
dst = pymysql.connect(
    host="170.239.148.19",
    user="ientc-pbi",
    password="K3nw00d.1@",
    port=3306,
    database="ientc-db",
    cursorclass=pymysql.cursors.DictCursor
)

with src.cursor() as c_src, dst.cursor() as c_dst:
    # Leer todos los registros de la tabla
    c_src.execute("SELECT * FROM odxs")
    rows = c_src.fetchall()

    if rows:
        # Generar columnas dinámicamente
        columns = ", ".join(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(rows[0]))
        insert_sql = f"INSERT INTO odxs ({columns}) VALUES ({placeholders})"

        data = [tuple(r.values()) for r in rows]

        # Insertar en destino
        c_dst.executemany(insert_sql, data)
        dst.commit()

print("Copiado exitoso.")
