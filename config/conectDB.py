import os

import psycopg2
from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


def connect_db():
    load_dotenv(_ENV_PATH, override=True)
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
        )
        return connection
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao banco de dados: {e}") from e


if __name__ == "__main__":
    conn = connect_db()
    if conn:
        print("Conexão com o banco de dados estabelecida com sucesso!")
        conn.close()
        print("Conexão fechada.")
