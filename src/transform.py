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
        "id", "docnumber", "txndate", "line_description",
        "line_qty", "line_unitprice", "line_amount", "line_servicedate", "line_itemref_value",
        "projectref_value", "customerref_value", "billaddr_id", "duedate", "totalamt", "balance"
    ]

    @staticmethod
    def _aggregate_line(lines: object) -> dict:
        """Resume as linhas 'SalesItemLineDetail' de uma fatura em um único registro
        (descarta SubTotalLineDetail; concatena/soma os itens quando há mais de um)."""
        if not isinstance(lines, list):
            return {}
        items = [l for l in lines if l.get("DetailType") == "SalesItemLineDetail"]
        if not items:
            return {}
        details = [i.get("SalesItemLineDetail", {}) or {} for i in items]
        descriptions = [i.get("Description") for i in items if i.get("Description")]
        service_dates = [d.get("ServiceDate") for d in details if d.get("ServiceDate")]
        item_refs = sorted({d.get("ItemRef", {}).get("value") for d in details if d.get("ItemRef", {}).get("value")})
        unit_prices = [d.get("UnitPrice") for d in details if d.get("UnitPrice") is not None]
        return {
            "description": " | ".join(descriptions),
            "qty": sum(d.get("Qty") or 0 for d in details),
            "unitprice": unit_prices[0] if len(unit_prices) == 1 else None,
            "amount": sum(i.get("Amount") or 0 for i in items),
            "servicedate": min(service_dates) if service_dates else None,
            "itemref_value": "; ".join(item_refs),
        }

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "line" in df.columns:
            line_df = pd.json_normalize(df["line"].apply(self._aggregate_line))
            line_df.columns = [f"line_{c}" for c in line_df.columns]
            df = pd.concat([df.drop(columns=["line"]).reset_index(drop=True), line_df.reset_index(drop=True)], axis=1)

        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["totalamt", "balance", "line_qty", "line_unitprice", "line_amount"])
        df = self._to_date(df, ["txndate", "duedate", "line_servicedate"])
        return df


class TransformPayment(BaseTransform):
    _COLS = [
        "id","customerref_value", "deposittoaccountref_value", "processpayment", "txndate",
        "line_amount", "line_linkedtxn_txnid", "line_linkedtxn_txntype", "projectref_value", "linkedtxn_txnid", "linkedtxn_txntype"
    ]

    @staticmethod
    def _flatten_line(line: object) -> dict:
        """Um Payment.Line traz o valor aplicado e a fatura quitada (LinkedTxn)."""
        if not isinstance(line, dict):
            return {}
        linked = line.get("LinkedTxn") or []
        first = linked[0] if linked else {}
        return {
            "amount": line.get("Amount"),
            "linkedtxn_txnid": first.get("TxnId"),
            "linkedtxn_txntype": first.get("TxnType"),
        }

    @staticmethod
    def _first_linkedtxn(linked: object) -> dict:
        """LinkedTxn no nível raiz do Payment aponta pro Deposit gerado (quando existe)."""
        if not isinstance(linked, list) or not linked:
            return {}
        return linked[0]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "linkedtxn" in df.columns:
            linked_df = pd.json_normalize(df["linkedtxn"].apply(self._first_linkedtxn))
            linked_df.columns = [f"linkedtxn_{c.lower()}" for c in linked_df.columns]
            df = pd.concat([df.drop(columns=["linkedtxn"]).reset_index(drop=True), linked_df.reset_index(drop=True)], axis=1)

        if "line" in df.columns:
            df = df.explode("line", ignore_index=True)
            line_df = pd.json_normalize(df["line"].apply(self._flatten_line))
            line_df.columns = [f"line_{c}" for c in line_df.columns]
            df = pd.concat([df.drop(columns=["line"]).reset_index(drop=True), line_df.reset_index(drop=True)], axis=1)

        df = self._select(df, self._COLS)
        df = self._to_numeric(df, ["line_amount"])
        df = self._to_date(df, ["txndate"])
        df = self._to_bool(df, ["processpayment"])
        return df


class TransformGeneralLedger(BaseTransform):
    _COLS = [
        "tx_date", "txn_type", "txn_type_id", "doc_num", "is_adj", "name",
        "name_id", "cust_name", "cust_name_id", "klass_name", "memo",
        "split_acc", "account", "subt_nat_amount",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._select(df, self._COLS)
        df = df.rename(columns={
            "txn_type_id": "txn_id",
            "subt_nat_amount": "amount",
            "cust_name": "customer",
            "cust_name_id": "customer_id",
        })
        df = self._to_numeric(df, ["amount"])
        # is_adj vem como texto "Yes"/"No" (coluna de relatório, não a API de
        # entidades) — não dá pra usar o _to_bool genérico (espera bool nativo).
        if "is_adj" in df.columns:
            df["is_adj"] = df["is_adj"].map({"Yes": True, "No": False})
        df = self._to_date(df, ["tx_date"])
        return df
