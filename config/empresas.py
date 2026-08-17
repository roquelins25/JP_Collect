import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv, set_key

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

_EMPRESA_INDEX_RE = re.compile(r"^QBO_(\d+)_ID_EMPRESA$")


@dataclass
class Empresa:
    """Configuração de conexão QBO de uma empresa (um bloco QBO_<indice>_... no .env)."""

    indice: int
    id_empresa: int
    client_id: str
    client_secret: str
    redirect_uri: str
    realm_id: str
    access_token: str
    refresh_token: str
    environment: str
    minor_version: str


def _env_key(indice: int, campo: str) -> str:
    return f"QBO_{indice}_{campo}"


def get_empresas() -> list[Empresa]:
    """Descobre todas as empresas configuradas no .env (blocos QBO_<indice>_ID_EMPRESA)."""
    load_dotenv(_ENV_PATH, override=True)

    indices = sorted(
        int(m.group(1))
        for k in os.environ
        if (m := _EMPRESA_INDEX_RE.match(k))
    )

    if not indices:
        raise ValueError("Nenhuma empresa configurada no .env (esperado QBO_<N>_ID_EMPRESA).")

    return [_carregar_empresa(i) for i in indices]


def get_empresa(id_empresa: int) -> Empresa:
    """Busca uma empresa específica pelo id_empresa."""
    for empresa in get_empresas():
        if empresa.id_empresa == id_empresa:
            return empresa
    raise ValueError(f"Nenhuma empresa configurada no .env com id_empresa={id_empresa}.")


def get_empresa_by_indice(indice: int) -> Empresa:
    """Carrega uma empresa pelo índice do bloco QBO_<indice>_... — usado no fluxo manual
    de autenticação (qbo/auth.py), onde ainda pode não haver tokens/realm_id salvos."""
    load_dotenv(_ENV_PATH, override=True)
    return _carregar_empresa(indice)


def _carregar_empresa(indice: int) -> Empresa:
    def req(campo: str) -> str:
        valor = os.getenv(_env_key(indice, campo))
        if not valor:
            raise ValueError(f"{_env_key(indice, campo)} não definido no .env.")
        return valor

    def opt(campo: str) -> str:
        return os.getenv(_env_key(indice, campo), "")

    return Empresa(
        indice=indice,
        id_empresa=int(req("ID_EMPRESA")),
        client_id=req("CLIENT_ID"),
        client_secret=req("CLIENT_SECRET"),
        redirect_uri=req("REDIRECT_URI"),
        realm_id=opt("REALM_ID"),
        access_token=opt("ACCESS_TOKEN"),
        refresh_token=opt("REFRESH_TOKEN"),
        environment=os.getenv(_env_key(indice, "ENVIRONMENT"), "sandbox"),
        minor_version=os.getenv(_env_key(indice, "MINOR_VERSION"), "75"),
    )


def save_tokens(empresa: Empresa, access_token: str, refresh_token: str, realm_id: str | None = None) -> None:
    """Persiste tokens renovados no bloco da empresa no .env."""
    env_path = os.path.abspath(_ENV_PATH)
    set_key(env_path, _env_key(empresa.indice, "ACCESS_TOKEN"), access_token)
    set_key(env_path, _env_key(empresa.indice, "REFRESH_TOKEN"), refresh_token)
    if realm_id:
        set_key(env_path, _env_key(empresa.indice, "REALM_ID"), realm_id)
    load_dotenv(env_path, override=True)
