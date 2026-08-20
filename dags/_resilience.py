"""Executa uma rotina por empresa sem deixar uma falha isolada (ex.: token
QBO expirado/inválido de uma única empresa) abortar as demais.

Cada empresa é processada em um try/except próprio: se falhar, o erro é
logado e a próxima empresa segue normalmente.

Por padrão (`raise_on_error=True`), se alguma empresa falhou, um erro
resumido é levantado ao final para que a task do Airflow seja marcada como
falha/retry (senão o problema passa despercebido). Com
`raise_on_error=False`, nada é levantado — a lista de falhas é apenas
retornada, para quem chamou decidir o que fazer (ex.: repassar via XCom e
só reportar numa task de resumo no final do DAG, sem bloquear as próximas
tasks encadeadas).
"""
import logging

logger = logging.getLogger(__name__)


def run_per_empresa(empresas, fn, label: str, raise_on_error: bool = True) -> list[tuple[str, object, str]]:
    erros = []
    for empresa in empresas:
        indice = getattr(empresa, "indice", empresa)
        try:
            fn(empresa)
        except Exception as exc:
            logger.error("%s: falha na empresa %s — %s", label, indice, exc)
            erros.append((label, indice, str(exc)))

    if erros and raise_on_error:
        indices = ", ".join(str(indice) for _, indice, _ in erros)
        raise RuntimeError(
            f"{label}: falha em {len(erros)} empresa(s) [{indices}]; demais empresas processadas normalmente"
        )

    return erros
