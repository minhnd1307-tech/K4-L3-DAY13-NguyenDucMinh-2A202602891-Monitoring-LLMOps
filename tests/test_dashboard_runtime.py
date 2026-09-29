from scripts.dashboard import panel_values, percentile


def test_dashboard_uses_success_and_failure_events() -> None:
    rows = [
        {"event": "request_received"},
        {"event": "request_received"},
        {"event": "response_sent", "ts": "2026-09-29T07:00:00Z", "latency_ms": 100, "ttft_ms": 40, "cost_usd": 0.01, "tokens_in": 10, "tokens_out": 20, "quality_score": 0.8, "tool_success": True},
        {"event": "request_failed", "tool_success": False},
    ]
    values = panel_values(rows)
    assert values["errors"] == ("50.0%", "1 errors / 2 requests<br>Retrieval success 50.0% (1/2)", 50.0)
    assert values["tokens"][0] == "30"
    assert values["latency"][0] == "100 ms"
    assert percentile([100, 200], 50) == 150
