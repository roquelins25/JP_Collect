import time
from datetime import datetime, timedelta

import requests


PAGE_SIZE = 1000
MAX_RETRIES = 3
BACKOFF_SECONDS = 60

GENERAL_LEDGER_COLUMNS = (
    "tx_date,txn_type,doc_num,is_adj,name,cust_name,klass_name,memo,split_acc,subt_nat_amount"
)


def _fetch_page(client, entity: str, start: int, extra_where: str = "") -> list:
    where = f"WHERE {extra_where} " if extra_where else ""
    sql = f"SELECT * FROM {entity} {where}STARTPOSITION {start} MAXRESULTS {PAGE_SIZE}"
    data = client.query(sql)
    return data.get("QueryResponse", {}).get(entity, [])


def fetch_all_by_period(client, entity: str, date_field: str, start_date: str, end_date: str) -> list:

    where = f"{date_field} >= '{start_date}' AND {date_field} <= '{end_date}'"
    return fetch_all(client, entity, extra_where=where)


def fetch_all(client, entity: str, extra_where: str = "") -> list:
    all_records = []
    start = 1

    while True:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page = _fetch_page(client, entity, start, extra_where)
                break
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    wait = BACKOFF_SECONDS * attempt
                    print(f"   ⏳ Rate limit atingido. Aguardando {wait}s (tentativa {attempt}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    if attempt == MAX_RETRIES:
                        raise
                else:
                    raise

        all_records.extend(page)

        if len(page) < PAGE_SIZE:
            break

        start += PAGE_SIZE
        time.sleep(0.2)

    return all_records


def month_ranges(start_date: str, end_date: str):
    """Quebra [start_date, end_date] (strings ISO) em blocos mensais."""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    cur = start.replace(day=1)
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = min(nxt - timedelta(days=1), end)
        yield max(cur, start), period_end
        cur = nxt


def _parse_general_ledger(raw: dict) -> list[dict]:
    """Achata o GeneralLedger (Section por conta -> Rows de transação, com
    sub-contas aninhadas recursivamente) numa lista de lançamentos.

    Cada linha de dado carrega o caminho completo da conta (ex:
    "CC BofA 5903:CC BofA - JP"). Colunas cuja célula traz um atributo "id"
    (txn_type -> id da transação, name -> id do customer/vendor) ganham uma
    coluna extra "<chave>_id" com esse identificador. Linhas de "Beginning
    Balance"/totais (sem data real) são descartadas.
    """
    columns = raw.get("Columns", {}).get("Column", [])
    keys = []
    for i, col in enumerate(columns):
        key = col.get("ColTitle", f"col_{i}")
        for meta in col.get("MetaData", []):
            if meta.get("Name") == "ColKey":
                key = meta["Value"]
        keys.append(key)

    records: list[dict] = []

    def walk(node_rows, account_path):
        for row in node_rows:
            if "Rows" in row:
                header_name = row.get("Header", {}).get("ColData", [{}])[0].get("value", "")
                child_path = f"{account_path}:{header_name}" if header_name else account_path
                walk(row["Rows"].get("Row", []), child_path)
                continue

            col_data = row.get("ColData", [])
            if not col_data or col_data[0].get("value") in ("", "Beginning Balance"):
                continue

            record = {}
            for key, cell in zip(keys, col_data):
                record[key] = cell.get("value", "")
                if cell.get("id"):
                    record[f"{key}_id"] = cell["id"]
            record["account"] = account_path
            records.append(record)

    for section in raw.get("Rows", {}).get("Row", []):
        account = section.get("Header", {}).get("ColData", [{}])[0].get("value", "")
        walk(section.get("Rows", {}).get("Row", []), account)

    return records


def _parse_profit_and_loss(raw: dict) -> list[dict]:
    """Achata o ProfitAndLoss (Sections aninhadas: Income, COGS, Expenses, ...) em
    formato longo: uma linha por (conta, coluna de período).

    Cada Section tem Header (nome/id da conta-pai), Rows (filhas, recursivo) e Summary
    (total da seção, ex: "Total Income"). Linhas "Data" são contas folha; linhas do
    Summary entram com row_type="Summary". "group" é o agrupador do QBO (Income,
    COGS, GrossProfit, Expenses, NetOperatingIncome, OtherIncome, OtherExpenses,
    NetOtherIncome, NetIncome). Colunas Money trazem StartDate/EndDate no MetaData
    (úteis com summarize_column_by=Month/Quarter/Year).
    """
    columns = raw.get("Columns", {}).get("Column", [])
    periodos = []  # (índice na ColData, título, start, end) só das colunas de valor
    for i, col in enumerate(columns):
        if col.get("ColType") != "Money":
            continue
        meta = {m.get("Name"): m.get("Value") for m in col.get("MetaData", [])}
        periodos.append((i, col.get("ColTitle", f"col_{i}"), meta.get("StartDate"), meta.get("EndDate")))

    records: list[dict] = []

    def emit(col_data, path, group, row_type):
        if not col_data:
            return
        conta = col_data[0]
        for i, titulo, start, end in periodos:
            if i >= len(col_data):
                continue
            valor = col_data[i].get("value", "")
            records.append({
                "account_id": conta.get("id", ""),
                "account": path,
                "group": group,
                "row_type": row_type,
                "column": titulo,
                "period_start": start,
                "period_end": end,
                "amount": valor,
            })

    def walk(node_rows, path, group):
        for row in node_rows:
            group = row.get("group", group)
            if "Rows" in row or "Summary" in row:
                # Seções como GrossProfit/NetIncome vêm só com Summary, sem Rows.
                header = row.get("Header", {}).get("ColData", [{}])
                nome = header[0].get("value", "")
                child_path = f"{path}:{nome}" if path and nome else (nome or path)
                # Conta-pai com lançamentos próprios traz o saldo dela no Header
                # (ex: "Auto Expenses 81.50"), fora das linhas das sub-contas.
                if any(c.get("value") for c in header[1:]):
                    emit(header, child_path, group, "Header")
                walk(row.get("Rows", {}).get("Row", []), child_path, group)
                if "Summary" in row:
                    summary = row["Summary"].get("ColData", [])
                    sum_path = child_path or (summary[0].get("value", "") if summary else "")
                    emit(summary, sum_path, group, "Summary")
                continue

            col_data = row.get("ColData", [])
            if not col_data:
                continue
            nome = col_data[0].get("value", "")
            emit(col_data, f"{path}:{nome}" if path else nome, group, row.get("type", "Data"))

    walk(raw.get("Rows", {}).get("Row", []), "", "")
    return records


def fetch_profit_and_loss(
    client,
    start_date: str,
    end_date: str,
    accounting_method: str = "Cash",
    summarize_column_by: str = "Month",
) -> list[dict]:
    """Busca o relatório ProfitAndLoss (DRE) do período.

    accounting_method: "Accrual" | "Cash".
    summarize_column_by: Total, Month, Quarter, Year, Week, Days, Customers,
    Vendors, Classes, Departments, Employees, ProductsAndServices.
    """
    raw = client._get(
        "/reports/ProfitAndLoss",
        params={
            "start_date": start_date,
            "end_date": end_date,
            "accounting_method": accounting_method,
            "summarize_column_by": summarize_column_by,
        },
    )
    return _parse_profit_and_loss(raw)


def fetch_general_ledger(client, start_date: str, end_date: str) -> list[dict]:
    """Busca o relatório GeneralLedger (livro razão) em blocos mensais.

    A Reports API do QBO trunca a resposta silenciosamente perto de ~400.000
    células (sem erro/aviso) — em ranges longos isso corta contas inteiras do
    fim da lista. Buscar mês a mês evita o truncamento.
    """
    records: list[dict] = []
    for period_start, period_end in month_ranges(start_date, end_date):
        raw = client._get(
            "/reports/GeneralLedger",
            params={
                "start_date": period_start.isoformat(),
                "end_date": period_end.isoformat(),
                "columns": GENERAL_LEDGER_COLUMNS,
            },
        )
        records.extend(_parse_general_ledger(raw))
    return records
