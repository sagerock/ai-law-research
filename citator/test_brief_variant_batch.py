import json

import pytest

import brief_variant_batch as batch
from test_brief_variants import detailed_brief, valid_candidate


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "STAGING", tmp_path / "staging")
    monkeypatch.setattr(batch, "approved_brief", lambda case_id: ("Dean Milk", "claude", detailed_brief()))
    published = []

    def fake_run(snippet, payload=None, timeout=180):
        if snippet is batch.PUBLISH_SNIPPET:
            published.append(payload)
            return {"ok": True}
        return [{"id": "104847", "title": "Dean Milk", "state": "missing"},
                {"id": "111715", "title": "Maine v. Taylor", "state": "stale"}]

    monkeypatch.setattr(batch.railway_db, "run", fake_run)

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return str(path)

    return write, published


def test_stage_rejects_invalid_candidate_without_staging(env):
    write, _ = env
    candidate = valid_candidate()
    candidate["simplified"]["holding"][0]["from"] = ["holding[0]"]  # drops the remand
    result = batch.cmd_stage("104847", write("c.json", candidate), "claude-sonnet-4-6")
    assert result["ok"] is False
    assert "simplified.holding drops detailed claims: holding[1]" in result["errors"]
    assert batch.load_staged("104847") is None


def test_approve_publishes_with_subscription_label(env):
    write, published = env
    assert batch.cmd_stage("104847", write("c.json", valid_candidate()), "claude-sonnet-4-6")["ok"]
    assert [item["id"] for item in batch.cmd_review_list(5)] == ["104847"]
    result = batch.cmd_review_save("104847", write("v.json", {"verdict": "approve", "problems": []}))
    assert result == {"ok": True, "status": "published"}
    (payload,) = published
    assert payload["model"] == "claude-sonnet-4-6 (subscription)"
    assert payload["digest"] == batch.source_digest(detailed_brief())
    assert batch.load_staged("104847")["status"] == "published"


def test_minor_problems_do_not_block_approval(env):
    write, published = env
    batch.cmd_stage("104847", write("c.json", valid_candidate()), "m")
    verdict = {"verdict": "approve", "problems": [{"line": "x", "severity": "minor", "problem": "loose"}]}
    assert batch.cmd_review_save("104847", write("v.json", verdict))["ok"]
    assert len(published) == 1


def test_hold_routes_to_repair_and_second_hold_needs_a_human(env):
    write, published = env
    hold = {"verdict": "hold", "problems": [{"line": "simplified.dissent[0]", "severity": "wrong",
                                             "problem": "says the opposite"}]}
    batch.cmd_stage("104847", write("c.json", valid_candidate()), "m")
    assert batch.cmd_review_save("104847", write("v.json", hold))["status"] == "held"

    queue = batch.cmd_queue(5, None)
    assert queue[0] == {"id": "104847", "title": "Dean Milk", "state": "repair",
                        "notes": ["simplified.dissent[0]: says the opposite"]}
    assert [item["id"] for item in queue[1:]] == ["111715"]  # held case not duplicated
    assert batch.cmd_fetch("104847")["repair"]["reviewer_notes"] == ["simplified.dissent[0]: says the opposite"]

    batch.cmd_stage("104847", write("c2.json", valid_candidate()), "m")
    assert batch.cmd_review_save("104847", write("v2.json", hold))["status"] == "needs-human"
    assert batch.cmd_stage("104847", write("c3.json", valid_candidate()), "m")["ok"] is False
    assert published == []


def test_verdicts_must_be_consistent(env):
    write, _ = env
    batch.cmd_stage("104847", write("c.json", valid_candidate()), "m")
    wrong = [{"line": "x", "severity": "wrong", "problem": "p"}]
    assert not batch.cmd_review_save("104847", write("a.json", {"verdict": "approve", "problems": wrong}))["ok"]
    assert not batch.cmd_review_save("104847", write("h.json", {"verdict": "hold", "problems": []}))["ok"]
    assert batch.load_staged("104847")["status"] == "pending"


def test_review_fetch_refuses_stale_candidate(env, monkeypatch):
    write, _ = env
    batch.cmd_stage("104847", write("c.json", valid_candidate()), "m")
    changed = detailed_brief()
    changed["holding"][1]["text"] = "Regenerated."
    monkeypatch.setattr(batch, "approved_brief", lambda case_id: ("Dean Milk", "claude", changed))
    assert "stale" in batch.cmd_review_fetch("104847")["error"]
