import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.empresas import get_empresas
from extract import ColetorAccounts, ColetorCustomers, ColetorItem, ColetorVendors
from load import process_table

_DEFAULT_ARGS = {
    "owner": "jpgroup",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_tb_customer() -> None:
    for empresa in get_empresas():
        df = ColetorCustomers(empresa).process()
        process_table("tb_customer", df)


def _run_tb_account() -> None:
    for empresa in get_empresas():
        df = ColetorAccounts(empresa).process()
        process_table("tb_account", df)


def _run_tb_vendor() -> None:
    for empresa in get_empresas():
        df = ColetorVendors(empresa).process()
        process_table("tb_vendor", df)


def _run_tb_item() -> None:
    for empresa in get_empresas():
        df = ColetorItem(empresa).process()
        process_table("tb_item", df)


with DAG(
    dag_id="jpgroup_dimensoes",
    default_args=_DEFAULT_ARGS,
    description="Carga das tabelas dimensão JP Group (customer, account, vendor, item) a cada 4 horas",
    schedule="0 */4 * * *",
    start_date=datetime(2026, 8, 1),
    catchup=False,
    tags=["jpgroup", "dimensoes"],
) as dag:

    op_customer = PythonOperator(task_id="tb_customer", python_callable=_run_tb_customer)
    op_account = PythonOperator(task_id="tb_account", python_callable=_run_tb_account)
    op_vendor = PythonOperator(task_id="tb_vendor", python_callable=_run_tb_vendor)
    op_item = PythonOperator(task_id="tb_item", python_callable=_run_tb_item)

    # paralelo — sem dependência entre dimensões
    [op_customer, op_account, op_vendor, op_item]
