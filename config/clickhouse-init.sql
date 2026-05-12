-- ══════════════════════════════════════════════════════════════
--  BANK-GRADE FINANCIAL DATA WAREHOUSE — CLICKHOUSE SCHEMA
--  Engine choices:
--    transactions      → ReplacingMergeTree: deduplicates on CDC
--                         re-deliveries using source_db_updated_at
--    high_value_alerts → MergeTree: append-only audit log
--    alerts_mv         → Materialized View: auto-populates alerts
-- ══════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────
-- Database
-- ──────────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS financial_dw;

-- ──────────────────────────────────────────────────────────────
-- Core Transactions Table
-- ReplacingMergeTree deduplicates rows with the same ORDER BY key,
-- keeping the row with the latest source_db_updated_at value.
-- This handles Debezium re-deliveries and CDC at-least-once semantics.
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS financial_dw.transactions
(
    transaction_id      String,
    account_number      String,
    customer_name       String,
    transaction_amount  Float64,
    currency            String,
    transaction_type    String,
    transaction_time    DateTime64(3, 'UTC'),
    merchant_name       String,
    city                String,
    country             String,
    phone_number        String,
    payment_method      String,
    ip_address          String,
    is_vip              UInt8,          -- 1 = VIP, 0 = standard
    -- Enriched fields added in v2
    category            String,
    status              String,
    fee                 Float64,
    balance_before      Float64,
    balance_after       Float64,
    risk_score          Float64,        -- [0.0, 1.0]
    device_type         String,
    browser_agent       String,
    source_db_updated_at DateTime64(3, 'UTC')   -- CDC watermark
)
ENGINE = ReplacingMergeTree(source_db_updated_at)
-- Composite key: deduplication scope is per-transaction per-account
ORDER BY (transaction_id, account_number);


-- ──────────────────────────────────────────────────────────────
-- High-Value Alerts Table
-- Append-only audit log populated by the materialized view below.
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS financial_dw.high_value_alerts
(
    alert_id            UUID    DEFAULT generateUUIDv4(),
    transaction_id      String,
    customer_name       String,
    transaction_amount  Float64,
    category            String,
    risk_score          Float64,
    alert_time          DateTime DEFAULT now(),
    severity            String  DEFAULT 'HIGH'
)
ENGINE = MergeTree()
ORDER BY alert_time;


-- ──────────────────────────────────────────────────────────────
-- Materialized View: Auto-Alert on High-Risk / High-Value / VIP
-- Runs on every INSERT into financial_dw.transactions and writes
-- qualifying rows to high_value_alerts.
--
-- Severity tiers:
--   CRITICAL  risk_score > 0.7
--   HIGH      transaction_amount > 50 000 (but risk not critical)
--   MEDIUM    everything else that passed the WHERE filter
-- ──────────────────────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS financial_dw.alerts_mv
TO financial_dw.high_value_alerts
AS
SELECT
    transaction_id,
    customer_name,
    transaction_amount,
    category,
    risk_score,
    now()  AS alert_time,
    CASE
        WHEN risk_score          > 0.7   THEN 'CRITICAL'
        WHEN transaction_amount  > 50000 THEN 'HIGH'
        ELSE                                  'MEDIUM'
    END    AS severity
FROM financial_dw.transactions
WHERE
    transaction_amount > 20000
    OR is_vip   = 1
    OR risk_score > 0.5;