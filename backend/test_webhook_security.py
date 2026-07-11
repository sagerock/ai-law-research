import pytest
from fastapi import HTTPException

from webhook_security import require_kofi_verification_token, require_webhook_secret


def test_webhook_secret_accepts_matching_value(monkeypatch):
    monkeypatch.setenv("COURTLISTENER_WEBHOOK_SECRET", "court-secret")
    require_webhook_secret("court-secret")


def test_webhook_secret_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("COURTLISTENER_WEBHOOK_SECRET", "court-secret")
    with pytest.raises(HTTPException) as exc:
        require_webhook_secret("wrong")
    assert exc.value.status_code == 401


def test_webhook_secret_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.delenv("COURTLISTENER_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_webhook_secret(None)
    assert exc.value.status_code == 503


def test_kofi_token_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("KOFI_VERIFICATION_TOKEN", "kofi-token")
    with pytest.raises(HTTPException) as exc:
        require_kofi_verification_token("wrong")
    assert exc.value.status_code == 401
