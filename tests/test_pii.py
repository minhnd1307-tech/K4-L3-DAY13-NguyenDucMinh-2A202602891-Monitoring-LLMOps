from app.logging_config import scrub_event
from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd_and_payment_card_even_in_nested_log_fields() -> None:
    event = {"session_id": "079203001234", "payload": {"items": ["4111 1111 1111 1111"]}}
    safe = scrub_event(None, "info", event)
    assert safe["session_id"] == "[REDACTED_CCCD]"
    assert safe["payload"]["items"] == ["[REDACTED_CREDIT_CARD]"]
