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