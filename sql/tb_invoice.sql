CREATE TABLE IF NOT EXISTS tb_invoice (
    id                          VARCHAR(100) PRIMARY KEY,
    docnumber                   VARCHAR(100),
    txndate                     DATE,
    duedate                     DATE,
    customerref_value           VARCHAR(100),
    customerref_name            VARCHAR(100),
    totalamt                    NUMERIC(14, 2),
    balance                     NUMERIC(14, 2),
    currencyref_value           VARCHAR(100),
    emailstatus                 VARCHAR(100),
    metadata_lastupdatedtime    TIMESTAMP,
    id_empresa                   BIGINT
);

CREATE INDEX IF NOT EXISTS ix_tb_invoice_txndate ON tb_invoice (txndate);
