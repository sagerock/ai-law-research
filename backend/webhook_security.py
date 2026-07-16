import hmac
import ipaddress
import os

from fastapi import HTTPException


COURTLISTENER_WEBHOOK_IPS = frozenset({"34.210.230.218", "54.189.59.91"})


def _nearest_public_address(forwarded_for: str | None, client_host: str | None) -> str | None:
    candidates = [part.strip() for part in (forwarded_for or "").split(",") if part.strip()]
    if client_host:
        candidates.append(client_host)

    # Work backwards to find the nearest public address, preventing a caller
    # from spoofing the leftmost X-Forwarded-For value.
    for candidate in reversed(candidates):
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_global:
            return str(address)
    return None


def require_courtlistener_source(
    real_ip: str | None,
    forwarded_for: str | None,
    client_host: str | None,
) -> None:
    """Allow webhook traffic only from CourtListener's documented static IPs.

    Railway's edge proxy reports the client's remote address in X-Real-IP and
    does not populate X-Forwarded-For, so X-Real-IP is authoritative when
    present. The X-Forwarded-For walk remains as a fallback for environments
    without that header (local dev, other proxies).
    """
    source_ip = None
    if real_ip and real_ip.strip():
        try:
            source_ip = str(ipaddress.ip_address(real_ip.strip()))
        except ValueError:
            source_ip = None
    else:
        source_ip = _nearest_public_address(forwarded_for, client_host)

    if source_ip not in COURTLISTENER_WEBHOOK_IPS:
        print(
            "Rejected webhook delivery: "
            f"source={source_ip} x-real-ip={real_ip!r} "
            f"x-forwarded-for={forwarded_for!r} client={client_host!r}"
        )
        raise HTTPException(status_code=401, detail="Invalid webhook source")


def require_kofi_verification_token(provided_token: object) -> None:
    expected_token = os.getenv("KOFI_VERIFICATION_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="Ko-fi webhook authentication is not configured")
    if not isinstance(provided_token, str) or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid webhook credentials")
