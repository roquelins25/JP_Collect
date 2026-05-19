"""
QuickBooks OAuth2 - Autenticação e renovação de tokens
"""
import base64
import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")

SANDBOX_BASE  = "https://sandbox-quickbooks.api.intuit.com"
PROD_BASE     = "https://quickbooks.api.intuit.com"
TOKEN_URL     = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
AUTH_URL      = "https://appcenter.intuit.com/connect/oauth2"
REVOKE_URL    = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"


def _credentials_header() -> str:
    client_id     = os.getenv("QBO_CLIENT_ID")
    client_secret = os.getenv("QBO_CLIENT_SECRET")
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return f"Basic {encoded}"


def get_base_url() -> str:
    env = os.getenv("QBO_ENVIRONMENT", "sandbox")
    return SANDBOX_BASE if env == "sandbox" else PROD_BASE


# ── Passo 1: Gera a URL de autorização e abre no browser ──────────────────────
def start_auth_flow():
    params = {
        "client_id":     os.getenv("QBO_CLIENT_ID"),
        "redirect_uri":  os.getenv("QBO_REDIRECT_URI"),
        "response_type": "code",
        "scope":         "com.intuit.quickbooks.accounting",
        "state":         "jp-group-qbo",
    }
    url = f"{AUTH_URL}?{urlencode(params)}"
    print(f"\n🔗 Abrindo navegador para autorização...")
    print(f"   Se não abrir, acesse manualmente:\n   {url}\n")
    webbrowser.open(url)


# ── Passo 2: Servidor local que captura o callback ─────────────────────────────
class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    realm_id  = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        _CallbackHandler.auth_code = query.get("code", [None])[0]
        _CallbackHandler.realm_id  = query.get("realmId", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Autorizado! Pode fechar esta aba.</h2>")
        print(f"\n✅ Código recebido. realmId: {_CallbackHandler.realm_id}")

    def log_message(self, *args):
        pass  # silencia logs do servidor


def capture_callback() -> tuple[str, str]:
    """Sobe servidor local na porta 8000 e aguarda o callback da Intuit."""
    port = int(os.getenv("QBO_REDIRECT_URI", "http://localhost:8000").split(":")[-1].split("/")[0])
    server = HTTPServer(("localhost", port), _CallbackHandler)
    print(f"⏳ Aguardando callback na porta {port}...")
    server.handle_request()
    return _CallbackHandler.auth_code, _CallbackHandler.realm_id


# ── Passo 3: Troca o code pelos tokens ────────────────────────────────────────
def exchange_code_for_tokens(auth_code: str, realm_id: str):
    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization":  _credentials_header(),
            "Content-Type":   "application/x-www-form-urlencoded",
            "Accept":         "application/json",
        },
        data={
            "grant_type":   "authorization_code",
            "code":         auth_code,
            "redirect_uri": os.getenv("QBO_REDIRECT_URI"),
        },
    )
    response.raise_for_status()
    tokens = response.json()
    _save_tokens(tokens["access_token"], tokens["refresh_token"], realm_id)
    print("✅ Tokens salvos no .env com sucesso!")
    return tokens


# ── Renovação automática ───────────────────────────────────────────────────────
def refresh_access_token() -> str:
    """Renova o access_token usando o refresh_token. Salva no .env automaticamente."""
    refresh_token = os.getenv("QBO_REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("QBO_REFRESH_TOKEN não encontrado no .env")

    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": _credentials_header(),
            "Content-Type":  "application/x-www-form-urlencoded",
            "Accept":        "application/json",
        },
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    tokens = response.json()
    realm_id = os.getenv("QBO_REALM_ID")
    _save_tokens(tokens["access_token"], tokens["refresh_token"], realm_id)
    print("🔄 Token renovado com sucesso!")
    return tokens["access_token"]


def _save_tokens(access_token: str, refresh_token: str, realm_id: str):
    env_path = os.path.abspath(ENV_FILE)
    set_key(env_path, "QBO_ACCESS_TOKEN", access_token)
    set_key(env_path, "QBO_REFRESH_TOKEN", refresh_token)
    if realm_id:
        set_key(env_path, "QBO_REALM_ID", realm_id)
    # Recarrega as vars em memória
    load_dotenv(override=True)


# ── Fluxo completo de autenticação inicial ─────────────────────────────────────
def authenticate():
    """Executa o fluxo completo OAuth2 do zero."""
    start_auth_flow()
    auth_code, realm_id = capture_callback()
    if not auth_code:
        raise RuntimeError("Código de autorização não recebido.")
    exchange_code_for_tokens(auth_code, realm_id)
