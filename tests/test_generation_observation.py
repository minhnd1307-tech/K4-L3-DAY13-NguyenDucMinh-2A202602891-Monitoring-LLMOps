from app import mock_llm


def test_generation_records_sanitized_prompt_usage_and_cost(monkeypatch) -> None:
    updates = []

    class Client:
        def update_current_generation(self, **kwargs):
            updates.append(kwargs)

    monkeypatch.setattr(mock_llm, "get_langfuse_client", lambda: Client())
    monkeypatch.setattr(mock_llm.time, "sleep", lambda _: None)
    response = mock_llm.FakeLLM.generate.__wrapped__(
        mock_llm.FakeLLM(), "Question=student@vinuni.edu.vn"
    )
    observation = updates[0]
    assert "student@vinuni.edu.vn" not in observation["input"]
    assert "[REDACTED_EMAIL]" in observation["input"]
    assert observation["model"] == response.model
    assert observation["usage_details"] == {
        "input": response.usage.input_tokens,
        "output": response.usage.output_tokens,
    }
    assert round(sum(observation["cost_details"].values()), 6) == response.cost_usd
