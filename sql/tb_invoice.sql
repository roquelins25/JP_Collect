-- Uma linha por fatura. A tabela é recarregada por período (DELETE + COPY).
CREATE TABLE IF NOT EXISTS tb_invoice (
    id                          VARCHAR(100),
    docnumber                   VARCHAR(100),
    txndate                     DATE,
    line_description            TEXT,
    line_qty                    NUMERIC(14, 2),
    line_unitprice              NUMERIC(14, 2),
    line_amount                 NUMERIC(14, 2),
    line_servicedate            DATE,
    line_itemref_value          VARCHAR(100),
    projectref_value            VARCHAR(100),
    customerref_value           VARCHAR(100),
    billaddr_id                 VARCHAR(100),
    duedate                     DATE,
    totalamt                    NUMERIC(14, 2),
    balance                     NUMERIC(14, 2),
    id_empresa                  BIGINT,
    id_relaciona                VARCHAR(150)
);

CREATE INDEX IF NOT EXISTS ix_tb_invoice_txndate ON tb_invoice (txndate);
CREATE INDEX IF NOT EXISTS ix_tb_invoice_id ON tb_invoice (id);
