CREATE TABLE IF NOT EXISTS tb_account (
    id                          BIGINT NOT NULL,
    name                        VARCHAR(100),
    accounttype                 VARCHAR(100),
    accountsubtype              VARCHAR(100),
    classification              VARCHAR(100),
    active                      BOOLEAN,
    currentbalance              NUMERIC(14,2),
    metadata_lastupdatedtime    TIMESTAMP,
    description                 VARCHAR(100),
    fullyqualifiedname          VARCHAR(255),
    id_empresa                  BIGINT NOT NULL,
    id_relaciona                VARCHAR(150) NOT NULL,
    PRIMARY KEY (id, id_empresa)
);