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
    ColetorVendors,
    ColetorItem
)
from load import process_table

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Início operacional da empresa no QBO — cobre todo o histórico transacional.
FULL_LOAD_START = date(2025, 6, 1)

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


# %%
def run_tb_vendor(empresa: Empresa) -> None:
    df = ColetorVendors(empresa).process()
    process_table("tb_vendor", df)



# %%
TASKS = [
    ("tb_customer", run_tb_customer),
    ("tb_account", run_tb_account),
    ("tb_vendor", run_tb_vendor),
    ("tb_item", run_tb_item),
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
