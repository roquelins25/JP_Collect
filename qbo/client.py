"""
QuickBooks Online API Client
- Auto-renova token ao receber 401
- Retorna pandas DataFrame diretamente
"""
import os
import pandas as pd
import requests
from dotenv import load_dotenv

from .auth import get_base_url, refresh_access_token

load_dotenv()


class QBOClient:
    def __init__(self):
        load_dotenv(override=True)
        self.realm_id      = os.getenv("QBO_REALM_ID")
        self.minor_version = os.getenv("QBO_MINOR_VERSION", "75")
        self._access_token = os.getenv("QBO_ACCESS_TOKEN")

        if not self.realm_id:
            raise ValueError("QBO_REALM_ID não definido no .env. Execute authenticate() primeiro.")

    @property
    def base_url(self) -> str:
        return f"{get_base_url()}/v3/company/{self.realm_id}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept":        "application/json",
        }

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """GET com retry automático em caso de token expirado."""
        if params is None:
            params = {}
        params["minorversion"] = self.minor_version

        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code == 401:
            print("⚠️  Token expirado. Renovando...")
            self._access_token = refresh_access_token()
            response = requests.get(url, headers=self._headers(), params=params)

        response.raise_for_status()
        return response.json()

    # ── Query genérica ─────────────────────────────────────────────────────────
    def query(self, sql: str) -> dict:
        """Executa uma query SQL do QBO e retorna o JSON bruto."""
        return self._get("/query", params={"query": sql})

    def query_df(self, sql: str, entity: str) -> pd.DataFrame:
        """Executa query e retorna DataFrame. entity = 'Customer', 'Invoice', etc."""
        data = self.query(sql)
        records = data.get("QueryResponse", {}).get(entity, [])
        return pd.json_normalize(records)

    # ── Entidades prontas ──────────────────────────────────────────────────────
    def get_customers(self, max_results: int = 1000) -> pd.DataFrame:
        sql = f"SELECT * FROM Customer MAXRESULTS {max_results}"
        return self.query_df(sql, "Customer")

    def get_invoices(self, since_date: str = None, max_results: int = 1000) -> pd.DataFrame:
        sql = f"SELECT * FROM Invoice"
        if since_date:
            sql += f" WHERE TxnDate >= '{since_date}'"
        sql += f" ORDERBY TxnDate DESC MAXRESULTS {max_results}"
        return self.query_df(sql, "Invoice")

    def get_payments(self, since_date: str = None, max_results: int = 1000) -> pd.DataFrame:
        sql = f"SELECT * FROM Payment"
        if since_date:
            sql += f" WHERE TxnDate >= '{since_date}'"
        sql += f" MAXRESULTS {max_results}"
        return self.query_df(sql, "Payment")

    def get_accounts(self) -> pd.DataFrame:
        return self.query_df("SELECT * FROM Account MAXRESULTS 1000", "Account")

    def get_vendors(self) -> pd.DataFrame:
        return self.query_df("SELECT * FROM Vendor MAXRESULTS 1000", "Vendor")

    def get_bills(self, since_date: str = None, max_results: int = 1000) -> pd.DataFrame:
        sql = f"SELECT * FROM Bill"
        if since_date:
            sql += f" WHERE TxnDate >= '{since_date}'"
        sql += f" MAXRESULTS {max_results}"
        return self.query_df(sql, "Bill")

    def get_profit_loss(self, start_date: str, end_date: str) -> dict:
        """Relatório P&L (retorna JSON bruto — estrutura do QBO Reports API)."""
        return self._get(
            "/reports/ProfitAndLoss",
            params={"start_date": start_date, "end_date": end_date},
        )

    # ── Change Data Capture (sync incremental) ─────────────────────────────────
    def get_changes(self, entities: list[str], since: str) -> dict:
        """
        Retorna apenas registros alterados desde 'since'.
        since: formato ISO 8601, ex: '2024-01-01T00:00:00Z'
        entities: ['Invoice', 'Customer', 'Payment']
        """
        return self._get(
            "/cdc",
            params={
                "entities":     ",".join(entities),
                "changedSince": since,
            },
        )

    # ── Export para Excel ──────────────────────────────────────────────────────
    def export_to_excel(self, output_path: str, since_date: str = None):
        """Exporta as principais entidades para um arquivo .xlsx."""
        print("📊 Exportando dados para Excel...")
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            datasets = {
                "Customers": self.get_customers(),
                "Invoices":  self.get_invoices(since_date=since_date),
                "Payments":  self.get_payments(since_date=since_date),
                "Accounts":  self.get_accounts(),
                "Vendors":   self.get_vendors(),
                "Bills":     self.get_bills(since_date=since_date),
            }
            for sheet_name, df in datasets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"   ✅ {sheet_name}: {len(df)} registros")

        print(f"\n💾 Salvo em: {output_path}")
