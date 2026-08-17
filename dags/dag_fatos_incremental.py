import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.empresas import get_empresas
from src.extract import ColetorGeneralLedger, ColetorInvoices, ColetorPayments
from src.load import process_table

_JANELA_DIAS = 90
_MESES_GENERAL_LEDGER = 3  # meses "fechados" revisitados — o QBO permite editar lançamentos passados

_DEFAULT_ARGS = {
    "owner": "jpgroup",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def _run_invoice_incremental() -> None:
    hoje = date.today()
    data_inicial = (hoje - timedelta(days=_JANELA_DIAS)).strftime("%Y-%m-%d")
    data_final = hoje.strftime("%Y-%m-%d")
    for empresa in get_empresas():
        df = ColetorInvoices(empresa, data_inicial, data_final).process()
        process_table("tb_invoice", df)


def _run_payment_incremental() -> None:
    hoje = date.today()
    data_inicial = (hoje - timedelta(days=_JANELA_DIAS)).strftime("%Y-%m-%d")
    data_final = hoje.strftime("%Y-%m-%d")
    for empresa in get_empresas():
        df = ColetorPayments(empresa, data_inicial, data_final).process()
        process_table("tb_payment", df)


def _n_meses_atras(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) - n
    ano, mes = divmod(total, 12)
    return date(ano, mes + 1, 1)


def _run_general_ledger_incremental() -> None:
    hoje = date.today()
    data_inicial = _n_meses_atras(hoje, _MESES_GENERAL_LEDGER - 1).strftime("%Y-%m-%d")
    data_final = hoje.strftime("%Y-%m-%d")
    for empresa in get_empresas():
        df = ColetorGeneralLedger(empresa, data_inicial, data_final).process()
        if not df.empty:
            process_table("tb_general_ledger", df)


with DAG(
    dag_id="jpgroup_incremental",
    default_args=_DEFAULT_ARGS,
    description=(
        "Carga incremental de tb_invoice/tb_payment (últimos 90 dias) e "
        "tb_general_ledger (últimos 3 meses fechados), a cada 2 horas"
    ),
    schedule="0 */2 * * *",
    start_date=datetime(2026, 8, 1),
    catchup=False,
    tags=["jpgroup", "incremental"],
) as dag:

    op_invoice = PythonOperator(
        task_id="invoice_ultimos_90_dias",
        python_callable=_run_invoice_incremental,
    )
    op_payment = PythonOperator(
        task_id="payment_ultimos_90_dias",
        python_callable=_run_payment_incremental,
    )
    op_general_ledger = PythonOperator(
        task_id="general_ledger_ultimos_3_meses",
        python_callable=_run_general_ledger_incremental,
    )

    op_invoice >> op_payment >> op_general_ledger
