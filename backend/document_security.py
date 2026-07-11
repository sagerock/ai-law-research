import asyncio
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException, UploadFile


MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_REMOTE_REDIRECTS = 3


async def read_upload_limited(
    file: UploadFile,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> bytes:
    content = bytearray()
    while chunk := await file.read(min(1024 * 1024, max_bytes + 1 - len(content))):
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(status_code=413, detail="File size limit is 10MB")
    return bytes(content)


def allowed_storage_hosts() -> set[str]:
    hosts = {
        host.strip().lower()
        for host in os.getenv("OUTLINE_STORAGE_HOSTS", "").split(",")
        if host.strip()
    }
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url and urlparse(supabase_url).hostname:
        hosts.add(urlparse(supabase_url).hostname.lower())
    return hosts


async def validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Invalid outline storage URL")

    hosts = allowed_storage_hosts()
    if not hosts:
        raise HTTPException(status_code=503, detail="Outline storage is not configured")
    if host.lower() not in hosts:
        raise HTTPException(status_code=400, detail="Outline storage host is not allowed")

    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Outline storage host could not be resolved")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise HTTPException(status_code=400, detail="Outline storage address is not public")


async def download_storage_file(
    url: str,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> bytes:
    current_url = url
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for redirect_count in range(MAX_REMOTE_REDIRECTS + 1):
            await validate_remote_url(current_url)
            async with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    if redirect_count == MAX_REMOTE_REDIRECTS:
                        raise HTTPException(status_code=400, detail="Too many storage redirects")
                    location = response.headers.get("location")
                    if not location:
                        raise HTTPException(status_code=400, detail="Invalid storage redirect")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > max_bytes:
                            raise HTTPException(status_code=413, detail="Remote file size limit is 10MB")
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid remote file response")

                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise HTTPException(status_code=413, detail="Remote file size limit is 10MB")
                return bytes(content)

    raise HTTPException(status_code=400, detail="Could not download outline file")
