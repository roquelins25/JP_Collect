-- Uma linha por lançamento contábil (relatório GeneralLedger, todas as
-- contas). Recarregada por período (DELETE + COPY), igual tb_invoice/
-- tb_payment/tb_bill — uma mesma transação (txn_id) pode aparecer em
-- múltiplas linhas (splits em várias contas), então não há PK de linha.
CREATE TABLE IF NOT EXISTS tb_general_ledger (
    tx_date                     DATE,
    txn_type                    VARCHAR(100),
    txn_id                      VARCHAR(100),
    doc_num                     VARCHAR(100),
    is_adj                      BOOLEAN,
    name                        VARCHAR(255),
    name_id                     VARCHAR(100),
    customer                    VARCHAR(255),
    customer_id                 VARCHAR(100),
    klass_name                  VARCHAR(100),
    memo                        TEXT,
    split_acc                   VARCHAR(255),
    account                     VARCHAR(255),
    amount                      NUMERIC(14, 2),
    id_empresa                  BIGINT,
    id_relaciona                VARCHAR(150)
);

CREATE INDEX IF NOT EXISTS ix_tb_general_ledger_txdate ON tb_general_ledger (tx_date);
CREATE INDEX IF NOT EXISTS ix_tb_general_ledger_txnid ON tb_general_ledger (txn_id);
CREATE INDEX IF NOT EXISTS ix_tb_general_ledger_account ON tb_general_ledger (account);
CREATE INDEX IF NOT EXISTS ix_tb_general_ledger_customerid ON tb_general_ledger (customer_id);
