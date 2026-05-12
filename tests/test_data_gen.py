import pytest
from main import generate_transaction


def test_generate_transaction_schema():
    """Test if the generated transaction has all required keys."""
    tx = generate_transaction()
    required_keys = [
        "transactionId",
        "userId",
        "timestamp",
        "amount",
        "currency",
        "city",
        "country",
        "merchantName",
        "paymentMethod",
        "ipAddress",
        "transaction_type",
        "phone_number",
    ]
    for key in required_keys:
        assert key in tx, f"Missing key: {key}"


def test_generate_transaction_values():
    """Test if transaction values are within logical bounds."""
    tx = generate_transaction()
    assert tx["amount"] > 0, "Amount must be positive"
    assert len(tx["currency"]) == 3, "Currency should be a 3-letter code"
    assert tx["transaction_type"] in [
        "DEPOSIT",
        "WITHDRAWAL",
        "PAYMENT",
        "TRANSFER",
    ], "Invalid transaction type"


def test_admin_phone_format():
    """Check if phone number starts with '+'."""
    tx = generate_transaction()
    assert tx["phone_number"].startswith("+"), "Phone number should have country code"
