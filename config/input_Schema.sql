-- ──────────────────────────────────────────────────────────────
-- 1. Databases Creation
-- ──────────────────────────────────────────────────────────────
-- Note: These must be created before connecting to them.
-- financial_db is our data source.
-- superset_metadata is for Superset settings.

-- ──────────────────────────────────────────────────────────────
-- 2. Enums & Types (Run inside financial_db)
-- ──────────────────────────────────────────────────────────────
CREATE TYPE currency_enum AS ENUM ('EGP', 'USD', 'EUR', 'GBP', 'AED');
CREATE TYPE transaction_type_enum AS ENUM ('PAYMENT', 'TRANSFER', 'WITHDRAWAL', 'DEPOSIT');
CREATE TYPE transaction_status_enum AS ENUM ('SUCCESS', 'FAILED', 'PENDING');
CREATE TYPE category_enum AS ENUM ('Groceries', 'Electronics', 'Entertainment', 'Healthcare', 'Travel', 'Utilities', 'Salary', 'Investment');
CREATE TYPE payment_method_enum AS ENUM ('credit_card', 'debit_card', 'online_banking', 'e-wallet');

-- ──────────────────────────────────────────────────────────────
-- 3. Core Transactions Table
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    -- Identity
    transaction_id      UUID                    PRIMARY KEY DEFAULT gen_random_uuid(),
    account_number      VARCHAR(255)            NOT NULL,
    customer_name       VARCHAR(255)            NOT NULL,

    -- Timing
    timestamp           TIMESTAMPTZ             NOT NULL DEFAULT NOW(),

    -- Amount & Currency
    amount              NUMERIC(15, 2)          NOT NULL CHECK (amount > 0),
    currency            currency_enum           NOT NULL DEFAULT 'EGP',
    fee                 NUMERIC(15, 2)          NOT NULL DEFAULT 0.00 CHECK (fee >= 0),

    -- Balance snapshot
    balance_before      NUMERIC(15, 2),
    balance_after       NUMERIC(15, 2),

    -- Classification
    transaction_type    transaction_type_enum   NOT NULL,
    category            category_enum,
    status              transaction_status_enum NOT NULL DEFAULT 'PENDING',

    -- Merchant / Branch
    merchant_name       VARCHAR(255),

    -- Location
    city                VARCHAR(255),
    country             VARCHAR(255),

    -- Technical / Security
    phone_number        VARCHAR(20),
    ip_address          INET,
    device_type         VARCHAR(255),
    browser_agent       TEXT,
    payment_method      payment_method_enum,

    -- Risk Metrics
    is_vip              BOOLEAN                 DEFAULT FALSE,
    risk_score          NUMERIC(4, 2)           CHECK (risk_score >= 0 AND risk_score <= 1.0),

    -- CDC Watermark
    source_db_updated_at TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

-- Index for faster lookups on account
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_number);
