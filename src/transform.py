import pandas as pd


class BaseTransform:
    """Casts comuns reaproveitados pelas transformações de cada entidade."""

    @staticmethod
    def _select(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        cols_existentes = [c for c in cols if c in df.columns]
        return df[cols_existentes].copy()

    @staticmethod
    def _to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def _to_date(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        return df

    @staticmethod
    def _to_timestamp(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns:
                # QBO retorna timestamps ISO8601 com offsets distintos por registro
                # (ex: -07:00 e -08:00 no horário de verão) — normaliza tudo para UTC.
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        return df

    @staticmethod
    def _to_bool(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns:
                df[col] = df[col].astype("boolean")
        return df


class TransformCustomer(BaseTransform):
    _COLS = [
        "id", "displayname", "companyname", "primaryemailaddr_address",
        "primaryphone_freeformnumber", "billaddr_line1", "billaddr_city",
        "billaddr_countrysubdivisioncode", "billaddr_postalcode",
        "active", "balance", "metadata_lastupdatedtime",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["balance"])
        df = self._to_bool(df, ["active"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df

class TransformItem(BaseTransform):
    _COLS = [
        "id", "name", "fullyqualifiedname", "type", "incomeaccountref_value", "incomeaccountref_name",
        "active", "metadata_lastupdatedtime",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["balance"])
        df = self._to_bool(df, ["active"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df
    
class TransformAccount(BaseTransform):
    _COLS = [
        "id", "name", "accounttype", "accountsubtype", "classification",
        "active", "currentbalance", "metadata_lastupdatedtime",
        "description","fullyqualifiedname"
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["currentbalance"])
        df = self._to_bool(df, ["active"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df


class TransformVendor(BaseTransform):
    _COLS = [
        "id", "displayname", "companyname", "primaryemailaddr_address",
        "primaryphone_freeformnumber", "active", "balance", "metadata_lastupdatedtime",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["balance"])
        df = self._to_bool(df, ["active"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df


class TransformInvoice(BaseTransform):
    _COLS = [
        "id", "docnumber", "txndate", "duedate", "customerref_value",
        "customerref_name", "totalamt", "balance", "currencyref_value",
        "emailstatus", "metadata_lastupdatedtime",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["totalamt", "balance"])
        df = self._to_date(df, ["txndate", "duedate"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df


class TransformPayment(BaseTransform):
    _COLS = [
        "id", "txndate", "customerref_value", "customerref_name",
        "totalamt", "unappliedamt", "currencyref_value", "metadata_lastupdatedtime",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["totalamt", "unappliedamt"])
        df = self._to_date(df, ["txndate"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df


class TransformBill(BaseTransform):
    _COLS = [
        "id", "txndate", "duedate", "vendorref_value", "vendorref_name",
        "totalamt", "balance", "currencyref_value", "metadata_lastupdatedtime",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["totalamt", "balance"])
        df = self._to_date(df, ["txndate", "duedate"])
        df = self._to_timestamp(df, ["metadata_lastupdatedtime"])
        return df


class TransformTransactionList(BaseTransform):
    _COLS = [
        "tx_date", "txn_type", "doc_num", "name", "memo",
        "account_name", "other_account", "subt_nat_amount",
        "create_date", "create_by", "last_mod_date", "last_mod_by",
        "pmt_mthd", "due_date", "cust_msg",
        "is_ar_paid", "is_ap_paid", "printed",
        "debt_amt", "credit_amt",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = df.replace("", pd.NA)
        df = self._to_numeric(df, ["subt_nat_amount", "debt_amt", "credit_amt"])
        df = self._to_date(df, ["tx_date", "due_date"])
        df = self._to_timestamp(df, ["create_date", "last_mod_date"])
        df = self._to_bool(df, ["is_ar_paid", "is_ap_paid", "printed"])
        return df
