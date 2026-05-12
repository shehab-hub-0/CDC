# 🗄️ Layer 4: Storage & OLAP Layer (ClickHouse)

ClickHouse serves as the high-performance analytical engine (OLAP) of the pipeline, capable of handling millions of transactions with sub-second response times.

---

## 🏛️ Data Warehouse Schema
The `transactions` table is designed to support deep financial forensics and real-time dashboarding.

![ClickHouse Warehouse Schema](../image/datawarehouse.png)

### Key Architectural Decisions:
*   **Engine**: `ReplacingMergeTree` is used to handle updates from the CDC stream, ensuring that only the latest version of a transaction is stored based on the `source_db_updated_at` watermark.
*   **Partitioning**: Data is partitioned by `toYYYYMM(transaction_time)` for efficient time-series queries.
*   **Columnar Storage**: Optimized for the complex queries required by the Superset v4 dashboard.

---

## 💎 The 23 Enriched Fields
Unlike the raw source database, the storage layer contains **23 enriched fields** including calculated columns like:
*   **Risk Score**: Calculated in real-time by Spark.
*   **Balance Delta**: The difference between balance before and after.
*   **Metadata**: IP Address, Device Type, and Browser Agent for fraud analysis.

---

## ⚡ Query Performance
*   **Average Query Time**: < 100ms.
*   **Ingestion Speed**: Optimized via Spark's JDBC/HTTP connector.

---
**[⬅️ Previous: Layer 3](./L3_Processing_Layer.md) | [🏡 Home: Master Doc](./CDC_DWH_DOCUMENTATION.md) | [Next: Layer 5 (Visualization) ➡️](./L5_Visualization_Layer.md)**
