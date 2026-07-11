# %%
import logging
import os
import sys
import fastparquet

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.api_conect import QBOAPI
from config.empresas import Empresa
from qbo.extractor import fetch_all, fetch_all_by_period
from transform import (
    TransformAccount,
    TransformBill,
    TransformCustomer,
    TransformInvoice,
    TransformPayment,
    TransformTransactionList,
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


def _com_id_empresa(df: pd.DataFrame, empresa: Empresa) -> pd.DataFrame:
    df["id_empresa"] = empresa.id_empresa
    return df

# %%
class ColetorCustomers:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Customer")
        logger.info("Customer: %d registros extraídos", len(records))
        df = TransformCustomer().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

#%%
class ColetorAccounts:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Account")
        logger.info("Account: %d registros extraídos", len(records))
        df = TransformAccount().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

#%%
class ColetorVendors:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Vendor")
        logger.info("Vendor: %d registros extraídos", len(records))
        df = TransformVendor().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

# %%
class ColetorItem:
    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all(api, "Item")
        logger.info("Item: %d registros extraídos", len(records))
        df = TransformItem().transform(_normalize(records))
        return _com_id_empresa(df, self.empresa)

#%%
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
        return _com_id_empresa(df, self.empresa)


class ColetorBills:
    def __init__(self, empresa: Empresa, start_date: str, end_date: str):
        self.empresa = empresa
        self.start_date = start_date
        self.end_date = end_date

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        records = fetch_all_by_period(api, "Bill", "TxnDate", self.start_date, self.end_date)
        logger.info("Bill: %d registros extraídos [%s → %s]", len(records), self.start_date, self.end_date)
        for r in records:
            r["id_empresa"] = self.empresa.id_empresa
        return records  #TransformBill().transform(_normalize(records))


# %%
class ColetorTransactionList:

    _COLUMNS = ",".join([
        # Conta
        "acct_num_with_extn",
        "account_name",

        # Identificação da transação
        "tx_date",
        "txn_type",
        "txn_num",
        "doc_num",
        "name",
        "memo",
        "other_account",
        "journal_code_name",

        # Valores
        "subt_nat_amount",
        "nat_open_bal",
        "neg_open_bal",
        "debt_amt",
        "credit_amt",
        "tax_amount",
        "net_amount",
        "quantity",
        "rate",

        # Datas
        "due_date",
        "paid_date",
        "create_date",
        "last_mod_date",

        # Auditoria
        "create_by",
        "last_mod_by",

        # Situação
        "is_ar_paid",
        "is_ap_paid",
        "printed",

        # Pagamento
        "pmt_mthd",

        # Item / mensagem
        "item_name",
        "cust_msg",
    ])

    def __init__(self, empresa: Empresa, start_date: str, end_date: str):
        self.empresa = empresa
        self.start_date = start_date
        self.end_date = end_date

    def process(self) -> pd.DataFrame:
        api = QBOAPI(self.empresa)
        rows = api.get_report(
            "JournalReport",
            params={
                "start_date": self.start_date,
                "end_date": self.end_date,
                "columns": self._COLUMNS
            },
        )
        logger.info("JournalReport: %d linhas extraídas [%s → %s]", len(rows), self.start_date, self.end_date)
        for r in rows:
            r["id_empresa"] = self.empresa.id_empresa

        return  rows #TransformTransactionList().transform(pd.DataFrame(rows))
