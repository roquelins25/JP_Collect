-- Uma linha por (conta, mês) do relatório ProfitAndLoss. Recarregada por período
-- (DELETE + COPY, escopado por id_empresa e accounting_method).
-- row_type: Data = conta folha; Header = saldo próprio de uma conta-pai (ex: "Auto
-- Expenses" com lançamentos diretos). Os totais do QBO (Summary: "Total for ...",
-- Gross Profit, Net Income) não são carregados — recalcular com SUM por account_lvN.
-- Receita/lucro: Income e Other Income somam +, COGS e Expenses somam - (ver account_group).
CREATE TABLE IF NOT EXISTS tb_profit_and_loss (
    id_empresa                  BIGINT NOT NULL,
    accounting_method           VARCHAR(10) NOT NULL,
    account_id                  VARCHAR(100),
    account                     VARCHAR(500),
    account_lv1                 VARCHAR(255),
    account_lv2                 VARCHAR(255),
    account_lv3                 VARCHAR(255),
    account_lv4                 VARCHAR(255),
    account_lv5                 VARCHAR(255),
    account_group              VARCHAR(50),
    row_type                    VARCHAR(20),
    period_label                VARCHAR(50),
    period_start                DATE,
    period_end                  DATE,
    amount                      NUMERIC(14, 2)
);

CREATE INDEX IF NOT EXISTS ix_tb_profit_and_loss_periodstart ON tb_profit_and_loss (id_empresa, period_start);
CREATE INDEX IF NOT EXISTS ix_tb_profit_and_loss_accountid ON tb_profit_and_loss (account_id);
