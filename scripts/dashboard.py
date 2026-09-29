"""Live six-panel dashboard backed by data/logs.jsonl (http://127.0.0.1:8001)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config/dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
LOG_PATH = ROOT / "data/logs.jsonl"


def percentile(values: list[float], percent: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent / 100
    low = int(index)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (index - low)


def read_logs(now: datetime) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    # ponytail: full scan is fine for a lab log; use indexed storage if it grows large.
    start = now - timedelta(minutes=CONFIG["time_range_minutes"])
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            timestamp = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
            if start <= timestamp <= now:
                rows.append(row)
        except (ValueError, KeyError, TypeError):
            continue
    return rows


def panel_values(rows: list[dict]) -> dict[str, tuple[str, str, float]]:
    received = [r for r in rows if r.get("event") == "request_received"]
    sent = [r for r in rows if r.get("event") == "response_sent"]
    failed = [r for r in rows if r.get("event") == "request_failed"]
    latency = [r["latency_ms"] for r in sent if isinstance(r.get("latency_ms"), (int, float))]
    ttft = [r["ttft_ms"] for r in sent if isinstance(r.get("ttft_ms"), (int, float))]
    tool = [r["tool_success"] for r in sent + failed if isinstance(r.get("tool_success"), bool)]
    costs = [r.get("cost_usd", 0) for r in sent]
    minute_cost = Counter()
    for row in sent:
        minute_cost[row["ts"][:16]] += row.get("cost_usd", 0)
    quality = [r["quality_score"] for r in sent if isinstance(r.get("quality_score"), (int, float))]
    error_rate = len(failed) / len(received) * 100 if received else 0
    retrieval_rate = sum(tool) / len(tool) * 100 if tool else 0
    input_tokens = sum(r.get("tokens_in", 0) for r in sent)
    output_tokens = sum(r.get("tokens_out", 0) for r in sent)
    quality_mean = sum(quality) / len(quality) if quality else 0
    return {
        "latency": (f"{percentile(latency, 95):.0f} ms", f"P50 {percentile(latency, 50):.0f} · P95 {percentile(latency, 95):.0f} · P99 {percentile(latency, 99):.0f} ms<br>TTFT P95 {percentile(ttft, 95):.0f} ms", percentile(latency, 95)),
        "traffic": (f"{len(received) / CONFIG['time_range_minutes']:.2f} req/min", f"{len(received)} requests in {CONFIG['time_range_minutes']} min", len(received) / CONFIG["time_range_minutes"]),
        "errors": (f"{error_rate:.1f}%", f"{len(failed)} errors / {len(received)} requests<br>Retrieval success {retrieval_rate:.1f}% ({sum(tool)}/{len(tool)})", error_rate),
        "cost": (f"${sum(costs):.4f}", f"Total USD · peak ${max(minute_cost.values(), default=0):.4f}/min", sum(costs)),
        "tokens": (f"{input_tokens + output_tokens:,}", f"Input {input_tokens:,} · output {output_tokens:,} tokens", max(input_tokens, output_tokens)),
        "quality": (f"{quality_mean:.2f}", f"Mean quality proxy from {len(quality)} responses", quality_mean),
    }


def render(now: datetime) -> str:
    rows = read_logs(now)
    values = panel_values(rows)
    cards = []
    for panel in CONFIG["panels"]:
        value, detail, actual = values[panel["id"]]
        threshold = panel["threshold"]
        target = f"{threshold['aggregation']} {threshold['operator']} {threshold['value']} {panel['unit']}"
        scale = max(threshold["value"] * 1.25, actual * 1.1, 0.001)
        actual_width = min(100, actual / scale * 100)
        target_left = min(100, threshold["value"] / scale * 100)
        cards.append(f'<section><h2>{escape(panel["title"])}</h2><strong>{escape(value)}</strong><p>{detail}</p><div class="gauge" style="--actual:{actual_width:.1f}%;--target:{target_left:.1f}%"><span></span><b></b></div><small>Threshold / SLO line: {escape(target)}</small></section>')
    start = now - timedelta(minutes=CONFIG["time_range_minutes"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="{CONFIG['refresh_seconds']}"><title>Day 13 monitoring dashboard</title>
<style>body{{margin:0;padding:28px;background:#101827;color:#eaf2ff;font:16px system-ui}}header{{margin-bottom:24px}}h1{{margin:0;font-size:28px}}header p{{color:#a6b8d0}}main{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}section{{background:#1a2940;border:1px solid #36506f;border-radius:14px;padding:22px;min-height:190px}}h2{{font-size:18px;margin:0 0 20px;color:#b9cee8}}strong{{font-size:36px;color:#7ee2c0}}p{{line-height:1.5;min-height:46px}}small{{color:#a6b8d0}}.gauge{{position:relative;height:12px;background:#31435d;border-radius:8px;margin:14px 0}}.gauge span{{display:block;width:var(--actual);height:100%;background:#7ee2c0;border-radius:8px}}.gauge b{{position:absolute;left:var(--target);top:-5px;height:22px;border-left:3px dashed #efb45f}}footer{{margin-top:22px;color:#a6b8d0}}</style>
<body><header><h1>{escape(CONFIG['title'])}</h1><p>Time range: {start:%Y-%m-%d %H:%M}–{now:%H:%M} UTC · Refresh: {CONFIG['refresh_seconds']}s · Source: data/logs.jsonl · {len(rows)} events</p></header><main>{''.join(cards)}</main><footer>Metrics → Logs → Traces · Generated from live structured logs</footer></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = render(datetime.now(timezone.utc)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("Dashboard: http://127.0.0.1:8001")
    HTTPServer(("127.0.0.1", 8001), Handler).serve_forever()
