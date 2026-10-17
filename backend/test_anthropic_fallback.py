import main


def test_opus_5_5_requests_opt_into_default_fallback_and_effort():
    body = main.anthropic_body("claude-opus-5-5", 16000, [], "high")
    assert body["fallbacks"] == "default"
    assert body["output_config"] == {"effort": "high"}
    assert main.anthropic_headers("k", "claude-opus-5-5")["anthropic-beta"] == main.FALLBACK_BETA
    assert "fallbacks" not in main.anthropic_body("claude-sonnet-4-6", 100, [])
    assert "anthropic-beta" not in main.anthropic_headers("k", "claude-sonnet-4-6")


def test_reservations_price_the_costliest_fallback_target():
    assert main.anthropic_reservation_model("claude-opus-5-5") == "claude-opus-4-8"
    assert main.anthropic_reservation_model("claude-sonnet-4-6") == "claude-sonnet-4-6"


def test_usage_prices_served_model_without_fallback():
    result = {"model": "claude-opus-5-5", "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}
    assert main.anthropic_result_usage(result, "claude-opus-5-5") == (1_000_000, 0, 4.0)


def test_usage_sums_every_attempt_after_a_fallback():
    result = {"model": "claude-opus-4-8", "usage": {
        "input_tokens": 10, "output_tokens": 10,
        "iterations": [
            {"type": "message", "input_tokens": 500_000, "output_tokens": 0},
            {"type": "fallback_message", "input_tokens": 500_000, "output_tokens": 0},
        ]}}
    assert main.anthropic_result_usage(result, "claude-opus-5-5") == (1_000_000, 0, 5.0)


def test_refusal_has_no_text_and_thinking_blocks_are_skipped():
    assert main.anthropic_result_text({"stop_reason": "refusal", "content": [{"type": "text", "text": "x"}]}) is None
    result = {"stop_reason": "end_turn",
              "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "{}"}]}
    assert main.anthropic_result_text(result) == "{}"
