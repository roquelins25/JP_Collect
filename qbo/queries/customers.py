from client import QBOClient

def get_customers(client, max_results=1000):
    sql = f"SELECT * FROM Customer MAXRESULTS {max_results}"
    return client.query_df(sql, "Customer")


def run():
    print("🔌 Conectando ao QuickBooks...")

    client = QBOClient()

    print("📥 Buscando customers...")
    df = get_customers(client)

    print(f"\n✅ Total de clientes: {len(df)}\n")

    if df.empty:
        print("⚠️ Nenhum cliente encontrado.")
        return

    # Mostra algumas colunas importantes (se existirem)
    cols = [
        "DisplayName",
        "PrimaryEmailAddr.Address",
        "PrimaryPhone.FreeFormNumber",
        "Active"
    ]

    cols_existentes = [c for c in cols if c in df.columns]

    print("📊 Prévia dos dados:\n")
    print(df[cols_existentes].head(20).to_string(index=False))

    print("\n📋 Colunas disponíveis:")
    print(df.columns.tolist())


if __name__ == "__main__":
    run()