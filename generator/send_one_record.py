import os
import time
import logging
import psycopg2
import pywhatkit
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────
# Setup & Config
# ──────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Credentials
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "financial_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "shehab_admin")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+201289910575")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", EMAIL_SENDER)

def send_postgres_record():
    """Inserts one high-risk admin record into Postgres (Full v2 Schema)."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        cur = conn.cursor()
        
        txn_id = str(uuid.uuid4())
        amount = 55000.00
        
        sql = """
            INSERT INTO transactions (
                transaction_id, account_number, customer_name, timestamp, amount, currency,
                city, country, merchant_name, payment_method,
                ip_address, transaction_type, phone_number, is_vip,
                category, status, fee, balance_before, balance_after,
                risk_score, device_type, browser_agent, source_db_updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(sql, (
            txn_id, "ACC-ADMIN-001", ADMIN_USERNAME, datetime.now(timezone.utc), amount, "EGP",
            "Cairo", "Egypt", "VIP-Terminal-01", "credit_card",
            "127.0.0.1", "TRANSFER", ADMIN_PHONE, True,
            "Investment", "SUCCESS", 50.0, 100000.0, 44950.0,
            0.95, "Admin-Console", "Security-Module-v2", datetime.now(timezone.utc)
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"✅ Record inserted for {ADMIN_USERNAME} (ID: {txn_id})")
        return txn_id, amount
    except Exception as e:
        logger.error(f"❌ Postgres Error: {e}")
        return None, None

def send_gmail_alert(amount, txn_id):
    """Sends a professional bilingual HTML Gmail notification."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        logger.warning("⚠️ Email credentials missing in .env")
        return

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"CDC Security System <{EMAIL_SENDER}>"
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"🚨 تنبيه أمني: عملية بمبلغ كبير | Security Alert: High-Value Transaction"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-top: 5px solid #d32f2f; padding: 20px;">
                    <h2 style="color: #d32f2f; text-align: center;">🚨 تنبيه أمني حرج | Critical Security Alert</h2>
                    <div style="direction: rtl; text-align: right; background: #fff4f4; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                        <p>عزيزي المستخدم،</p>
                        <p>نحيطكم علماً بأنه قد تم اكتشاف عملية تحويل <b>بمبلغ كبير</b> على حسابكم:</p>
                        <ul style="list-style: none; padding: 0;">
                            <li>💰 <b>المبلغ:</b> {amount:,.2f} جنيه مصري</li>
                            <li>👤 <b>المستخدم:</b> {ADMIN_USERNAME}</li>
                            <li>🆔 <b>رقم العملية:</b> {txn_id}</li>
                        </ul>
                    </div>
                    <div style="direction: ltr; text-align: left; background: #f9f9f9; padding: 15px; border-radius: 5px;">
                        <p>Dear Admin,</p>
                        <p>A <b>high-value transaction</b> has been detected on your account:</p>
                        <ul style="list-style: none; padding: 0;">
                            <li>💰 <b>Amount:</b> {amount:,.2f} EGP</li>
                            <li>👤 <b>User:</b> {ADMIN_USERNAME}</li>
                            <li>🆔 <b>Transaction ID:</b> {txn_id}</li>
                        </ul>
                    </div>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, [EMAIL_RECEIVER], msg.as_string())
        server.quit()
        logger.info(f"📧 Email alert sent to {EMAIL_RECEIVER}!")
    except Exception as e:
        logger.error(f"❌ Gmail Error: {e}")

def send_whatsapp_alert(amount, txn_id):
    """Sends a professional bilingual WhatsApp message."""
    try:
        message = (
            f"🚨 *SECURITY ALERT*\n"
            f"💰 *Amount:* {amount:,.2f} EGP\n"
            f"👤 *User:* {ADMIN_USERNAME}\n"
            f"🆔 *ID:* {txn_id[:8]}\n"
            f"✅ *CDC Monitoring*"
        )
        logger.info(f"📱 Sending WhatsApp to {ADMIN_PHONE}...")
        pywhatkit.sendwhatmsg_instantly(ADMIN_PHONE, message, wait_time=15, tab_close=True)
        logger.info("✅ WhatsApp sent!")
    except Exception as e:
        logger.error(f"❌ WhatsApp Error: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting Full Schema Test...")
    txn_id, amount = send_postgres_record()
    if txn_id:
        send_gmail_alert(amount, txn_id)
        send_whatsapp_alert(amount, txn_id)
        logger.info("🏁 Test complete.")