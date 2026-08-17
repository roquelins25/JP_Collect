CREATE TABLE IF NOT EXISTS tb_payment (
    id                          VARCHAR(100),
    customerref_value           VARCHAR(100),
    deposittoaccountref_value   VARCHAR(100),
    processpayment              BOOLEAN,
    txndate                     DATE,
    line_amount                 NUMERIC(14, 2),
    line_linkedtxn_txnid        VARCHAR(100),
    line_linkedtxn_txntype      VARCHAR(100),
    projectref_value            VARCHAR(100),
    linkedtxn_txnid             VARCHAR(100),
    linkedtxn_txntype           VARCHAR(100),
    id_empresa                  BIGINT,
    id_relaciona                VARCHAR(150)
);

CREATE INDEX IF NOT EXISTS ix_tb_payment_txndate ON tb_payment (txndate);
