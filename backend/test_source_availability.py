import json

import main


def test_docket_only_source_explains_pending_recap_request():
    detail = main.unavailable_opinion_detail({
        "source_text_status": "verified_docket_entry_only",
        "full_order_available": False,
        "document_number": 93,
        "recap_prayer_id": 53250,
    })

    assert detail == (
        "The full order for Filing 93 is not available from CourtListener yet, "
        "so Tortwell cannot generate a source-linked AI brief. "
        "Tortwell has requested the document through RECAP."
    )


def test_available_or_unrelated_source_is_not_blocked():
    assert main.unavailable_opinion_detail({"full_order_available": True}) is None
    assert main.unavailable_opinion_detail(json.dumps({
        "source_text_status": "courtlistener_opinion",
        "full_order_available": False,
    })) is None
