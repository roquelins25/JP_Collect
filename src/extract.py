# %%
import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.api_conect import QBOAPI
from config.empresas import Empresa
from qbo.extractor import fetch_all, fetch_all_by_period, fetch_general_ledger
from transform import (
    TransformAccount,
    TransformCustomer,
    TransformGeneralLedger,
    TransformInvoice,
    TransformPayment,
    TransformVendor,
    TransformItem
)

logger = logging.getLogger(__name__)

# %%
def _normalize(records: list[dict]) -> pd.DataFrame:
    """Achata os campos aninhados (ex: CustomerRef.value) e normaliza para minúsculo."""
    if not records:
        return pd.DataFrame()
    df = pd.json_normalize(records, sep="_")
    df.columns = df.columns.str.lower()
    return df


def _com_id_empresa(df: pd.DataFrame, empresa: Empresa, id_col: str = "id") -> pd.DataFrame:
    df["id_empresa"] = empresa.id_empresa
    df["id_relaciona"] = df["id_empresa"].astype(str) + "_" + df[id_col].astype(str)
    return df

# %% ### CUSTOMERS
class ColetorCustomers:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        # Sem WHERE, a API só devolve customers ativos — precisa pedir os dois.
        records = fetch_all(api, "Customer", extra_where="Active IN (true, false)")
        logger.info("Customer: %d registros extraídos", len(records))
        df = TransformCustomer().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

#%% ### ACCOUNTS
class ColetorAccounts:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Account")
        logger.info("Account: %d registros extraídos", len(records))
        df = TransformAccount().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

#%%  ### VENDORS
class ColetorVendors:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Vendor", extra_where="Active IN (true, false)")
        logger.info("Vendor: %d registros extraídos", len(records))
        df = TransformVendor().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

# %%   ### ITEMS
class ColetorItem:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Item", extra_where="Active IN (true, false)")
        logger.info("Item: %d registros extraídos", len(records))
        df = TransformItem().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)


#%%   Invoices
class ColetorInvoices:
    def __init__(self, empresa: Empresa, start_date: str, end_date: str):
        self.empresa = empresa
        self.start_date = start_date
        self.end_date = end_date

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all_by_period(api, "Invoice", "TxnDate", self.start_date, self.end_date)
        logger.info("Invoice: %d registros extraídos [%s → %s]", len(records), self.start_date, self.end_date)
        df = TransformInvoice().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)


# %% #### Payments
class ColetorPayments:
    def __init__(self, empresa: Empresa, start_date: str, end_date: str):
        self.empresa = empresa
        self.start_date = start_date
        self.end_date = end_date

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all_by_period(api, "Payment", "TxnDate", self.start_date, self.end_date)
        logger.info("Payment: %d registros extraídos [%s → %s]", len(records), self.start_date, self.end_date)
        df = TransformPayment().transform(_normalize(records))
        return  _com_id_empresa(df, self.empresa)

# %%  General Ledger
class ColetorGeneralLedger:
    """Livro razão detalhado (relatório GeneralLedger), todas as contas.

    Diferente das demais entidades: vem do endpoint /reports (não /query),
    já com o valor por lançamento em vez do documento inteiro — por isso
    cada linha aqui já é um lançamento contábil individual, não precisa de
    _normalize()/json_normalize (o registro já é plano).
    """

    def __init__(self, empresa: Empresa, start_date: str, end_date: str):
        self.empresa = empresa
        self.start_date = start_date
        self.end_date = end_date

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_general_ledger(api, self.start_date, self.end_date)
        logger.info(
            "GeneralLedger: %d lançamentos extraídos [%s → %s]",
            len(records), self.start_date, self.end_date,
        )
        if not records:
            return pd.DataFrame()
        df = TransformGeneralLedger().transform(pd.DataFrame(records))
        return _com_id_empresa(df, self.empresa, id_col="txn_id")

# %%
