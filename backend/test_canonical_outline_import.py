from pathlib import Path

from scripts.import_canonical_outline import build_section, load_outline, outline_content_hash, section_slug
from scripts.privatize_outline_uploads import supabase_storage_path


CONTENT = Path(__file__).resolve().parents[1] / "frontend" / "content" / "outlines" / "civil-procedure.json"


def test_civil_procedure_outline_has_stable_unique_sections():
    outline = load_outline(CONTENT)

    assert outline["slug"] == "civil-procedure"
    assert len(outline["sections"]) == 11
    assert len({section_slug(section["title"]) for section in outline["sections"]}) == 11


def test_section_renderer_links_rules_and_cases_as_sources():
    outline = load_outline(CONTENT)
    pleadings = outline["sections"][2]
    body, sources = build_section(pleadings)

    assert "[Rule 8(a)](/rules/rule-8)" in body
    assert "[Bell Atlantic Corp. v. Twombly (2007)](/case/145730)" in body
    assert {source["target_type"] for source in sources} >= {"rule", "case"}


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
