CREATE TABLE IF NOT EXISTS tb_transactionlist (
    tx_date            DATE,
    txn_type           VARCHAR(100),
    doc_num            VARCHAR(100),
    name               VARCHAR(100),
    memo               VARCHAR(100),
    account_name       VARCHAR(100),
    other_account      VARCHAR(100),
    subt_nat_amount    NUMERIC(14, 2),
    id_empresa          BIGINT
);

CREATE INDEX IF NOT EXISTS ix_tb_transactionlist_txdate ON tb_transactionlist (tx_date);
