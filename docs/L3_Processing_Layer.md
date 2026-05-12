# 🧠 Layer 3: Processing Layer (Apache Spark)

The Processing Layer is the central "Brain" of the pipeline. It consumes raw Kafka events and transforms them into high-fidelity financial records.

---

## 🏗️ Spark Structured Streaming
The pipeline (`notebooks/spark_realtime_pipeline.py`) processes data in near real-time with micro-batches.

### Critical Responsibilities:
1.  **Schema Enforcement**: Every incoming message is validated against the **23-column financial schema**.
2.  **Risk Scoring**: A real-time logic engine assigns a `risk_score` (0.0 to 1.0) based on amount, category, and merchant history.
3.  **Data Type Mapping**: Ensuring compatibility between JSON/Kafka types and ClickHouse-specific types (e.g., converting booleans to UInt8).

---

## 🚨 Integrated Alerting Triggers
Spark acts as the supervisor for the **Alerting Layer**.
*   It identifies "Whale Transactions" (>= 55k EGP).
*   It detects Admin-related activities.
*   It pushes relevant data to the [L6: Alerting Layer](./L6_Alerting_Layer.md).

---

## ⚙️ Performance & Tuning
*   **Checkpointing**: Enables fault-tolerant restarts without data duplication.
*   **Parallelism**: Configured to scale across multiple Spark executors.

---
**[⬅️ Previous: Layer 2](./L2_Ingestion_Layer.md) | [🏡 Home: Master Doc](./CDC_DWH_DOCUMENTATION.md) | [Next: Layer 4 (Storage) ➡️](./L4_Storage_Layer.md)**
