from pathlib import Path

from scripts.import_canonical_outline import build_section, load_outline, outline_content_hash, section_slug
from scripts.privatize_outline_uploads import supabase_storage_path


CONTENT = Path(__file__).resolve().parents[1] / "frontend" / "content" / "outlines" / "civil-procedure.json"


def test_civil_procedure_outline_has_stable_unique_sections():
    outline = load_outline(CONTENT)

    assert outline["slug"] == "civil-procedure"
    assert len(outline["sections"]) == 15
    assert len({section_slug(section["title"]) for section in outline["sections"]}) == 15
    # Doctrine sections lead the outline but are excluded from the /civpro timeline.
    doctrine_titles = [s["title"] for s in outline["sections"] if s.get("kind") == "doctrine"]
    assert doctrine_titles == [
        "Subject Matter Jurisdiction",
        "Personal Jurisdiction",
        "Venue, Transfer & Forum Non Conveniens",
        "The Erie Doctrine",
    ]
    # Process-stage ids 1-11 predate the doctrine sections; their section_keys
    # anchor live votes/comments and must never be renumbered.
    stage_ids = {s["id"] for s in outline["sections"] if s.get("kind") != "doctrine"}
    assert stage_ids == set(range(1, 12))


def test_section_renderer_links_rules_and_cases_as_sources():
    outline = load_outline(CONTENT)
    pleadings = next(s for s in outline["sections"] if s["title"] == "Pleadings & Motions")
    body, sources = build_section(pleadings)

    assert "[Rule 8(a)](/rules/rule-8)" in body
    assert "[Bell Atlantic Corp. v. Twombly (2007)](/case/145730)" in body
    assert {source["target_type"] for source in sources} >= {"rule", "case"}


def test_doctrine_sections_link_their_case_canon():
    outline = load_outline(CONTENT)
    erie = next(s for s in outline["sections"] if s["title"] == "The Erie Doctrine")
    body, sources = build_section(erie)

    assert "[Erie Railroad Co. v. Tompkins (1938)](/case/103012)" in body
    assert "[Hanna v. Plumer (1965)](/case/107024)" in body
    case_refs = {s["target_ref"] for s in sources if s["target_type"] == "case"}
    assert {"103012", "107024", "104182", "105689"} <= case_refs


def test_content_hash_changes_when_revision_content_changes():
    outline = load_outline(CONTENT)
    original_hash = outline_content_hash(outline)
    outline["sections"][0]["subtitle"] = "Changed"

    assert outline_content_hash(outline) != original_hash


def test_supabase_storage_path_extracts_public_outline_object():
    assert supabase_storage_path(
        "https://example.supabase.co/storage/v1/object/public/outlines/user%2Foutline.pdf"
    ) == "user/outline.pdf"
    assert supabase_storage_path("https://example.com/outline.pdf") is None
