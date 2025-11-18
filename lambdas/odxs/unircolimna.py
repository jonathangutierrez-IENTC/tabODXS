import pandas as pd
import pymysql
import time

# ---------------------------------------
# 1. Conexión MySQL
# ---------------------------------------
conn = pymysql.connect(
    host="127.0.0.1",
    user="root",
    password="",
    database="olimpo-db"
)

cur = conn.cursor()

# ---------------------------------------
# 2. Desactivar trigger que causa deadlocks
# ---------------------------------------
print("Desactivando trigger accounts_after_update...")
cur.execute("DROP TRIGGER IF EXISTS accounts_after_update;")
conn.commit()


# ---------------------------------------
# 3. Cargar datos con Pandas
# ---------------------------------------
print("Cargando datos...")

df_odxs = pd.read_sql("SELECT id, accountNumber FROM odxs", conn)
df_accounts = pd.read_sql("SELECT accountNumber, totalAccount FROM accounts", conn)


# ---------------------------------------
# 4. Merge
# ---------------------------------------
print("Realizando merge...")
df_merged = df_odxs.merge(df_accounts, on="accountNumber", how="left")

# Filtramos solo los que sí tienen totalAccount encontrado
df_valid = df_merged[df_merged["totalAccount"].notnull()]

# Lista de updates (totalAccount, id)
updates = list(zip(df_valid["totalAccount"], df_valid["id"]))

print(f"Total registros a actualizar: {len(updates)}")


# ---------------------------------------
# 5. UPDATE en lotes (batch)
# ---------------------------------------
batch_size = 5000
sql = "UPDATE odxs SET totalAccount = %s WHERE id = %s"

conn.autocommit(False)   # evita locks innecesarios

print("Iniciando actualización en lotes...")

for i in range(0, len(updates), batch_size):
    batch = updates[i:i + batch_size]
    cur.executemany(sql, batch)
    conn.commit()
    print(f"Lote {i} → {i + len(batch)} actualizado")
    time.sleep(0.1)   # descanso para evitar carga alta


# ---------------------------------------
# 6. Volver a crear el trigger
# ---------------------------------------
print("Reactivando trigger accounts_after_update...")

trigger_sql = """
DELIMITER $$

CREATE TRIGGER accounts_after_update
AFTER UPDATE ON accounts
FOR EACH ROW
BEGIN
    IF NEW.totalAccount <> OLD.totalAccount THEN
        UPDATE odxs
        SET totalAccount = NEW.totalAccount
        WHERE accountNumber = NEW.accountNumber;
    END IF;
END $$

DELIMITER ;
"""

# Ejecutar trigger (MySQL 8 acepta múltiples statements si se envían separados)
for part in trigger_sql.split("DELIMITER"):
    part = part.strip()
    if part:
        cur.execute(part)

conn.commit()


# ---------------------------------------
# 7. Finalizar
# ---------------------------------------
cur.close()
conn.close()

print("✔ Proceso completado sin locks y con trigger reactivado.")
