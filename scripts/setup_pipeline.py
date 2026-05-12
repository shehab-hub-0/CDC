import os
import time

import psycopg2
import requests
from clickhouse_driver import Client
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Configuration from .env
POSTGRES_DB = os.getenv("POSTGRES_DB", "financial_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

CH_HOST = "localhost"  # Running from host
CH_PORT = os.getenv("CLICKHOUSE_NATIVE_PORT", "9000")  # Native port
CH_USER = os.getenv("CLICKHOUSE_USER", "admin")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "admin")
CH_DB = os.getenv("CLICKHOUSE_DB", "financial_dw")

DEBEZIUM_URL = "http://localhost:8083/connectors"


def setup_postgres():
    print("Setting up PostgreSQL...")
    try:
        # 1. Connect to default postgres DB to create our app DBs
        conn = psycopg2.connect(
            dbname="postgres",
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Create Financial DB if not exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{POSTGRES_DB}'")
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {POSTGRES_DB}")
            print(f"[OK] Created Database: {POSTGRES_DB}")

        # Create Superset Metadata DB if not exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname='superset_metadata'")
        if not cur.fetchone():
            cur.execute("CREATE DATABASE superset_metadata")
            print("[OK] Created Database: superset_metadata")

        cur.close()
        conn.close()

        # 2. Connect to our app DB to create table
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id VARCHAR(255) PRIMARY KEY,
                account_number VARCHAR(255),
                customer_name VARCHAR(255),
                timestamp TIMESTAMPTZ,
                amount DECIMAL(15,2),
                currency VARCHAR(10),
                city VARCHAR(255),
                country VARCHAR(255),
                merchant_name VARCHAR(255),
                payment_method VARCHAR(50),
                ip_address VARCHAR(50),
                transaction_type VARCHAR(50),
                phone_number VARCHAR(20),
                is_vip BOOLEAN DEFAULT FALSE,
                category VARCHAR(100),
                status VARCHAR(50),
                fee DECIMAL(15,2),
                balance_before DECIMAL(15,2),
                balance_after DECIMAL(15,2),
                risk_score DECIMAL(3,2),
                device_type VARCHAR(100),
                browser_agent VARCHAR(255),
                source_db_updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("[OK] Created Table: transactions")

        # Clear old replication slots to prevent Debezium conflicts
        cur.execute(
            "SELECT pg_drop_replication_slot('debezium') WHERE EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name='debezium')"
        )
        print("[OK] Cleaned old replication slots")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Postgres Error: {e}")


def setup_debezium():
    print("Setting up Debezium Connector...")
    connector_name = "financial-connector-v4"  # New version for setup
    config = {
        "name": connector_name,
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": "postgres",
            "database.port": "5432",
            "database.user": POSTGRES_USER,
            "database.password": POSTGRES_PASSWORD,
            "database.dbname": POSTGRES_DB,
            "topic.prefix": "postgres",
            "table.include.list": "public.transactions",
            "plugin.name": "pgoutput",
            "snapshot.mode": "always",
            "decimal.handling.mode": "double",
        },
    }

    try:
        # Delete old ones first
        requests.delete(f"{DEBEZIUM_URL}/{connector_name}")
        time.sleep(1)

        # Register new
        response = requests.post(DEBEZIUM_URL, json=config)
        if response.status_code in [200, 201]:
            print("[OK] Debezium Connector Registered Successfully")
        else:
            print(f"⚠️ Debezium Status: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Debezium Error: {e}")


def setup_clickhouse():
    print("Setting up ClickHouse DWH...")
    try:
        # Use Native port 9000 for clickhouse-driver
        client = Client(host=CH_HOST, port=9000, user=CH_USER, password=CH_PASS)

        client.execute(f"CREATE DATABASE IF NOT EXISTS {CH_DB}")
        client.execute(f"USE {CH_DB}")

        client.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id String,
                account_number String,
                customer_name String,
                transaction_time DateTime64(3, 'UTC'),
                transaction_amount Float64,
                currency String,
                city String,
                country String,
                merchant_name String,
                payment_method String,
                ip_address String,
                transaction_type String,
                phone_number String,
                is_vip UInt8,
                category String,
                status String,
                fee Float64,
                balance_before Float64,
                balance_after Float64,
                risk_score Float64,
                device_type String,
                browser_agent String,
                source_db_updated_at DateTime64(3, 'UTC'),
                processed_at DateTime DEFAULT now()
            ) ENGINE = ReplacingMergeTree(source_db_updated_at)
            ORDER BY (transaction_id, account_number)
        """)
        print(f"[OK] ClickHouse DB & Table Ready: {CH_DB}.transactions")
    except Exception as e:
        print(f"[ERROR] ClickHouse Error: {e}")


def setup_superset():
    print("Superset is configured to self-initialize via its entrypoint script.")
    print(
        "Ensure you have run 'docker compose up -d --build superset' to apply changes."
    )


if __name__ == "__main__":
    print("STARTING END-TO-END PIPELINE SETUP")
    print("=" * 40)
    setup_postgres()
    setup_clickhouse()
    setup_debezium()
    setup_superset()
    print("=" * 40)
    print("ALL SYSTEMS READY!")
    print("1. Start generator: python generator/main.py")
    print("2. Start Spark Pipeline in your Notebook")
    print("3. Open Superset: http://localhost:8089")
