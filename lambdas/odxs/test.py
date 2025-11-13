import json
import pymysql
from decimal import Decimal 

# ============================================
# CONFIGURACIÓN DE CONEXIÓN
# ============================================
DB_A = {
    "user":"root",
    "password":"",
    "host":"127.0.0.1",
    "port":3306,        
    "database":"olimpo-db"
}

DB_B = {
    "host": "170.239.148.19",
    "user": "ientc-pbi",
    "password": "K3nw00d.1@",
    "database": "olimpo-db",
    "port": 3306
}

TABLA_A = "odxs"
TABLA_B = "odxs"

# Columna con la que se comparará
COLUMNA_CLAVE = "odx"   # cámbiala por tu columna

def convertir_json(obj):
    if isinstance(obj, Decimal):
        return float(obj)  # o str(obj) si quieres mantener formato exacto
    return obj
# ============================================
# FUNCIÓN PARA OBTENER DATOS DE UNA TABLA
# ============================================
def obtener_datos(db_config, tabla):
    connection = pymysql.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        port=db_config["port"]
    )

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(f"SELECT * FROM {tabla}")
        datos = cursor.fetchall()

    connection.close()
    return datos

def obtener_datos_B(db_config, tabla):
    connection = pymysql.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        port=db_config["port"]
    )

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(f'SELECT * FROM {tabla} WHERE createdAt >= "2023-01-01" AND createdAt <= "2024-12-31"')
        datos = cursor.fetchall()

    connection.close()
    return datos

# ============================================
# MAIN
# ============================================
def main():
    print("Leyendo tabla A...")
    datos_A = obtener_datos(DB_A, TABLA_A)

    print("Leyendo tabla B...")
    datos_B = obtener_datos_B(DB_B, TABLA_B)

    # Crear un set con los valores clave de tabla B
    for i in datos_A:
        print(i[COLUMNA_CLAVE])
        break
    for i in datos_B:
        print(i[COLUMNA_CLAVE])
        break
    valores_B = {row[COLUMNA_CLAVE] for row in datos_B}

    # Lista de registros de A que NO están en B
    faltantes = [row[COLUMNA_CLAVE] for row in datos_A if row[COLUMNA_CLAVE] not in valores_B]

    print(f"Registros faltantes encontrados: {len(faltantes)}")


    # Guardar en JSON
    with open("faltantes2odx.json", "w", encoding="utf-8") as f:
        json.dump(faltantes, f, indent=4, ensure_ascii=False, default=convertir_json)

    # print("Archivo faltantes.json generado correctamente.")


# Ejecutar
main()

