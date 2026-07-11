import time
import requests


PAGE_SIZE = 1000
MAX_RETRIES = 3
BACKOFF_SECONDS = 60


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
