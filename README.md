# JP_collect

Pipeline de ETL que extrai dados do QuickBooks Online (QBO) via API e carrega em um banco Postgres, para a JP Group Construction (e outras empresas configuráveis no `.env`).

## O que carrega

| Tabela | Tipo | Origem (QBO) | Estratégia de carga |
|---|---|---|---|
| `tb_customer` | dimensão | `Customer` (entidade) | upsert por `(id, id_empresa)` |
| `tb_account` | dimensão | `Account` (entidade) | upsert por `(id, id_empresa)` |
| `tb_vendor` | dimensão | `Vendor` (entidade) | upsert por `(id, id_empresa)` |
| `tb_item` | dimensão | `Item` (entidade) | upsert por `(id, id_empresa)` |
| `tb_invoice` | transacional | `Invoice` (entidade) | delete + insert por período |
| `tb_payment` | transacional | `Payment` (entidade) | delete + insert por período |
| `tb_general_ledger` | transacional | relatório `GeneralLedger` (Reports API) | delete + insert por mês |

`tb_general_ledger` é o livro razão detalhado (lançamento por lançamento, com a conta contábil e o customer/job de cada linha) — equivalente ao relatório "Transaction Detail by Account" do QBO. As demais entidades vêm do endpoint `/query`; o razão vem do endpoint `/reports`, que tem um formato e limitações bem diferentes (ver [Notas sobre a Reports API](#notas-sobre-a-reports-api-do-qbo)).

## Estrutura

```
JP_collect/
├── config/
│   ├── empresas.py      # lê os blocos QBO_<n>_... do .env, um por empresa
│   ├── api_conect.py    # QBOAPI: cliente HTTP (query genérica + reports)
│   └── conectDB.py      # conexão com o Postgres
├── qbo/
│   ├── auth.py          # fluxo OAuth2 manual (autenticação inicial / refresh)
│   └── extractor.py     # paginação de entidades + busca/parse do GeneralLedger
├── src/
│   ├── extract.py       # um Coletor por entidade/relatório (ColetorCustomers, ColetorInvoices, ...)
│   ├── transform.py     # normalização/tipagem de cada Coletor (BaseTransform + subclasses)
│   └── load.py          # process_table(): cria a tabela (sql/*.sql) e faz upsert ou delete+insert
├── sql/                 # DDL de cada tabela (tb_<nome>.sql)
├── dags/                # DAGs do Airflow (ver Deploy)
└── main.py              # orquestração local: roda todas as tabelas pra todas as empresas
```

Cada Coletor segue o mesmo formato: `Coletor____(empresa[, start_date, end_date]).process() -> pd.DataFrame`, já com `id_empresa`/`id_relaciona` adicionados.

## Setup

Requer Python 3.14 e [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Crie um `.env` na raiz (nunca versionar) com um bloco `QBO_<n>_*` por empresa e as credenciais do Postgres:

```
QBO_1_ID_EMPRESA=...
QBO_1_CLIENT_ID=...
QBO_1_CLIENT_SECRET=...
QBO_1_REDIRECT_URI=...
QBO_1_ACCESS_TOKEN=...
QBO_1_REFRESH_TOKEN=...
QBO_1_REALM_ID=...
QBO_1_ENVIRONMENT=sandbox   # ou production
QBO_1_MINOR_VERSION=75

DB_HOST=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_PORT=...
```

Para adicionar mais empresas, duplique o bloco trocando o índice (`QBO_2_...`, `QBO_3_...`) — `get_empresas()` descobre todas automaticamente.

### Autenticação inicial / renovação manual de token

```bash
python -m qbo.auth <indice_empresa>            # primeira autorização (abre o navegador)
python -m qbo.auth <indice_empresa> refresh     # renova o access_token na mão
```

Na operação normal o token expirado é renovado automaticamente (`QBOAPI._get`), sem precisar rodar isso manualmente.

## Rodando localmente

```bash
python main.py
```

Roda `TASKS` (todas as tabelas) para todas as empresas configuradas, em sequência — carga incremental por padrão (`tb_general_ledger` revisita só os últimos 3 meses). Para carga histórica completa do razão (uma vez, ou sob demanda), use `backfill_tb_general_ledger(empresa)` diretamente.

## Deploy (Airflow)

A pasta `dags/` segue a estrutura esperada pelo Airflow Hub — ver `DEPLOY_AIRFLOW.md` no diretório pai para o passo a passo completo (clonar no servidor, `.env` no servidor, registrar no `docker-compose.yaml` do hub).

Três DAGs:

- **`jpgroup_dimensoes`** — `tb_customer`/`tb_account`/`tb_vendor`/`tb_item`, em paralelo, a cada 4h.
- **`jpgroup_historico`** — backfill mês a mês desde `2026-01-01`, trigger manual (`schedule=None`), com parâmetros pra ligar/desligar cada tabela individualmente.
- **`jpgroup_incremental`** — `tb_invoice`/`tb_payment` (últimos 90 dias) e `tb_general_ledger` (últimos 3 meses fechados), a cada 2h.

Os três reprocessam janelas fechadas de tempo (não só "desde a última execução") porque o QBO permite editar lançamentos retroativamente — um invoice de meses atrás pode ser criado ou alterado hoje.

## Notas sobre a Reports API do QBO

Coisas não óbvias descobertas na prática, que valem a pena lembrar antes de mexer em `qbo/extractor.py`:

- **Truncamento silencioso**: a Reports API corta a resposta perto de ~400.000 células, sem erro nem aviso. Em ranges longos isso derruba contas inteiras do fim da lista. `fetch_general_ledger` busca em blocos mensais por causa disso — nunca peça um range de vários meses numa chamada só sem chunking.
- **Sub-contas aninhadas**: uma conta com sub-conta (ex: `CC BofA 5903` → `CC BofA - JP`) vem como uma `Section` dentro de outra `Section` no JSON — inclusive um "balde" sem `Header` para os lançamentos diretos da conta-mãe quando ela também tem sub-conta. `_parse_general_ledger` percorre isso recursivamente; um parser que só olha um nível perde lançamentos de verdade.
- **`cust_name`**: chave de coluna (não documentada de forma óbvia) que devolve o customer/job de cada linha, já dividindo automaticamente lançamentos com split entre vários jobs. Evita ter que filtrar por `customer=<id>` uma empresa por vez.
- **`SELECT * FROM Customer/Vendor/Item`** (endpoint `/query`) só devolve registros **ativos** por padrão — precisa `WHERE Active IN (true, false)` pra pegar os inativos também. `Account` é a exceção: já vem completo (contas nunca são deletadas de verdade no QBO).
- **Cash Basis com retroatividade**: os valores do razão em cash basis são recalculados com base no estado *atual* dos pagamentos — uma fatura parcialmente paga hoje pode mostrar valor diferente do que mostrava há alguns meses, mesmo pra um lançamento antigo. Isso é esperado, não é bug de extração (validamos isso comparando com exports antigos do QBO).
