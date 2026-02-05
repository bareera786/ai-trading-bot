from contextlib import contextmanager
from typing import Generator
import psycopg2
import os

class DatabasePool:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_pool()
        return cls._instance

    def _init_pool(self):
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,  # Adjust based on expected load
            dsn=os.getenv('DATABASE_URL')
        )

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def execute_safe(self, query: str, params: tuple = None):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall() if cursor.description else None