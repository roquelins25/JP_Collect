"""Import isolado para os módulos deste projeto dentro do Airflow Hub.

O hub aponta AIRFLOW__CORE__DAGS_FOLDER para /opt/airflow/projects e trata
todos os projetos montados ali (bachirotto, duasmeninas, lenon_collect,
maracutala, JP_Collect, ...) como uma única pasta de DAGs. Como todos usam
os mesmos nomes de módulo genéricos do template padrão — config, extract,
load, transform, qbo — o parser de DAGs importa arquivos de projetos
diferentes no mesmo processo Python, e o sys.modules é compartilhado: o
primeiro projeto a importar "extract" (por exemplo) faz esse nome apontar
para o seu próprio arquivo pelo resto do processo, quebrando o import dos
demais projetos.

`import_project_modules()` remove temporariamente do sys.modules qualquer
entrada com esses nomes, dá prioridade ao path deste projeto, importa os
módulos pedidos, e depois restaura o sys.modules ao estado anterior — assim
os outros projetos que rodarem no mesmo processo não são afetados.
"""
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = PROJECT_ROOT / "src"
_GENERIC_MODULE_NAMES = ("config", "extract", "load", "transform", "qbo")


def import_project_modules(*names: str):
    """Importa `names` (ex.: "extract", "config.empresas") isolados de
    módulos de mesmo nome vindos de outros projetos no mesmo processo."""
    saved = {
        key: sys.modules.pop(key)
        for key in list(sys.modules)
        if key.split(".")[0] in _GENERIC_MODULE_NAMES
    }
    added_paths = [p for p in (str(PROJECT_ROOT), str(_SRC_ROOT)) if p not in sys.path]
    for p in added_paths:
        sys.path.insert(0, p)

    try:
        modules = tuple(importlib.import_module(name) for name in names)
    finally:
        for key in list(sys.modules):
            if key.split(".")[0] in _GENERIC_MODULE_NAMES:
                del sys.modules[key]
        sys.modules.update(saved)
        for p in added_paths:
            sys.path.remove(p)

    return modules
