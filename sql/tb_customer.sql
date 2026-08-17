CREATE TABLE IF NOT EXISTS tb_customer (
    id                                BIGINT NOT NULL,
    displayname                       VARCHAR(100),
    companyname                       VARCHAR(100),
    primaryemailaddr_address          VARCHAR(100),
    primaryphone_freeformnumber       VARCHAR(100),
    billaddr_line1                    VARCHAR(100),
    billaddr_city                     VARCHAR(100),
    billaddr_countrysubdivisioncode   VARCHAR(100),
    billaddr_postalcode               VARCHAR(100),
    active                            BOOLEAN,
    balance                           NUMERIC(14, 2),
    metadata_lastupdatedtime          TIMESTAMP,
    id_empresa                        BIGINT NOT NULL,
    id_relaciona                      VARCHAR(150) NOT NULL,
    PRIMARY KEY (id, id_empresa)
);
