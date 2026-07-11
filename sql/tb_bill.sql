CREATE TABLE IF NOT EXISTS tb_bill (
    id                          BIGINT PRIMARY KEY,
    txndate                     DATE,
    duedate                     DATE,
    vendorref_value             VARCHAR(100),
    vendorref_name              VARCHAR(100),
    totalamt                    NUMERIC(14, 2),
    balance                     NUMERIC(14, 2),
    currencyref_value           VARCHAR(100),
    metadata_lastupdatedtime    TIMESTAMP,
    id_empresa                   BIGINT
);

CREATE INDEX IF NOT EXISTS ix_tb_bill_txndate ON tb_bill (txndate);
