import pytest
from fastapi import HTTPException

from webhook_security import require_courtlistener_source, require_kofi_verification_token


def test_courtlistener_source_accepts_forwarded_static_ip():
    require_courtlistener_source("34.210.230.218", "100.64.0.14")


def test_courtlistener_source_accepts_static_ip_before_private_proxy_chain():
    require_courtlistener_source("54.189.59.91, 100.64.0.14", "100.64.0.15")


def test_courtlistener_source_rejects_unknown_ip():
    with pytest.raises(HTTPException) as exc:
        require_courtlistener_source("203.0.113.10", "100.64.0.14")
    assert exc.value.status_code == 401


def test_courtlistener_source_rejects_spoofed_leftmost_ip():
    with pytest.raises(HTTPException) as exc:
        require_courtlistener_source(
            "34.210.230.218, 8.8.8.8", "100.64.0.14"
        )
    assert exc.value.status_code == 401


def test_kofi_token_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("KOFI_VERIFICATION_TOKEN", "kofi-token")
    with pytest.raises(HTTPException) as exc:
        require_kofi_verification_token("wrong")
    assert exc.value.status_code == 401
