# %%
import logging
import os
import sys
from datetime import date, datetime

# Console do Windows usa cp1252 por padrão; alguns prints do projeto (ex: qbo/auth.py
# na renovação automática de token) usam emoji e quebram com UnicodeEncodeError nesse encoding.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config.empresas import Empresa, get_empresas
from extract import (
    ColetorAccounts,
    ColetorCustomers,
    ColetorGeneralLedger,
    ColetorInvoices,
    ColetorVendors,
    ColetorItem,
    ColetorPayments
)
from load import process_table
from qbo import month_ranges

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# %%
# Início operacional da empresa no QBO — cobre todo o histórico transacional.
FULL_LOAD_START = date(2026, 1, 1)

# %%
def _hoje() -> str:
    return datetime.now().strftime("%Y-%m-%d")

# %%
def run_tb_customer(empresa: Empresa) -> None:
    df = ColetorCustomers(empresa).process()
    process_table("tb_customer", df)

# %%
def run_tb_item(empresa: Empresa) -> None:
    df = ColetorItem(empresa).process()
    process_table("tb_item", df)

# %%
def run_tb_account(empresa: Empresa) -> None:
    df = ColetorAccounts(empresa).process()
    process_table("tb_account", df)
    return df


# %%
def run_tb_vendor(empresa: Empresa) -> None:
    df = ColetorVendors(empresa).process()
    process_table("tb_vendor", df)
# %%
def run_tb_invoice(empresa: Empresa) -> None:
    df = ColetorInvoices(empresa, FULL_LOAD_START.isoformat(), _hoje()).process()
    process_table("tb_invoice", df)

# %%
def run_tb_payment(empresa: Empresa) -> None:
    df = ColetorPayments(empresa, FULL_LOAD_START.isoformat(), _hoje()).process()
    return process_table("tb_payment", df)

# %%
def _n_months_ago(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) - n
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def run_tb_general_ledger(empresa: Empresa, months_back: int = 3) -> None:
    """Carrega tb_general_ledger em janelas mensais independentes.

    Cada mês é extraído e gravado separadamente (process_table faz DELETE +
    INSERT só do range de datas daquele mês) — se um mês falhar, os outros já
    processados continuam válidos, e é barato reprocessar só um mês específico.

    months_back: quantos meses (a partir do mês corrente, inclusive) revisitar
    a cada execução. O QBO permite editar lançamentos de meses "fechados" —
    vimos isso na validação (invoices criadas/alteradas depois do fato, ex:
    1786/1788/1833) — por isso a carga do dia a dia não fica só no mês
    corrente, ela revisita os últimos meses pra capturar esses ajustes.
    Para carga histórica completa (uma vez), use backfill_tb_general_ledger.
    """
    start = _n_months_ago(date.today(), months_back - 1)
    for month_start, month_end in month_ranges(start.isoformat(), _hoje()):
        df = ColetorGeneralLedger(empresa, month_start.isoformat(), month_end.isoformat()).process()
        process_table("tb_general_ledger", df)
        logger.info(
            "tb_general_ledger: %s carregado (%d lançamentos)",
            month_start.strftime("%Y-%m"), len(df),
        )


def backfill_tb_general_ledger(empresa: Empresa) -> None:
    """Carga histórica completa, mês a mês, desde FULL_LOAD_START. Rodar uma
    vez (ou sob demanda) — não faz parte do TASKS do dia a dia."""
    for month_start, month_end in month_ranges(FULL_LOAD_START.isoformat(), _hoje()):
        df = ColetorGeneralLedger(empresa, month_start.isoformat(), month_end.isoformat()).process()
        process_table("tb_general_ledger", df)
        logger.info(
            "tb_general_ledger: %s carregado (%d lançamentos)",
            month_start.strftime("%Y-%m"), len(df),
        )


# %%
TASKS = [
    ("tb_customer", run_tb_customer),
    ("tb_account", run_tb_account),
    ("tb_vendor", run_tb_vendor),
    ("tb_item", run_tb_item),
    ("tb_invoice", run_tb_invoice),
    ("tb_payment", run_tb_payment),
    ("tb_general_ledger", run_tb_general_ledger),
]


# %%
def main() -> None:
    inicio = datetime.now()
    logger.info("Processo iniciado")
    erros = []

    for empresa in get_empresas():
        logger.info("Empresa id_empresa=%s (realm %s)", empresa.id_empresa, empresa.realm_id)
        for nome, func in TASKS:
            try:
                func(empresa)
            except Exception:
                logger.exception("Falha em %s (id_empresa=%s)", nome, empresa.id_empresa)
                erros.append(f"{nome}/{empresa.id_empresa}")

    duracao = (datetime.now() - inicio).total_seconds()
    logger.info("Processo finalizado em %.1fs", duracao)

    if erros:
        logger.error("Tasks com erro: %s", erros)
        sys.exit(1)


if __name__ == "__main__":
    main()
