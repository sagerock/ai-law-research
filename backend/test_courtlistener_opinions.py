import asyncio

from courtlistener_opinions import (
    SubOpinion,
    assemble_sub_opinions,
    extract_opinion_text,
    fetch_courtlistener_document,
)
from opinion_passages import assess_opinion_boundaries, build_opinion_passages


def part(type_code, text, opinion_id, author=None, ordering_key=None):
    return SubOpinion(opinion_id, type_code, author, text, "plain_text", ordering_key)


def test_components_preserve_every_typed_writing_and_suppress_combined_duplicate():
    document = assemble_sub_opinions("10", [
        part("010combined", "Combined duplicate. " * 20, "1"),
        part("020lead", "Majority text. " * 20, "2", "Justice Lead"),
        part("030concurrence", "Concurrence text. " * 20, "3", "Justice Join"),
        part("040dissent", "Dissent text. " * 20, "4", "Justice Dissent"),
    ])
    assert document is not None
    assert document.assembly == "components"
    assert [value.type_code for value in document.parts] == [
        "020lead", "030concurrence", "040dissent"
    ]
    assert "Combined duplicate" not in document.text
    assert '"part":"majority"' in document.text
    assert '"part":"concurrence"' in document.text
    assert '"part":"dissent"' in document.text
    assert '"source_field":"plain_text"' in document.text


def test_single_dissent_keeps_its_type_marker():
    document = assemble_sub_opinions(
        "11", [part("040dissent", "Only available writing. " * 20, "5")]
    )
    assert document is not None
    assert '"type":"040dissent"' in document.text
    assert '"part":"dissent"' in document.text


def test_combined_record_is_used_when_components_have_no_primary_writing():
    document = assemble_sub_opinions("12", [
        part("010combined", "Complete combined opinion. " * 20, "6"),
        part("040dissent", "Standalone dissent. " * 20, "7"),
    ])
    assert document is not None
    assert document.assembly == "combined"
    assert [value.opinion_id for value in document.parts] == ["6"]


def test_combined_record_keeps_separate_text_and_uses_typed_lead_as_default_boundary():
    document = assemble_sub_opinions("14", [
        part(
            "010combined",
            "Complete majority opinion. " * 20
            + "\n=== Dissent ===\n"
            + "Separate dissenting opinion. " * 20,
            "10",
        ),
        part("020lead", "Duplicated lead only. " * 20, "11"),
    ])
    assert document is not None
    assert document.assembly == "combined"
    assert [value.opinion_id for value in document.parts] == ["10"]
    assert '"type":"010combined","part":"majority"' in document.text
    _, passages = build_opinion_passages(document.text)
    assessment = assess_opinion_boundaries(
        document.text, passages, require_explicit=True
    )
    assert assessment.ok
    assert assessment.part_counts == {"majority": 20, "dissent": 20}


def test_plurality_and_partial_concurrence_have_conservative_coarse_parts():
    document = assemble_sub_opinions("13", [
        part("025plurality", "Plurality text. " * 20, "8"),
        part("035concurrenceinpart", "Mixed separate writing. " * 20, "9"),
    ])
    assert document is not None
    assert '"part":"majority"' in document.text
    assert '"part":"dissent"' in document.text


def test_html_with_citations_is_preferred_and_keeps_blocks():
    text, source = extract_opinion_text({
        "plain_text": "Plain fallback. " * 20,
        "html_with_citations": "<p>First paragraph.</p><p>Second paragraph.</p>" * 10,
    })
    assert source == "html_with_citations"
    assert "First paragraph.\nSecond paragraph." in text


def test_canonical_document_round_trips_through_passage_preflight():
    document = assemble_sub_opinions("15", [
        part("020lead", "Majority sentence. " * 20, "12"),
        part("040dissent", "Dissent sentence. " * 20, "13"),
    ])
    assert document is not None
    _, passages = build_opinion_passages(document.text)
    assessment = assess_opinion_boundaries(document.text, passages)
    assert assessment.ok
    assert assessment.part_counts == {"majority": 20, "dissent": 20}


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class PartialClient:
    async def get(self, url, **kwargs):
        if "/clusters/16/" in url:
            return FakeResponse(200, {
                "sub_opinions": [
                    "https://www.courtlistener.com/api/rest/v4/opinions/20/",
                    "https://www.courtlistener.com/api/rest/v4/opinions/21/",
                ]
            })
        if "/opinions/20/" in url:
            return FakeResponse(200, {
                "id": 20, "type": "020lead", "plain_text": "Majority. " * 30,
            })
        if "/opinions/21/" in url:
            return FakeResponse(503, {})
        return FakeResponse(200, {"results": []})


def test_partial_sub_opinion_fetch_is_not_assembled_or_persistable():
    document = asyncio.run(fetch_courtlistener_document(
        "16", "token", client=PartialClient(),
    ))
    assert document is None


class TextlessPartClient(PartialClient):
    async def get(self, url, **kwargs):
        if "/opinions/21/" in url:
            return FakeResponse(200, {"id": 21, "type": "040dissent", "plain_text": ""})
        return await super().get(url, **kwargs)


def test_textless_expected_sub_opinion_is_not_treated_as_complete():
    document = asyncio.run(fetch_courtlistener_document(
        "16", "token", client=TextlessPartClient(),
    ))
    assert document is None


class FlakyOnceClient(PartialClient):
    """Opinion 21 fails on the first attempt only — a transient blip must not
    refuse the whole cluster."""

    def __init__(self):
        self.failed_once = False

    async def get(self, url, **kwargs):
        if "/opinions/21/" in url:
            if not self.failed_once:
                self.failed_once = True
                return FakeResponse(503, {})
            return FakeResponse(200, {
                "id": 21, "type": "040dissent", "plain_text": "Dissent. " * 30,
            })
        return await super().get(url, **kwargs)


def test_transient_sub_opinion_failure_is_retried_and_assembles():
    document = asyncio.run(fetch_courtlistener_document(
        "16", "token", client=FlakyOnceClient(),
    ))
    assert document is not None
    assert [value.type_code for value in document.parts] == ["020lead", "040dissent"]


class MissingClusterClient:
    async def get(self, url, **kwargs):
        if "/clusters/16/" in url:
            return FakeResponse(503, {})
        return FakeResponse(200, {"results": [
            {"id": 20, "type": "020lead", "plain_text": "Majority. " * 30}
        ]})


def test_cluster_manifest_is_required_for_complete_fetch():
    document = asyncio.run(fetch_courtlistener_document(
        "16", "token", client=MissingClusterClient(),
    ))
    assert document is None
