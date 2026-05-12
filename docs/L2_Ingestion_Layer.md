# 🐝 Layer 2: Ingestion Layer (Debezium & Kafka)

This layer captures every row-level change (INSERT/UPDATE) in the PostgreSQL source database and streams it to a distributed messaging queue.

---

## ⚡ Change Data Capture (CDC)
We use **Debezium** to monitor the Postgres WAL (Write Ahead Log). This ensures that 100% of data changes are captured with zero data loss, even if the downstream services are temporarily unavailable.

### Kafka Topic Strategy
The transactions are published to a specific topic:
*   **Topic**: `postgres.public.transactions`
*   **Format**: JSON (Avro/Protobuf optional for future scaling)

---

## 🏗️ Infrastructure Components
1.  **Kafka Broker**: The high-throughput backbone.
2.  **Zookeeper**: Coordinates the Kafka cluster.
3.  **Kafka Connect**: Hosts the Debezium Postgres connector.

---

## 🔗 Connection Parameters
The connector is configured via the `scripts/setup_pipeline.py` script, which automatically initializes the Kafka topics and Debezium settings.

---
**[⬅️ Previous: Layer 1](./L1_Source_Layer.md) | [🏡 Home: Master Doc](./CDC_DWH_DOCUMENTATION.md) | [Next: Layer 3 (Processing) ➡️](./L3_Processing_Layer.md)**
