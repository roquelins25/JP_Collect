CREATE TABLE IF NOT EXISTS tb_vendor (
    id                             BIGINT NOT NULL,
    displayname                    VARCHAR(100),
    companyname                    VARCHAR(100),
    primaryemailaddr_address       VARCHAR(100),
    primaryphone_freeformnumber    VARCHAR(100),
    active                         BOOLEAN,
    balance                        NUMERIC(14, 2),
    metadata_lastupdatedtime       TIMESTAMP,
    id_empresa                     BIGINT NOT NULL,
    PRIMARY KEY (id, id_empresa)
);
