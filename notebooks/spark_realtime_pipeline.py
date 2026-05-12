"""
╔══════════════════════════════════════════════════════════════╗
║     BANK-GRADE CDC STREAMING PIPELINE                        ║
║     Reads Debezium CDC events from Kafka, applies            ║
║     transformations in Spark Structured Streaming, writes    ║
║     results to ClickHouse, and dispatches email alerts       ║
║     for monitored (admin) accounts.                          ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, from_json, when
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    StringType,
    StructField,
    StructType,
)

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

KAFKA_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "")
ADMIN_USER: str = os.getenv("ADMIN_USERNAME", "shehab_admin")

EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "").strip()
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "").replace(" ", "").strip()
EMAIL_RECEIVER: str = os.getenv("EMAIL_RECEIVER", "").strip()

CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_INSERT_URL: str = (
    f"http://{CLICKHOUSE_HOST}:8123/" "?query=INSERT%20INTO%20financial_dw.transactions%20FORMAT%20JSONEachRow"
)

# ──────────────────────────────────────────────────────────────
# Debezium Payload Schema
# ──────────────────────────────────────────────────────────────

_AFTER_SCHEMA = StructType(
    [
        StructField("transaction_id", StringType()),
        StructField("account_number", StringType()),
        StructField("customer_name", StringType()),
        StructField("timestamp", StringType()),
        StructField("amount", DoubleType()),
        StructField("currency", StringType()),
        StructField("city", StringType()),
        StructField("country", StringType()),
        StructField("merchant_name", StringType()),
        StructField("payment_method", StringType()),
        StructField("ip_address", StringType()),
        StructField("transaction_type", StringType()),
        StructField("phone_number", StringType()),
        StructField("is_vip", BooleanType()),
        StructField("category", StringType()),
        StructField("status", StringType()),
        StructField("fee", DoubleType()),
        StructField("balance_before", DoubleType()),
        StructField("balance_after", DoubleType()),
        StructField("risk_score", DoubleType()),
        StructField("device_type", StringType()),
        StructField("browser_agent", StringType()),
        StructField("source_db_updated_at", StringType()),
    ]
)

DEBEZIUM_SCHEMA = StructType(
    [
        StructField(
            "payload",
            StructType(
                [
                    StructField("after", _AFTER_SCHEMA),
                    StructField("op", StringType()),
                ]
            ),
        )
    ]
)

# ──────────────────────────────────────────────────────────────
# Spark Session
# ──────────────────────────────────────────────────────────────


def build_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("BankGrade-CDC-Pipeline-v2")
        .master("local[*]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0",
        )
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )


# ──────────────────────────────────────────────────────────────
# Stream Transformations
# ──────────────────────────────────────────────────────────────


def read_kafka_stream(spark: SparkSession) -> DataFrame:
    """Read raw Debezium CDC events from Kafka and parse the JSON envelope."""
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "earliest")
        .load()
    )
    return (
        raw.selectExpr("CAST(value AS STRING)")
        .select(from_json(col("value"), DEBEZIUM_SCHEMA).alias("d"))
        .select("d.payload.after.*", "d.payload.op")
        .filter(col("op").isin("c", "u"))  # inserts and updates only
    )


def apply_transformations(df: DataFrame) -> DataFrame:
    """
    Rename and cast columns to match the ClickHouse data-warehouse schema.
    """
    return df.na.fill(
        {
            "merchant_name": "Unknown",
            "city": "Unknown",
            "country": "Unknown",
            "phone_number": "N/A",
            "payment_method": "N/A",
            "ip_address": "0.0.0.0",
            "category": "Other",
            "status": "PENDING",
            "device_type": "Unknown",
            "browser_agent": "N/A",
            "amount": 0.0,
            "risk_score": 0.0,
            "fee": 0.0,
            "balance_before": 0.0,
            "balance_after": 0.0,
        }
    ).select(
        col("transaction_id"),
        col("account_number"),
        col("customer_name"),
        col("amount").alias("transaction_amount"),
        col("currency"),
        col("transaction_type"),
        col("timestamp").cast("timestamp").alias("transaction_time"),
        col("merchant_name"),
        col("city"),
        col("country"),
        col("phone_number"),
        col("payment_method"),
        col("ip_address"),
        when(col("is_vip"), 1).otherwise(0).cast("integer").alias("is_vip"),
        col("category"),
        col("status"),
        col("fee"),
        col("balance_before"),
        col("balance_after"),
        col("risk_score"),
        col("device_type"),
        col("browser_agent"),
        col("source_db_updated_at").cast("timestamp").alias("source_db_updated_at"),
    )


# ──────────────────────────────────────────────────────────────
# Email Notifications
# ──────────────────────────────────────────────────────────────

_EMAIL_TEMPLATE = """\
<html>
<body style="font-family:sans-serif;color:#333;margin:0;padding:0;">
  <div style="max-width:600px;margin:auto;border:1px solid #ddd;border-radius:10px;overflow:hidden;">
    <div style="background:#1a73e8;color:white;padding:20px;text-align:center;">
      <h2 style="margin:0;">Official Transaction Alert</h2>
    </div>
    <div style="padding:24px;">
      <p>Dear <strong>{customer_name}</strong>,</p>
      <p>A transaction has been detected on your account:</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr style="background:#f9f9f9;">
          <td style="padding:10px;"><b>Amount</b></td>
          <td style="padding:10px;color:#d93025;font-size:1.2em;">
            {transaction_amount} {currency}
          </td>
        </tr>
        <tr>
          <td style="padding:10px;"><b>Category</b></td>
          <td style="padding:10px;">{category}</td>
        </tr>
        <tr style="background:#f9f9f9;">
          <td style="padding:10px;"><b>Merchant / Branch</b></td>
          <td style="padding:10px;">{merchant_name}</td>
        </tr>
        <tr>
          <td style="padding:10px;"><b>New Balance</b></td>
          <td style="padding:10px;"><b>{balance_after} {currency}</b></td>
        </tr>
        <tr style="background:#fff3cd;">
          <td style="padding:10px;"><b>Risk Score</b></td>
          <td style="padding:10px;">{risk_score:.2f} / 1.0</td>
        </tr>
      </table>
      <p style="font-size:12px;color:#888;margin-top:16px;">
        Device: {device_type} &nbsp;|&nbsp; Location: {city}, {country}
      </p>
    </div>
  </div>
</body>
</html>
"""


def send_email_alert(row_dict: dict) -> None:
    """
    Send an HTML transaction alert via Gmail SMTP (SSL, port 465).
    Silently skips if email credentials are not configured.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        logger.warning("Email credentials missing — skipping alert.")
        return

    # Handle None values for numeric fields before formatting
    row_dict["risk_score"] = row_dict.get("risk_score") or 0.0
    row_dict["transaction_amount"] = row_dict.get("transaction_amount") or 0.0
    row_dict["balance_after"] = row_dict.get("balance_after") or 0.0

    subject = f"BANK ALERT: {row_dict['transaction_type']} of " f"{row_dict['transaction_amount']} {row_dict['currency']}"
    html_body = _EMAIL_TEMPLATE.format(**row_dict)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("Email alert sent for txn %s", row_dict["transaction_id"][:8])
    except Exception as exc:
        logger.error("Email delivery failed: %s", exc)


# ──────────────────────────────────────────────────────────────
# ClickHouse Sink
# ──────────────────────────────────────────────────────────────


def write_to_clickhouse(pandas_df) -> None:
    """
    Bulk-insert a pandas DataFrame into ClickHouse via the HTTP interface.
    Uses JSONEachRow format for compatibility with all ClickHouse versions.
    """
    json_payload = pandas_df.to_json(orient="records", date_format="iso", lines=True)
    # Formatting dates for ClickHouse compatibility
    for col_name in ["transaction_time", "source_db_updated_at"]:
        if col_name in pandas_df.columns:
            pandas_df[col_name] = pandas_df[col_name].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]

    json_payload = pandas_df.to_json(orient="records", date_format="iso", lines=True)
    try:
        resp = requests.post(
            CLICKHOUSE_INSERT_URL,
            data=json_payload,
            auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD),
            timeout=30,
        )
        if resp.status_code != 200:
            logger.error("ClickHouse Error Detail: %s", resp.text)
            resp.raise_for_status()
        logger.info("ClickHouse: %d records written.", len(pandas_df))
    except requests.RequestException as exc:
        error_msg = exc.response.text if exc.response else str(exc)
        logger.error("ClickHouse write failed: %s | Details: %s", exc, error_msg)


# ──────────────────────────────────────────────────────────────
# Micro-batch Processor
# ──────────────────────────────────────────────────────────────


def process_batch(df: DataFrame, epoch_id: int) -> None:
    """
    Called by Spark for each micro-batch.
    1. Write all records to ClickHouse.
    2. Send email alerts for any admin-user transactions.
    """
    count = df.count()
    if count == 0:
        return

    logger.info("[Batch %d] Processing %d records.", epoch_id, count)
    pandas_df = df.toPandas()

    # Sink to ClickHouse
    write_to_clickhouse(pandas_df)

    # Alerts for the admin / monitored account
    admin_rows = df.filter(col("account_number") == ADMIN_USER).collect()
    for row in admin_rows:
        send_email_alert(row.asDict())


# ──────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────


def main() -> None:
    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    raw_stream = read_kafka_stream(spark)
    final_stream = apply_transformations(raw_stream)

    query = final_stream.writeStream.foreachBatch(process_batch).outputMode("update").start()

    logger.info("Bank-Grade CDC pipeline is running...")
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
