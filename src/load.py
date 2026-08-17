import csv
import logging
import os
import sys
from io import StringIO

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.conectDB import connect_db

logger = logging.getLogger(__name__)

_SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")

_TABLE_PK = {
    "tb_customer": ["id", "id_empresa"],
    "tb_account": ["id", "id_empresa"],
    "tb_vendor": ["id", "id_empresa"],
    "tb_item": ["id", "id_empresa"],
}

_TRANSACTIONAL_DATE_COL = {
    "tb_invoice": "txndate",
    "tb_payment": "txndate",
    "tb_general_ledger": "tx_date",
}


def create_table_if_not_exists(conn, table: str) -> None:
    sql_path = os.path.join(_SQL_DIR, f"{table}.sql")
    if not os.path.exists(sql_path):
        logger.warning("SQL não encontrado para %s — tabela não será criada", table)
        return
    with open(sql_path, encoding="utf-8") as f:
        ddl = f.read()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _copy_to_buffer(df: pd.DataFrame) -> StringIO:
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)
    return buffer


def _upsert_dimensao(conn, df: pd.DataFrame, table: str, pk_cols: list[str]) -> None:
    cols = df.columns.tolist()
    cols_str = ", ".join(cols)
    tmp = f"tmp_{table}"

    update_cols = [c for c in cols if c not in pk_cols]
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    pk_cols_str = ", ".join(pk_cols)

    copy_sql = f"COPY {tmp} ({cols_str}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    upsert_sql = f"""
        INSERT INTO {table} ({cols_str})
        SELECT {cols_str} FROM {tmp}
        ON CONFLICT ({pk_cols_str}) DO UPDATE SET {update_set}
    """

    with conn.cursor() as cur:
        cur.execute(f"CREATE TEMP TABLE {tmp} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
        cur.copy_expert(copy_sql, _copy_to_buffer(df))
        cur.execute(upsert_sql)

    conn.commit()
    logger.info("%s: %d registros upserted", table, len(df))


def _load_transacional(conn, df: pd.DataFrame, table: str, date_col: str) -> None:
    cols = df.columns.tolist()
    cols_str = ", ".join(cols)
    copy_sql = f"COPY {table} ({cols_str}) FROM STDIN WITH (FORMAT CSV, NULL '')"

    data_min = pd.to_datetime(df[date_col]).min().date()
    data_max = pd.to_datetime(df[date_col]).max().date()

    delete_sql = f"DELETE FROM {table} WHERE {date_col} BETWEEN %s AND %s"

    with conn.cursor() as cur:
        cur.execute(delete_sql, (data_min, data_max))
        deleted = cur.rowcount
        cur.copy_expert(copy_sql, _copy_to_buffer(df))

    conn.commit()
    logger.info(
        "%s: %d registros deletados, %d inseridos (período %s → %s)",
        table, deleted, len(df), data_min, data_max,
    )


def process_table(table: str, df: pd.DataFrame) -> None:
    if df.empty:
        logger.warning("%s: nenhum registro para carregar", table)
        return

    conn = connect_db()
    try:
        create_table_if_not_exists(conn, table)

        if table in _TRANSACTIONAL_DATE_COL:
            _load_transacional(conn, df, table, _TRANSACTIONAL_DATE_COL[table])
        else:
            pk_cols = _TABLE_PK[table]
            _upsert_dimensao(conn, df, table, pk_cols)

    except Exception:
        conn.rollback()
        logger.exception("Falha ao processar %s", table)
        raise
    finally:
        conn.close()
