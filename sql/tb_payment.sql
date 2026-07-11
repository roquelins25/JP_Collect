CREATE TABLE IF NOT EXISTS tb_payment (
    id                          BIGINT PRIMARY KEY,
    txndate                     DATE,
    customerref_value           VARCHAR(100),
    customerref_name            VARCHAR(100),
    totalamt                    NUMERIC(14, 2),
    unappliedamt                NUMERIC(14, 2),
    currencyref_value           VARCHAR(100),
    metadata_lastupdatedtime    TIMESTAMP,
    id_empresa                   BIGINT
);

CREATE INDEX IF NOT EXISTS ix_tb_payment_txndate ON tb_payment (txndate);
