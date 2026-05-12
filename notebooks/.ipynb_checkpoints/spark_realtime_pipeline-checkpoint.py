from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, current_timestamp, lit
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from requests.auth import HTTPBasicAuth
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

# Configuration from .env
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
CH_URL = f"jdbc:clickhouse://{os.getenv('CLICKHOUSE_HOST')}:{os.getenv('CLICKHOUSE_PORT')}/{os.getenv('CLICKHOUSE_DB')}"
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD")
ADMIN_USER = os.getenv("ADMIN_USERNAME")

# Email Config
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# Twilio Config
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}"

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("RealTimeCDC-ClickHouse") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

# Define Schema for Debezium JSON (Comprehensive)
schema = StructType([
    StructField("payload", StructType([
        StructField("after", StructType([
            StructField("transaction_id", StringType()),
            StructField("user_id", StringType()),
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
            StructField("is_vip", StringType()) # Debezium might send as string or boolean
        ])),
        StructField("op", StringType())
    ]))
])

# Read from Kafka
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "earliest") \
    .load()

# Parse JSON payload
parsed_df = kafka_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.payload.after.*", "data.payload.op") \
    .filter(col("op").isin(["c", "u"]))

# Transformations
final_df = parsed_df.withColumn("source_db_updated_at", current_timestamp()) \
    .withColumn("is_vip_clean", when(col("is_vip") == "true", 1).otherwise(0)) \
    .select(
        col("transaction_id"),
        col("user_id").alias("account_number"),
        col("user_id").alias("customer_name"), # Using user_id as name for now
        col("amount").cast("double").alias("transaction_amount"),
        col("currency"),
        col("transaction_type"),
        col("timestamp").cast("timestamp").alias("transaction_time"),
        col("merchant_name"),
        col("city"),
        col("country"),
        col("phone_number"),
        col("is_vip_clean").alias("is_vip"),
        col("source_db_updated_at")
    )

def send_email_notification(subject, row):
    """
    Sends a professional HTML Email notification.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("\n[SIMULATED EMAIL] Sender credentials missing.")
        return

    html_content = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1a73e8; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Transaction Notification</h1>
            </div>
            <div style="padding: 20px;">
                <p>Dear <strong>{row['customer_name']}</strong>,</p>
                <p>This is an automated alert to inform you that a transaction has been successfully processed on your account.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #eee;"><strong>Transaction Type</strong></td>
                        <td style="padding: 10px; border: 1px solid #eee;">{row['transaction_type']}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #eee;"><strong>Amount</strong></td>
                        <td style="padding: 10px; border: 1px solid #eee; color: #d93025; font-size: 18px;"><strong>{row['transaction_amount']} {row['currency']}</strong></td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 10px; border: 1px solid #eee;"><strong>Merchant</strong></td>
                        <td style="padding: 10px; border: 1px solid #eee;">{row['merchant_name']}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #eee;"><strong>Date & Time</strong></td>
                        <td style="padding: 10px; border: 1px solid #eee;">{row['transaction_time']}</td>
                    </tr>
                </table>

                <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 4px; border: 1px solid #ffeeba; font-size: 14px;">
                    <strong>Security Tip:</strong> If you did not authorize this transaction, please contact our support immediately at 19xxx.
                </div>
            </div>
            <div style="background-color: #f1f3f4; color: #70757a; padding: 15px; text-align: center; font-size: 12px;">
                <p>Transaction Reference: {row['transaction_id']}<br>
                &copy; 2026 Future Bank CDC System. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"\n[SUCCESS] Professional Email sent to {EMAIL_RECEIVER}")
    except Exception as e:
        print(f"\n[ERROR] Failed to send Email: {str(e)}")

def send_whatsapp_notification(phone, row):
    """
    Sends a bank-style formatted WhatsApp message via Twilio API.
    """
    if not TWILIO_SID or not TWILIO_TOKEN or "your_auth_token" in TWILIO_TOKEN:
        print(f"\n[SIMULATED WHATSAPP] To: {phone} | Message: Official Transaction Alert for {row['transaction_amount']} {row['currency']}")
        return

    msg = f"""
🏛️ *OFFICIAL TRANSACTION ALERT*

Dear *{row['customer_name']}*,

A *{row['transaction_type']}* was processed successfully.
💰 *Amount:* {row['transaction_amount']} {row['currency']}
🏢 *At:* {row['merchant_name']}
🕒 *Time:* {row['transaction_time']}

*Ref ID:* `{row['transaction_id'][:8]}...`

_If this was not you, please call support immediately._
    """
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = {
        "From": TWILIO_FROM,
        "To": f"whatsapp:{phone}",
        "Body": msg
    }
    
    try:
        response = requests.post(url, data=data, auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN))
        if response.status_code == 201:
            print(f"\n[SUCCESS] WhatsApp sent to {phone}")
        else:
            print(f"\n[ERROR] Failed to send WhatsApp: {response.text}")
    except Exception as e:
        print(f"\n[EXCEPTION] Error sending WhatsApp: {str(e)}")

def process_batch(df, epoch_id):
    if df.isEmpty():
        return

    # --- Great Expectations Validation ---
    print(f"\n[GX] Validating Batch {epoch_id}...")
    
    # Create a GX validator for the current Spark DataFrame
    # Using the Pandas-like API of GX for simplicity in Spark batches
    # For a more robust setup, we would use a full DataContext
    validator = gx.from_pandas(df.toPandas()) # Converting small micro-batch to Pandas for easy validation
    
    # Define Expectations
    validator.expect_column_values_to_not_be_null("transaction_id")
    validator.expect_column_values_to_be_between("transaction_amount", min_value=0)
    validator.expect_column_values_to_be_in_set("transaction_type", ["DEPOSIT", "WITHDRAWAL", "PAYMENT", "TRANSFER", "Manual_Entry"])
    
    validation_result = validator.validate()
    
    if not validation_result.success:
        print(f"⚠️ [DATA QUALITY ALERT] Batch {epoch_id} failed validation!")
        # Send a High Priority Email Alert
        subject = "🚨 CRITICAL: Data Quality Failure in CDC Pipeline"
        body = f"Data Quality Validation failed for batch {epoch_id}.\nResults: {validation_result}"
        send_email_notification(subject, {"customer_name": "Admin", "transaction_type": "DATA_QUALITY_ERROR", "transaction_amount": 0, "currency": "N/A", "merchant_name": "GX_ENGINE", "transaction_time": "NOW", "transaction_id": "ERROR"})
    else:
        print(f"✅ [GX] Batch {epoch_id} passed all quality checks.")

    # 1. Write to ClickHouse (Only if valid or as a choice)
    df.write \
        .format("jdbc") \
        .option("url", CH_URL) \
        .option("dbtable", "transactions") \
        .option("user", CH_USER) \
        .option("password", CH_PASS) \
        .option("driver", "com.clickhouse.jdbc.ClickHouseDriver") \
        .mode("append") \
        .save()

    # 2. Check for Admin Transactions and send Alerts
    admin_txs = df.filter(col("account_number") == ADMIN_USER).collect()
    for row in admin_txs:
        subject = f"🚨 SECURITY ALERT: {row['transaction_type']} of {row['transaction_amount']} {row['currency']}"
        
        # Send Professional Email (HTML)
        send_email_notification(subject, row)
        
        # Log Professional WhatsApp
        send_whatsapp_notification(row['phone_number'], row)

# Start Sinks
query = final_df.writeStream \
    .foreachBatch(process_batch) \
    .outputMode("update") \
    .start()

print("Real-time Professional Pipeline with VIP WhatsApp Notifications Started...")
spark.streams.awaitAnyTermination()
