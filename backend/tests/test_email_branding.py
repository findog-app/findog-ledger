from app.core.config import settings
from app.utils import (
    generate_new_account_email,
    generate_reset_password_email,
    generate_test_email,
)


def test_account_email_previews_use_oblidog_branding(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "PROJECT_NAME", "Oblidog")

    emails = (
        generate_test_email("recipient@example.com"),
        generate_reset_password_email(
            "recipient@example.com", "user@example.com", "token"
        ),
        generate_new_account_email(
            "recipient@example.com", "user@example.com", "password"
        ),
    )

    for email in emails:
        assert "Oblidog" in email.subject
        assert "Oblidog" in email.html_content
        assert "Findog" not in email.subject
        assert "Findog" not in email.html_content
