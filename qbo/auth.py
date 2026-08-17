# %%
import base64
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.empresas import Empresa, get_empresa_by_indice, save_tokens

#%%
SANDBOX_BASE  = "https://sandbox-quickbooks.api.intuit.com"
PROD_BASE     = "https://quickbooks.api.intuit.com"
TOKEN_URL     = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
AUTH_URL      = "https://appcenter.intuit.com/connect/oauth2"
REVOKE_URL    = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"

#%%
def _credentials_header(empresa: Empresa) -> str:
    encoded = base64.b64encode(f"{empresa.client_id}:{empresa.client_secret}".encode()).decode()
    return f"Basic {encoded}"


def get_base_url(empresa: Empresa) -> str:
    return SANDBOX_BASE if empresa.environment == "sandbox" else PROD_BASE

#%%
# ── Passo 1: Gera a URL de autorização e abre no browser ──────────────────────
def start_auth_flow(empresa: Empresa):
    params = {
        "client_id":     empresa.client_id,
        "redirect_uri":  empresa.redirect_uri,
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


def capture_callback(empresa: Empresa) -> tuple[str, str]:
    """Sobe servidor local na porta 8000 e aguarda o callback da Intuit."""
    port = int(empresa.redirect_uri.split(":")[-1].split("/")[0])
    server = HTTPServer(("localhost", port), _CallbackHandler)
    print(f"⏳ Aguardando callback na porta {port}...")
    server.handle_request()
    return _CallbackHandler.auth_code, _CallbackHandler.realm_id


# ── Passo 3: Troca o code pelos tokens ────────────────────────────────────────
def exchange_code_for_tokens(empresa: Empresa, auth_code: str, realm_id: str):
    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization":  _credentials_header(empresa),
            "Content-Type":   "application/x-www-form-urlencoded",
            "Accept":         "application/json",
        },
        data={
            "grant_type":   "authorization_code",
            "code":         auth_code,
            "redirect_uri": empresa.redirect_uri,
        },
    )
    response.raise_for_status()
    tokens = response.json()
    save_tokens(empresa, tokens["access_token"], tokens["refresh_token"], realm_id)
    print("✅ Tokens salvos no .env com sucesso!")
    return tokens


# ── Renovação automática ───────────────────────────────────────────────────────
def refresh_access_token(empresa: Empresa) -> str:
    """Renova o access_token usando o refresh_token. Salva no .env automaticamente."""
    if not empresa.refresh_token:
        raise ValueError(f"QBO_{empresa.indice}_REFRESH_TOKEN não encontrado no .env")

    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": _credentials_header(empresa),
            "Content-Type":  "application/x-www-form-urlencoded",
            "Accept":        "application/json",
        },
        data={
            "grant_type":    "refresh_token",
            "refresh_token": empresa.refresh_token,
        },
    )
    response.raise_for_status()
    tokens = response.json()
    save_tokens(empresa, tokens["access_token"], tokens["refresh_token"], empresa.realm_id)
    print("🔄 Token renovado com sucesso!")
    return tokens["access_token"]


# ── Fluxo completo de autenticação inicial ─────────────────────────────────────
def authenticate(empresa: Empresa):
    """Executa o fluxo completo OAuth2 do zero para uma empresa."""
    start_auth_flow(empresa)
    auth_code, realm_id = capture_callback(empresa)
    if not auth_code:
        raise RuntimeError("Código de autorização não recebido.")
    exchange_code_for_tokens(empresa, auth_code, realm_id)


# ── Uso manual: `python -m qbo.auth <indice>` (primeira vez) ou
#    `python -m qbo.auth <indice> refresh` — <indice> é o N do bloco QBO_<N>_... no .env ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python -m qbo.auth <indice_empresa> [refresh]")

    _empresa = get_empresa_by_indice(int(sys.argv[1]))
    if "refresh" in sys.argv[2:]:
        refresh_access_token(_empresa)
    else:
        authenticate(_empresa)
