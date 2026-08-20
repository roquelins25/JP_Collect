"""Executa uma rotina por empresa sem deixar uma falha isolada (ex.: token
QBO expirado/inválido de uma única empresa) abortar as demais.

Cada empresa é processada em um try/except próprio: se falhar, o erro é
logado e a próxima empresa segue normalmente. Ao final, se alguma empresa
falhou, um erro resumido é levantado para que a task do Airflow ainda seja
marcada como falha/retry (senão o problema passa despercebido).
"""
import logging

logger = logging.getLogger(__name__)


def run_per_empresa(empresas, fn, label: str) -> None:
    erros = []
    for empresa in empresas:
        indice = getattr(empresa, "indice", empresa)
        try:
            fn(empresa)
        except Exception as exc:
            logger.error("%s: falha na empresa %s — %s", label, indice, exc)
            erros.append((indice, exc))

    if erros:
        indices = ", ".join(str(indice) for indice, _ in erros)
        raise RuntimeError(
            f"{label}: falha em {len(erros)} empresa(s) [{indices}]; demais empresas processadas normalmente"
        )
