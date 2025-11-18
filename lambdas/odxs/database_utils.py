from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class PostgresDB:
    def __init__(self, user: str, password: str, host: str, port: int, database: str):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.engine: Engine = None

    def connect(self):
        """Crea conexión con PostgreSQL usando SQLAlchemy"""
        url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.engine = create_engine(url)
        print("Conectado a PostgreSQL")

    def close(self):
        """Cierra conexión"""
        if self.engine:
            self.engine.dispose()
            print("Conexión cerrada")

    def execute(self, sql: str, params: Optional[Dict] = None, fetch: bool = False) -> Optional[List[Dict]]:
        """
        Ejecuta cualquier SQL.
        - sql: la consulta SQL
        - params: diccionario con parámetros para la consulta
        - fetch: si es True devuelve resultados (para SELECT)
        """
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), params or {})
            if fetch:
                return [dict(row) for row in result.fetchall()]
        return None


class MySQLDB:
    def __init__(self, user: str, password: str, host: str, port: int, database: str):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.engine: Engine | None = None

    def connect(self):
        """Crea conexión con MySQL usando SQLAlchemy (driver PyMySQL)."""
        # Requiere: pip install mysql-connector-python sqlalchemy
        url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?connect_timeout=5"
        self.engine = create_engine(url, future=True, pool_pre_ping=True)
        print(self.engine)
        print("Conectado a MySQL")

    def close(self):
        """Cierra conexión"""
        if self.engine:
            self.engine.dispose()
            print("Conexión cerrada")

    def execute(self, sql: str, params: Optional[Dict] = None, fetch: bool = False) -> Optional[List[Dict]]:
        """
        Ejecuta cualquier SQL.
        - sql: la consulta SQL
        - params: diccionario con parámetros para la consulta
        - fetch: si es True devuelve resultados (para SELECT)
        """
        if not self.engine:
            raise RuntimeError("La conexión no está inicializada. Llama a connect() primero.")
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), params or {})
            if fetch:
                # result.mappings() devuelve dict-like por fila
                return [dict(row) for row in result.mappings().all()]
        return None
    
    def fetch_batched_tableB(self, offset: int, limit: int = 200):
        """
        Obtiene lote de registros de TableB en orden.
        """
        sql = """
            SELECT accountNumber, totalAccount
            FROM accounts
            ORDER BY accountNumber ASC
            LIMIT :limit OFFSET :offset
        """
        return self.execute(sql, {"limit": limit, "offset": offset}, fetch=True)
    
    def update_tableA_from_tableB_in_batches(self, batch_size: int = 200):
        """
        Ejecuta la actualización en lotes de batch_size.
        """
        offset = 0

        while True:
            print(f"🔍 Fetching batch starting at offset {offset}...")

            rows = self.fetch_batched_tableB(offset, batch_size)

            if not rows:
                print("✔ No more rows in TableB.")
                break

            print(f"📝 Updating {len(rows)} rows in TableA...")
            self.update_tableA_batch(rows)

            offset += batch_size

        print("✔ Finished updating TableA from TableB in batches.")

    def update_tableA_batch(self, rows: List[Dict]):
        """
        Actualiza TableA solo para los registros especificados en rows.
        rows: lista de dicts con columnas {accountNumber, totalAccount}
        """
        if not rows:
            return

        # Build CASE WHEN for batch update
        case_statements = []
        account_numbers = []

        for row in rows:
            acc = row["accountNumber"]
            val = row["totalAccount"] if row["totalAccount"] is not None else "NA"

            case_statements.append(
                f"WHEN '{acc}' THEN '{val}'"
            )
            account_numbers.append(f"'{acc}'")

        sql = f"""
            UPDATE odxs
            SET totalAccount = CASE accountNumber
                {' '.join(case_statements)}
            END
            WHERE accountNumber IN ({','.join(account_numbers)});
        """

        with self.engine.begin() as conn:
            conn.execute(text(sql))