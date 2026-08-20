import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _isolated_import import import_project_modules
from _resilience import run_per_empresa

from airflow import DAG
from airflow.operators.python import PythonOperator

_config_empresas, _extract, _load = import_project_modules("config.empresas", "extract", "load")
get_empresas = _config_empresas.get_empresas
ColetorAccounts = _extract.ColetorAccounts
ColetorCustomers = _extract.ColetorCustomers
ColetorItem = _extract.ColetorItem
ColetorVendors = _extract.ColetorVendors
process_table = _load.process_table

_DEFAULT_ARGS = {
    "owner": "jpgroup",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_tb_customer() -> None:
    def _processar(empresa):
        process_table("tb_customer", ColetorCustomers(empresa).process())

    run_per_empresa(get_empresas(), _processar, "tb_customer")


def _run_tb_account() -> None:
    def _processar(empresa):
        process_table("tb_account", ColetorAccounts(empresa).process())

    run_per_empresa(get_empresas(), _processar, "tb_account")


def _run_tb_vendor() -> None:
    def _processar(empresa):
        process_table("tb_vendor", ColetorVendors(empresa).process())

    run_per_empresa(get_empresas(), _processar, "tb_vendor")


def _run_tb_item() -> None:
    def _processar(empresa):
        process_table("tb_item", ColetorItem(empresa).process())

    run_per_empresa(get_empresas(), _processar, "tb_item")


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
