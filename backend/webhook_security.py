import hmac
import ipaddress
import os

from fastapi import HTTPException


COURTLISTENER_WEBHOOK_IPS = frozenset({"34.210.230.218", "54.189.59.91"})


def require_courtlistener_source(forwarded_for: str | None, client_host: str | None) -> None:
    """Allow webhook traffic only from CourtListener's documented static IPs."""
    candidates = [part.strip() for part in (forwarded_for or "").split(",") if part.strip()]
    if client_host:
        candidates.append(client_host)

    # Railway's internal proxy appears last at request.client. Work backwards to
    # find the nearest public address, preventing a caller from spoofing the
    # leftmost X-Forwarded-For value.
    source_ip = None
    for candidate in reversed(candidates):
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_global:
            source_ip = str(address)
            break

    if source_ip not in COURTLISTENER_WEBHOOK_IPS:
        raise HTTPException(status_code=401, detail="Invalid webhook source")


def require_kofi_verification_token(provided_token: object) -> None:
    expected_token = os.getenv("KOFI_VERIFICATION_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="Ko-fi webhook authentication is not configured")
    if not isinstance(provided_token, str) or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid webhook credentials")
