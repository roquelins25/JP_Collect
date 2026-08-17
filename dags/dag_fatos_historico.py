import calendar
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator

from config.empresas import get_empresas
from src.extract import ColetorGeneralLedger, ColetorInvoices, ColetorPayments
from src.load import process_table

# Início operacional da empresa no QBO — mesmo valor de FULL_LOAD_START no main.py.
_HISTORICO_INICIO = date(2026, 1, 1)
_RATE_LIMIT_SLEEP = 5

_DEFAULT_ARGS = {
    "owner": "jpgroup",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_invoice_mes(data_inicial: str, data_final: str, **context) -> None:
    if not context["params"]["executar_invoice"]:
        return
    for empresa in get_empresas():
        df = ColetorInvoices(empresa, data_inicial, data_final).process()
        process_table("tb_invoice", df)
    time.sleep(_RATE_LIMIT_SLEEP)


def _run_payment_mes(data_inicial: str, data_final: str, **context) -> None:
    if not context["params"]["executar_payment"]:
        return
    for empresa in get_empresas():
        df = ColetorPayments(empresa, data_inicial, data_final).process()
        process_table("tb_payment", df)
    time.sleep(_RATE_LIMIT_SLEEP)


def _run_general_ledger_mes(data_inicial: str, data_final: str, **context) -> None:
    if not context["params"]["executar_general_ledger"]:
        return
    for empresa in get_empresas():
        df = ColetorGeneralLedger(empresa, data_inicial, data_final).process()
        if not df.empty:
            process_table("tb_general_ledger", df)
    time.sleep(_RATE_LIMIT_SLEEP)


def _gerar_meses(inicio: date, fim: date):
    cursor = inicio.replace(day=1)
    while cursor <= fim:
        ultimo_dia = calendar.monthrange(cursor.year, cursor.month)[1]
        data_final = min(date(cursor.year, cursor.month, ultimo_dia), fim)
        yield cursor.strftime("%Y-%m-%d"), data_final.strftime("%Y-%m-%d"), cursor.strftime("%Y_%m")
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


with DAG(
    dag_id="jpgroup_historico",
    default_args=_DEFAULT_ARGS,
    description="Backfill histórico mês a mês desde 2026-01 — trigger manual",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["jpgroup", "historico"],
    params={
        "executar_invoice":        Param(True, type="boolean", description="Executar carga de tb_invoice"),
        "executar_payment":        Param(True, type="boolean", description="Executar carga de tb_payment"),
        "executar_general_ledger": Param(True, type="boolean", description="Executar carga de tb_general_ledger"),
    },
) as dag:

    tasks = []
    hoje = date.today()

    for data_ini, data_fim, label in _gerar_meses(_HISTORICO_INICIO, hoje):
        t_invoice = PythonOperator(
            task_id=f"invoice_{label}",
            python_callable=_run_invoice_mes,
            op_kwargs={"data_inicial": data_ini, "data_final": data_fim},
        )
        t_payment = PythonOperator(
            task_id=f"payment_{label}",
            python_callable=_run_payment_mes,
            op_kwargs={"data_inicial": data_ini, "data_final": data_fim},
        )
        t_general_ledger = PythonOperator(
            task_id=f"general_ledger_{label}",
            python_callable=_run_general_ledger_mes,
            op_kwargs={"data_inicial": data_ini, "data_final": data_fim},
        )
        t_invoice >> t_payment >> t_general_ledger

        if tasks:
            tasks[-1] >> t_invoice
        tasks.append(t_general_ledger)
