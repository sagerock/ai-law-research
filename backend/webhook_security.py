import hmac
import os

from fastapi import HTTPException


def require_webhook_secret(provided_secret: str | None) -> None:
    expected_secret = os.getenv("COURTLISTENER_WEBHOOK_SECRET") or os.getenv("WEBHOOK_SECRET")
    if not expected_secret:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured")
    if not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook credentials")


def require_kofi_verification_token(provided_token: object) -> None:
    expected_token = os.getenv("KOFI_VERIFICATION_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="Ko-fi webhook authentication is not configured")
    if not isinstance(provided_token, str) or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid webhook credentials")
