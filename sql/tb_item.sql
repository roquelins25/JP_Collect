CREATE TABLE IF NOT EXISTS tb_item (
    id                          BIGINT NOT NULL,
    name                        VARCHAR(100),
    fullyqualifiedname          VARCHAR(100),
    type                        VARCHAR(100),
    incomeaccountref_value      VARCHAR(100),
    incomeaccountref_name       VARCHAR(100),
    active                      BOOLEAN,
    metadata_lastupdatedtime    TIMESTAMP,
    id_empresa                  BIGINT NOT NULL,
    id_relaciona                VARCHAR(150) NOT NULL,
    PRIMARY KEY (id, id_empresa)
);