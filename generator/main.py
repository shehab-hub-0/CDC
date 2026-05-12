"""
Bank-Grade Real-Time Transaction Data Generator (Enriched v2)
"""

import logging
import os
import random  # nosec
import time
from datetime import datetime, timezone
from typing import Any

import faker
import psycopg2
from dotenv import load_dotenv
from psycopg2 import pool

# ──────────────────────────────────────────────────────────────
# Setup & Config
# ──────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

fake = faker.Faker()

# Constants
CURRENCIES = ["EGP", "USD", "EUR", "GBP", "AED"]
PAYMENT_METHODS = ["credit_card", "debit_card", "online_banking", "e-wallet"]
TRANSACTION_TYPES = ["PAYMENT", "TRANSFER", "WITHDRAWAL", "DEPOSIT"]
CATEGORIES = [
    "Groceries",
    "Electronics",
    "Entertainment",
    "Healthcare",
    "Travel",
    "Utilities",
    "Salary",
    "Investment",
]
STATUSES = ["SUCCESS", "SUCCESS", "SUCCESS", "FAILED", "PENDING"]
DEVICES = ["iPhone 15", "Samsung S23", "Windows PC", "MacBook Pro", "Android Tablet"]

_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "shehab_admin")


def generate_transaction() -> dict[str, Any]:
    # 1% chance of a "Whale Transaction" (55,000+)
    if random.random() < 0.01:
        amount = round(random.uniform(55000, 250000), 2)
    else:
        amount = round(random.expovariate(1 / 450.0) + 5.0, 2)

    category = random.choice(CATEGORIES)
    txn_type = random.choice(TRANSACTION_TYPES)

    fee = round(amount * random.uniform(0.001, 0.02), 2) if txn_type in {"PAYMENT", "TRANSFER"} else 0.0
    balance_before = round(random.uniform(5_000, 500_000), 2)
    balance_after = (
        round(balance_before - amount - fee, 2)
        if txn_type in {"PAYMENT", "TRANSFER", "WITHDRAWAL"}
        else round(balance_before + amount, 2)
    )

    risk_score = round(random.uniform(0.0, 0.3), 2)
    if amount > 40000 or (category == "Investment" and amount > 20000):
        risk_score = round(random.uniform(0.5, 0.95), 2)

    return {
        "transaction_id": fake.uuid4(),
        "account_number": fake.iban(),
        "customer_name": fake.name(),
        "timestamp": datetime.now(timezone.utc),
        "amount": amount,
        "currency": random.choice(CURRENCIES),
        "city": fake.city(),
        "country": fake.country(),
        "merchant_name": fake.company(),
        "payment_method": random.choice(PAYMENT_METHODS),
        "ip_address": fake.ipv4(),
        "transaction_type": txn_type,
        "phone_number": f"+201{random.randint(0, 9)}{random.randint(1000000, 9999999)}",
        "is_vip": amount > 20000,
        "category": category,
        "status": random.choice(STATUSES),
        "fee": fee,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "risk_score": risk_score,
        "device_type": random.choice(DEVICES),
        "browser_agent": fake.user_agent(),
        "source_db_updated_at": datetime.now(timezone.utc),
    }


_INSERT_SQL = """
    INSERT INTO transactions (
        transaction_id, account_number, customer_name, timestamp, amount, currency,
        city, country, merchant_name, payment_method,
        ip_address, transaction_type, phone_number, is_vip,
        category, status, fee, balance_before, balance_after,
        risk_score, device_type, browser_agent, source_db_updated_at
    ) VALUES (
        %(transaction_id)s, %(account_number)s, %(customer_name)s, %(timestamp)s, %(amount)s, %(currency)s,
        %(city)s, %(country)s, %(merchant_name)s, %(payment_method)s,
        %(ip_address)s, %(transaction_type)s, %(phone_number)s, %(is_vip)s,
        %(category)s, %(status)s, %(fee)s, %(balance_before)s, %(balance_after)s,
        %(risk_score)s, %(device_type)s, %(browser_agent)s, %(source_db_updated_at)s
    )
"""


def main():
    interval = int(os.getenv("GENERATOR_INTERVAL_SECONDS", 2))
    conn_pool = pool.SimpleConnectionPool(
        1,
        10,
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
    )

    logger.info("🚀 Transaction generator started (interval=%ds)", interval)
    try:
        while True:
            txn = generate_transaction()
            conn = conn_pool.getconn()
            with conn.cursor() as cur:
                cur.execute(_INSERT_SQL, txn)
            conn.commit()
            conn_pool.putconn(conn)
            logger.info(
                "✅ Inserted: %s | %.2f %s | Risk: %.2f",
                txn["customer_name"],
                txn["amount"],
                txn["currency"],
                txn["risk_score"],
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        conn_pool.closeall()


if __name__ == "__main__":
    main()
