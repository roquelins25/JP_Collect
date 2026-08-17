import logging
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.empresas import Empresa
from qbo.auth import get_base_url, refresh_access_token

logger = logging.getLogger(__name__)


class QBOAPI:
    """Cliente HTTP para a API do QuickBooks Online de uma empresa específica.

    Reaproveita as regras de autenticação já existentes em qbo/auth.py
    (obtenção de base_url e renovação de access_token via refresh_token).
    """

    def __init__(self, empresa: Empresa):
        self.empresa = empresa
        self.realm_id = empresa.realm_id
        self.minor_version = empresa.minor_version
        self._access_token = empresa.access_token

    @property
    def base_url(self) -> str:
        return f"{get_base_url(self.empresa)}/v3/company/{self.realm_id}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["minorversion"] = self.minor_version

        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code == 401:
            logger.info("Token expirado. Renovando...")
            self._access_token = refresh_access_token(self.empresa)
            response = requests.get(url, headers=self._headers(), params=params)

        response.raise_for_status()
        return response.json()

    # ── Query genérica (entidades: Customer, Invoice, Payment, Bill, Account, Vendor...) ──
    def query(self, sql: str) -> dict:
        return self._get("/query", params={"query": sql})

    # ── Relatórios (endpoint /reports/<nome>) ──────────────────────────────────
    def get_report(self, report_name: str, params: dict) -> list[dict]:
        raw = self._get(f"/reports/{report_name}", params=params)
        return self._parse_report(raw)

    @staticmethod
    def _column_key(col: dict, index: int) -> str:

        for meta in col.get("MetaData", []):
            if meta.get("Name") == "ColKey":
                return meta["Value"]
        return col.get("ColTitle", f"col_{index}")

    @classmethod
    def _parse_report(cls, raw: dict) -> list[dict]:
        columns = raw.get("Columns", {}).get("Column", [])
        keys = [cls._column_key(col, i) for i, col in enumerate(columns)]

        rows = []
        for row in raw.get("Rows", {}).get("Row", []):
            col_data = row.get("ColData", [])
            rows.append({key: cell.get("value", "") for key, cell in zip(keys, col_data)})
        return rows
