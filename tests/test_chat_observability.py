from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True


def test_request_id_is_returned_and_context_does_not_leak(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_requests() -> list[httpx.Response]:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return [
                await client.post("/chat", headers={"x-request-id": request_id}, json={
                    "user_id": user_id, "session_id": "s1", "feature": "qa", "message": "Explain monitoring"
                })
                for request_id, user_id in (("req-abcdef12", "first"), ("invalid", "second"))
            ]

    responses = asyncio.run(send_requests())
    assert responses[0].headers["x-request-id"] == "req-abcdef12"
    assert responses[1].headers["x-request-id"].startswith("req-")
    assert len(responses[1].headers["x-request-id"]) == 12
    assert all(float(response.headers["x-response-time-ms"]) >= 0 for response in responses)
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    received = [event for event in events if event["event"] == "request_received"]
    assert [event["correlation_id"] for event in received] == [response.headers["x-request-id"] for response in responses]
    assert received[0]["user_id_hash"] != received[1]["user_id_hash"]
    assert all(event["model"] and event["env"] and event["feature"] for event in received)
