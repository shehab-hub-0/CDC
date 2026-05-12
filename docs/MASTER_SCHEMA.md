# 💎 Master Data Schema: 23 Financial Fields (v4)

This document defines the strict 23-column financial schema enforced across the entire pipeline (Postgres → Kafka → Spark → ClickHouse).

---

## 📋 Full Field Definitions

| # | Field Name | Type (SQL) | Description | Business Logic / Source |
|:---|:---|:---|:---|:---|
| 1 | `transaction_id` | UUID/String | Unique Identifier | Primary Key (L1) |
| 2 | `account_number` | String | IBAN / Account ID | Source Account |
| 3 | `customer_name` | String | Full Name | Customer Data |
| 4 | `transaction_amount` | Float64 | Transaction Value | Amount in EGP |
| 5 | `currency` | String | Currency Code | Default: EGP |
| 6 | `transaction_type` | String | Operation Type | PAYMENT, TRANSFER, etc. |
| 7 | `transaction_time` | DateTime | Event Timestamp | Occurrence Time |
| 8 | `merchant_name` | String | Recipient Name | Target Merchant |
| 9 | `city` | String | Origin City | Geo-location |
| 10 | `country` | String | Origin Country | Geo-location |
| 11 | `phone_number` | String | Contact Info | Customer Identity |
| 12 | `payment_method` | String | Instrument Type | Credit Card, Wallet, etc. |
| 13 | `ip_address` | String | Source IP | Fraud Detection Meta |
| 14 | `is_vip` | UInt8 | VIP Flag (0/1) | Loyalty Status |
| 15 | `category` | String | Spending Category | Food, Travel, Investment, etc. |
| 16 | `status` | String | Result | SUCCESS, FAILED, PENDING |
| 17 | `fee` | Float64 | Service Charge | Calculated: % of Amount |
| 18 | `balance_before` | Float64 | Starting Balance | Pre-transaction state |
| 19 | `balance_after` | Float64 | Ending Balance | Post-transaction state |
| 20 | `risk_score` | Float64 | Fraud Probability | Calculated by Spark (0.0 - 1.0) |
| 21 | `device_type` | String | Hardware Info | iPhone, Android, PC |
| 22 | `browser_agent` | String | Software Info | Session Meta |
| 23 | `source_db_updated_at`| DateTime | CDC Watermark | Watermark for Deduplication |

---

## 🐳 Special Logic: Whale Transactions
In Version 4, the data generator has a **1% probability** to generate transactions where `transaction_amount >= 55,000`. 
These events automatically trigger:
*   `risk_score` elevation to `> 0.8`.
*   Real-time WhatsApp and Email alerts.
*   Inclusion in the "🚨 High Risk Transactions" table on the Dashboard.

---
---
**[⬅️ Previous: Layer 6](./L6_Alerting_Layer.md) | [🏡 Home: Master Doc](./CDC_DWH_DOCUMENTATION.md)**
