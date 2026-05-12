# 🧱 Layer 1: Source & Generation Layer (PostgreSQL)

The first layer of the pipeline is responsible for the persistent storage of transactional data and the generation of synthetic, high-fidelity financial events.

---

## 🐘 PostgreSQL: The Source of Truth
We use **PostgreSQL** as the primary OLTP (Online Transactional Processing) database. Every transaction is first recorded here before being streamed downstream.

### Transactional Schema (Source)
The source table `public.transactions` follows a strict bank-grade schema of **23 fields**. 
> [!NOTE]
> For the full field definitions, see the [Master Schema](./MASTER_SCHEMA.md).

---

## 🐳 Whale Transactions & Synthetic Data
The **Generator** (`generator/main.py`) simulates real-world banking activity.
*   **Whale Logic**: A 1% probability trigger for transactions >= 55,000 EGP.
*   **VIP Tracking**: Special handling for transactions involving the `shehab_admin` account.

---

## 🛠️ Configuration
The source connection details are managed via environment variables to ensure portability.
```bash
POSTGRES_USER=postgres
POSTGRES_DB=financial_db
```

---
**[🏡 Home: Master Doc](./CDC_DWH_DOCUMENTATION.md) | [Next: Layer 2 (Ingestion) ➡️](./L2_Ingestion_Layer.md)**
