from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import html
import json
import re
import warnings
from typing import Any, Iterable


COURTLISTENER_API_BASE = "https://www.courtlistener.com/api/rest/v4"
DOCUMENT_FORMAT_VERSION = 1
MARKER_PREFIX = "[[COURTLISTENER_SUBOPINION "

# CourtListener's exact Opinion.type values. The misspelling in
# 015unamimous is part of their public data model.
TYPE_TO_PART = {
    "010combined": "opinion",
    "015unamimous": "majority",
    "020lead": "majority",
    "025plurality": "majority",
    "030concurrence": "concurrence",
    "035concurrenceinpart": "dissent",
    "040dissent": "dissent",
    "050addendum": "other",
    "060remittitur": "other",
    "070rehearing": "other",
    "080onthemerits": "majority",
    "090onmotiontostrike": "other",
    "100trialcourt": "other",
}
PRIMARY_TYPES = frozenset({"015unamimous", "020lead", "025plurality", "080onthemerits"})


@dataclass(frozen=True)
class SubOpinion:
    opinion_id: str | None
    type_code: str | None
    author: str | None
    text: str
    source_field: str | None = None
    ordering_key: int | float | None = None


@dataclass(frozen=True)
class OpinionDocument:
    cluster_id: str
    text: str
    parts: tuple[SubOpinion, ...]
    assembly: str
    format_version: int
    sha256: str

    def manifest(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "assembly": self.assembly,
            "cluster_id": self.cluster_id,
            "sha256": self.sha256,
            "parts": [
                {
                    "id": part.opinion_id,
                    "type": part.type_code,
                    "author": part.author,
                    "source_field": part.source_field,
                }
                for part in self.parts
            ],
        }


def _html_to_text(value: str) -> str:
    try:
        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
            return BeautifulSoup(value, "html.parser").get_text(separator="\n", strip=True)
    except ImportError:
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", value)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</blockquote>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        lines = [re.sub(r"\s+", " ", html.unescape(line)).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)


def extract_opinion_text(opinion_data: dict[str, Any]) -> tuple[str, str | None]:
    """Extract the best available text while preserving HTML block boundaries."""
    for field in (
        "html_with_citations",
        "plain_text",
        "html_lawbox",
        "html",
        "html_columbia",
        "xml_harvard",
    ):
        value = opinion_data.get(field)
        if not isinstance(value, str) or len(value.strip()) <= 100:
            continue
        text = value if field == "plain_text" else _html_to_text(value)
        if len(text.strip()) > 100:
            return text.strip(), field
    return "", None


def sub_opinion_from_api(opinion_data: dict[str, Any]) -> SubOpinion | None:
    text, source_field = extract_opinion_text(opinion_data)
    if not text:
        return None
    author = opinion_data.get("author_str")
    if not author and opinion_data.get("per_curiam"):
        author = "per curiam"
    opinion_id = opinion_data.get("id")
    return SubOpinion(
        opinion_id=str(opinion_id) if opinion_id is not None else None,
        type_code=opinion_data.get("type"),
        author=author or None,
        text=text,
        source_field=source_field,
        ordering_key=opinion_data.get("ordering_key"),
    )


def encode_sub_opinion_marker(part: SubOpinion, default_part: str | None = None) -> str:
    metadata = {
        "id": part.opinion_id,
        "type": part.type_code,
        "part": default_part or TYPE_TO_PART.get(
            part.type_code, "opinion" if not part.type_code else "other"
        ),
        "author": part.author,
        "source_field": part.source_field,
    }
    return MARKER_PREFIX + json.dumps(metadata, ensure_ascii=True, separators=(",", ":")) + "]]"


def _part_sort_key(part: SubOpinion) -> tuple[Any, ...]:
    has_order = part.ordering_key is not None
    return (
        0 if has_order else 1,
        part.ordering_key if has_order else 0,
        part.type_code or "999unknown",
        part.opinion_id or "",
    )


def assemble_sub_opinions(cluster_id: str, parts: Iterable[SubOpinion]) -> OpinionDocument | None:
    usable = [part for part in parts if len(part.text.strip()) > 100]
    if not usable:
        return None

    combined = [part for part in usable if part.type_code == "010combined"]
    components = [part for part in usable if part.type_code != "010combined"]
    if components and (
        not combined
        or (len(components) > 1 and any(part.type_code in PRIMARY_TYPES for part in components))
    ):
        selected = components
        assembly = "components"
    elif combined:
        selected = [sorted(combined, key=_part_sort_key)[0]]
        assembly = "combined"
    else:
        selected = components
        assembly = "components"

    selected = sorted(selected, key=_part_sort_key)
    combined_default = (
        "majority"
        if assembly == "combined" and any(part.type_code in PRIMARY_TYPES for part in components)
        else None
    )
    text = "\n\n\n".join(
        f"{encode_sub_opinion_marker(part, combined_default)}\n{part.text.strip()}"
        for part in selected
    )
    return OpinionDocument(
        cluster_id=str(cluster_id),
        text=text,
        parts=tuple(selected),
        assembly=assembly,
        format_version=DOCUMENT_FORMAT_VERSION,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


async def _get_with_retry(client: Any, url: str, **kwargs: Any) -> Any:
    """One retry on a failed request: a single transient sub-opinion error
    otherwise refuses the whole cluster (complete-fetch invariant)."""
    for attempt in (1, 2):
        try:
            response = await client.get(url, **kwargs)
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(1.0)
            continue
        if response.status_code == 200 or attempt == 2:
            return response
        await asyncio.sleep(1.0)
    return response


async def fetch_courtlistener_document(
    cluster_id: str,
    api_key: str | None,
    *,
    client: Any = None,
) -> OpinionDocument | None:
    if not str(cluster_id).isdigit():
        return None
    if not api_key:
        raise RuntimeError("COURTLISTENER_API_KEY is not configured")
    headers = {"Authorization": f"Token {api_key}"}
    owns_client = client is None
    if client is None:
        import httpx

        client = httpx.AsyncClient()
    try:
        response = await _get_with_retry(
            client,
            f"{COURTLISTENER_API_BASE}/clusters/{cluster_id}/",
            headers=headers,
            timeout=30.0,
        )
        if response.status_code != 200:
            return None
        opinion_data_by_id: dict[str, dict[str, Any]] = {}
        opinion_urls = response.json().get("sub_opinions", [])
        expected_ids = {
            str(opinion_url).rstrip("/").split("/")[-1]
            for opinion_url in opinion_urls
        }
        for opinion_url in opinion_urls:
            opinion_id = str(opinion_url).rstrip("/").split("/")[-1]
            opinion_response = await _get_with_retry(
                client,
                f"{COURTLISTENER_API_BASE}/opinions/{opinion_id}/",
                headers=headers,
                timeout=30.0,
            )
            if opinion_response.status_code == 200:
                opinion_data_by_id[opinion_id] = opinion_response.json()

        if not opinion_data_by_id or (
            expected_ids is not None and not expected_ids.issubset(opinion_data_by_id)
        ):
            search = await _get_with_retry(
                client,
                f"{COURTLISTENER_API_BASE}/opinions/",
                params={"cluster": cluster_id},
                headers=headers,
                timeout=30.0,
            )
            if search.status_code == 200:
                for result in search.json().get("results", []):
                    result_id = result.get("id")
                    if result_id is not None:
                        opinion_data_by_id[str(result_id)] = result

        # Never persist a partial cluster after a transient sub-opinion failure.
        if not expected_ids.issubset(opinion_data_by_id):
            return None

        parts = [
            part for data in opinion_data_by_id.values()
            if (part := sub_opinion_from_api(data))
        ]
        usable_ids = {part.opinion_id for part in parts}
        if not expected_ids.issubset(usable_ids):
            return None
        return assemble_sub_opinions(str(cluster_id), parts)
    finally:
        if owns_client:
            await client.aclose()
