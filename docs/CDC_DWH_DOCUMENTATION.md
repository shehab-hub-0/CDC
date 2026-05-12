# 📖 Full Technical Documentation: Real-Time Financial CDC Pipeline 

Welcome to the comprehensive technical guide for the **Bank-Grade Financial Pipeline**. This document provides an in-depth look at the architecture, data flow, and technologies used in this project.

---

## 📐 High-Level Architecture
![System Architecture](../image/sys_arc.png)

The pipeline is designed as a **6-Layer Decoupled Architecture**, ensuring high availability and independent scalability for each component.

### Pipeline Flow:
1.  **Ingestion**: Transactions are generated/updated in **PostgreSQL**.
2.  **Capture**: **Debezium** captures row-level changes and streams them to **Kafka**.
3.  **Processing**: **Spark Streaming** consumes Kafka messages, enforces the schema, and calculates risk scores.
4.  **Alerting**: High-risk transactions trigger **Gmail** and **WhatsApp** alerts in real-time.
5.  **Storage**: Cleaned data is stored in **ClickHouse** (OLAP) for sub-second queries.
6.  **Visualization**: **Apache Superset** (v4) provides interactive dashboards.

---

## 🛠️ Layer-by-Layer Breakdown

### [L1: Source & Generation Layer](./L1_Source_Layer.md)
*   **PostgreSQL**: The transactional source of truth.
*   **Data Generator (v2)**: Generates 23-field financial transactions, including "Whale Transactions" (55k+ EGP).

### [L2: Ingestion Layer](./L2_Ingestion_Layer.md)
*   **Kafka Cluster**: Acts as the high-throughput buffer.
*   **Debezium Connector**: Real-time CDC from Postgres to Kafka.

### [L3: Processing Layer](./L3_Processing_Layer.md)
*   **Spark Structured Streaming**: The real-time brain executing transformations and risk analysis.

### [L4: Storage Layer (OLAP)](./L4_Storage_Layer.md)
*   **ClickHouse**: Columnar storage optimized for financial analytics.
![ClickHouse Schema](../image/datawarehouse.png)

### [L5: Visualization Layer](./L5_Visualization_Layer.md)
*   **Superset v4**: Professional dashboard with 15 interactive charts.
![Dashboard Highlights](../image/dashboard1.png)

### [L6: Security & Alerting](./L6_Alerting_Layer.md)
*   **Multi-channel Alerts**: Real-time fraud detection with instant notifications.
![Alert Evidence](../image/whatsapp.png)

---

## 💎 The 23-Field Master Schema
For a detailed breakdown of all fields, data types, and their business logic, refer to the **[Master Schema Documentation](./MASTER_SCHEMA.md)**.

---

## 🚀 Deployment Guide
To deploy the entire stack from scratch, follow the instructions in the [Quick Start section of the README](../README.md#🚀-quick-start-production-setup).

---
*Last Updated: May 2026*
