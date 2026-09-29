# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Đức Minh
- **MSSV:** 2A202602891
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/minhnd1307-tech/K4-L3-DAY13-NguyenDucMinh-2A202602891-Monitoring-LLMOps
- **Commit SHA cuối:** 06846e6f815c04cd9b2d88457601853bc7c09ee8
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602891`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png` / `evidence/06-trace-list.txt` |
| Trace waterfall | `evidence/07-trace-waterfall.png` / `evidence/07-trace-waterfall.txt` |
| Trace metadata | `evidence/08-trace-metadata.png` / `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.png` / `evidence/09-prompt-versions.txt` |
| Prompt rollback | `evidence/10-prompt-rollback.txt` / `evidence/10a-production-v2.png` / `evidence/10b-rollback-v1.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.txt` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đầy đủ trường JSON schema, lan truyền correlation ID, enrich contextvars và scrub 100% PII |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel | HỢP LỆ: 6/6 panel | Đủ 6/6 panel theo contract với đầy đủ aggregations, threshold, unit |
| `pytest` | 22 passed | 26 passed | Pass toàn bộ test suite bao gồm test PII, tracing adapter, observation API và dashboard runtime |
| Số traces hợp lệ | 0 (chưa config key) | 22 traces | Đều được tạo trong project Langfuse cá nhân `day13-k4-l3a-2A202602891`, khớp correlation_id với log |
| Số PII leak | 0 | 0 | Không có rò rỉ email, số điện thoại VN, CCCD hay thẻ ngân hàng trong log và trace |
| Latency P95 / TTFT P95 | 234 ms / 50 ms (bình thường) | 3,752 ms / 50 ms (trong incident) | P95 phản ánh chính xác độ trễ tăng vọt do span retrieval bị nghẽn 2.5s trong incident rag_slow |
| Retrieval success rate | 100% | 100% | 100% request retrieval trả về document, tool_success=True ghi nhận đầy đủ |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - Trong `CorrelationIdMiddleware` (`app/middleware.py`), middleware đọc header `x-request-id` từ request đến; nếu không có hoặc không đúng định dạng `^req-[0-9a-fA-F]{8}$`, hàm sẽ sinh mới theo format chuẩn `req-{uuid4().hex[:8]}`.
  - Context cũ của structlog được làm sạch bằng `clear_contextvars()`, sau đó bind `correlation_id` vào request context và gán vào `request.state.correlation_id`.
  - Header `x-request-id` luôn được gán ngược lại vào HTTP response header để client đối soát.
- **Các metadata được ghi vào structured log:**
  - Metadata được bind qua `structlog.contextvars.bind_contextvars`: `user_id_hash` (băm sha256 12-hex), `session_id`, `feature`, `model`, `env`.
  - Mỗi log event dạng JSON (`request_received`, `response_sent`, `request_failed`, `incident_enabled`, `incident_disabled`) có `ts` ISO-8601 UTC, `service`, `event`, `level`, `correlation_id` cùng các số liệu runtime: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  - PII processor `pii_scrub_processor` được đăng ký trong cấu hình structlog (`app/logging_config.py`) nằm **trước** processor render JSON (`structlog.processors.JSONRenderer`).
  - Hàm `scrub_pii_value` đệ quy qua toàn bộ dict/list/string trong log record, dùng regex để thay thế email (`[REDACTED_EMAIL]`), số điện thoại Việt Nam (`[REDACTED_PHONE_VN]`), số CCCD 12 số (`[REDACTED_CCCD]`), số thẻ tín dụng 16 số (`[REDACTED_CREDIT_CARD]`).
  - `user_id` thật không bao giờ ghi thô ra log mà luôn chuyển thành `user_id_hash`. Nội dung tin nhắn người dùng được rút gọn an toàn bằng `summarize_text`.
- **Cách kiểm chứng kết quả:**
  - Chạy `python scripts/validate_logs.py` đạt điểm tuyệt đối 100/100, 0 PII leak detected trên toàn bộ 85 log records.
  - Bộ kiểm thử `tests/test_pii.py` và `tests/test_chat_observability.py` pass 100%.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  - Mọi trace đều nằm trong project riêng `day13-k4-l3a-2A202602891` trên Langfuse Cloud, kết nối qua cặp key cá nhân `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` trong `.env`.
  - Không dùng chung project hay key của người khác. Mỗi trace có tag chứa model, tên lab và user_id_hash tương ứng.
- **Cấu trúc root/retrieval/generation observations:**
  - Tách bạch cấu trúc cha-con chuẩn mực theo Langfuse Python SDK v4:
    - Root observation: `AGENT lab-agent-run` (do `@observe(name="lab-agent-run", as_type="agent")` bọc `LabAgent.run`).
    - Retrieval child observation: `RETRIEVER retrieval` (do `@observe(name="retrieval", as_type="retriever")` trong `app/mock_rag.py`).
    - Generation child observation: `GENERATION fake-llm` (do `@observe(name="fake-llm", as_type="generation")` trong `app/mock_llm.py`).
  - Generation observation ghi nhận `model`, `usage` (`input`, `output`, `total` tokens) và `cost` tính theo bảng giá USD chuẩn.
- **Cách nối trace với log:**
  - Dùng `correlation_id` (ví dụ `req-f2cbbb3b`) làm khóa liên kết đồng nhất giữa trường `correlation_id` trong structured log `data/logs.jsonl` và trường `metadata.correlation_id` trong trace Langfuse.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, label `baseline`
- **Version/label candidate:** Version 2, label `candidate`
- **Trace ID của mỗi version:**
  - Trace ID với Prompt v1 (`baseline`): `406c5e868ffd9c4939609f9c33d044ac` (correlation_id: `req-7f4c5efa`)
  - Trace ID với Prompt v2 (`candidate`): `c41d0f40cf2f1b7752ac71519472db43` (correlation_id: `req-9c347a60`)
  - Trace ID sau khi promote v2 lên `production`: `83a39520b685dcabf2450a2ad1c412c4` (correlation_id: `req-631b7905`)
  - Trace ID sau khi rollback `production` về v1: `a9a552a8c8b23b2e3a3d0f207e0ef97c` (correlation_id: `req-d979b848`)
- **Cách promote và rollback `production`:**
  - Tiến hành trên giao diện Langfuse Prompt Management: ban đầu gán label `production` cho v1.
  - Khi thử nghiệm bản mới, promote v2 bằng cách thêm label `production` vào v2 (Langfuse tự động chuyển nhãn `production` sang v2).
  - Khi cần rollback, gán lại label `production` cho v1; app ngay lập tức fetch về v1 với `prompt_version=1` mà không cần restart server hay deploy lại code.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  - Được cấu hình tại `config/dashboard.yaml` và trực quan hóa qua server `scripts/dashboard.py` (port 8001):
    1. `latency`: P50, P95, P99 và TTFT P95 (threshold P95 <= 3,000 ms).
    2. `traffic`: Request traffic rate_per_minute (threshold >= 1 req/min).
    3. `errors`: Error rate (%) và Retrieval success rate (%) (threshold error_rate <= 2%).
    4. `cost`: Tổng chi phí USD và chi phí cao nhất mỗi phút (threshold <= $2.5).
    5. `tokens`: Tổng input và output tokens (threshold <= 50,000 tokens).
    6. `quality`: Điểm chất lượng trung bình chất lượng heuristic (threshold mean >= 0.75).
- **SLO và lý do chọn:**
  - Primary SLO (`config/slo.yaml`): `fast_successful_requests` với target 99.5% trong chu kỳ 28 ngày.
  - Định nghĩa SLI: `good_event` là `event == "response_sent" and latency_ms <= 3000` trên tổng số `total_event` là `event == "request_received"`.
  - Lý do: Với hệ thống AI Assistant tương tác trực tiếp với người dùng, độ trễ trên 3 giây gây suy giảm trải nghiệm nghiêm trọng tương đương với lỗi. Ngưỡng 99.5% đảm bảo tính sẵn sàng cao và giữ chân người dùng.
- **Cách tính error budget:**
  - Error budget = 100% - Target SLO = 100% - 99.5% = 0.5%.
  - Tức là trong mỗi 10,000 requests, hệ thống cho phép tối đa 50 requests bị lỗi hoặc có latency vượt quá 3,000 ms.
- **Ba alert và runbook tương ứng:**
  - Cấu hình trong `config/alert_rules.yaml` và runbook tại `docs/alerts.md`:
    1. `high_request_latency` (warning, owner `api-oncall`): P95 latency > 3000 ms liên tục trong 5 phút. Runbook: Kiểm tra P95 trên dashboard, lọc correlation_id chậm, đối chiếu trace xem bottleneck tại retrieval hay LLM generation để kích hoạt cache/fallback.
    2. `high_request_error_rate` (critical, owner `api-oncall`): Tỷ lệ request_failed/request_received > 2% liên tục trong 5 phút. Runbook: Xác định loại lỗi, trích xuất correlation_id, đối chiếu span lỗi; nếu do phiên bản mới thì rollback ngay, nếu do vector store timeout thì kích hoạt circuit breaker.
    3. `low_retrieval_success` (warning, owner `rag-oncall`): Tỷ lệ tool_success < 90% liên tục trong 10 phút. Runbook: Kiểm tra chất lượng retrieval, kiểm tra kết nối vector store và khôi phục fallback corpus.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** `2026-09-29 08:58:54 UTC` đến `2026-09-29 08:59:46 UTC`
- **Triệu chứng từ metrics:**
  - P95 latency của API nhảy vọt từ mức bình thường (~234 ms) lên **3,752 ms**, vi phạm ngưỡng cảnh báo 3,000 ms của alert `high_request_latency` và tiêu tốn error budget của SLO.
  - Load test với 5 concurrent queries ghi nhận thời gian phản hồi kéo dài từ 4.05s đến 14.67s.
  - Error rate vẫn ở mức 0% (các request đều trả về mã HTTP 200).
- **Log line và correlation ID liên quan:**
  - Log kích hoạt incident: `{"service": "control", "payload": {"name": "rag_slow"}, "event": "incident_enabled", "correlation_id": "req-7a17f076", "ts": "2026-09-29T08:58:54.828176Z"}`
  - Log request tiêu biểu bị ảnh hưởng: Correlation ID `req-f2cbbb3b`
    - Request received: `{"service": "api", "payload": {"message_preview": "Which signal should be checked after latency increases?"}, "event": "request_received", "correlation_id": "req-f2cbbb3b", "feature": "monitoring", "session_id": "k4-l3a-challenge-s04", "ts": "2026-09-29T08:59:19.138554Z"}`
    - Response sent: `{"service": "api", "latency_ms": 3752, "ttft_ms": 50, "tokens_in": 36, "tokens_out": 135, "cost_usd": 0.002133, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "event": "response_sent", "correlation_id": "req-f2cbbb3b", "feature": "monitoring", "ts": "2026-09-29T08:59:23.172926Z"}`
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID cùng correlation_id `req-f2cbbb3b`: `15b49cbdf4e66ada4b94803442d57add`
  - Cấu trúc waterfall phân rã thời gian:
    - Root span `AGENT lab-agent-run`: tổng thời gian `3.752s`
    - Child span `RETRIEVER retrieval`: chiếm **2.501s** (chiếm ~67% tổng thời gian request)
    - Child span `GENERATION fake-llm`: chỉ mất `0.152s`
  - Kết luận: Span gây nghẽn trực tiếp là span `retrieval`.
- **Root cause:**
  - Thành phần Retrieval (RAG pipeline) bị nghẽn (do kịch bản `rag_slow` inject độ trễ cố định 2.5s vào hàm `retrieve()` trong `app/mock_rag.py`), khiến thời gian truy xuất tài liệu tăng đột biến và kéo theo toàn bộ thời gian phản hồi của request vượt quá ngưỡng latency SLO.
- **Fix action:**
  - Tắt kịch bản incident bằng lệnh `POST /incidents/rag_slow/disable` (thực hiện qua `python scripts/inject_incident.py --disable`).
  - Trong môi trường sản xuất thực tế: Thêm timeout cho lời gọi retrieval (ví dụ 1.5s), nếu vượt quá timeout thì fallback ngay sang câu trả lời tổng quát dựa trên pre-cached corpus thay vì chờ nghẽn luồng.
- **Preventive measure:**
  - Thiết lập cơ chế cache truy vấn (semantic caching/Redis) cho các câu hỏi phổ biến thuộc feature `monitoring` để giảm tải cho vector database.
  - Bổ sung circuit breaker cho RAG service: tự động chuyển sang degraded mode khi phát hiện latency trung bình của vector store vượt quá 1,000 ms.
  - Cấu hình auto-scaling cho cụm dịch vụ Vector Search / Embeddings.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Lựa chọn đặt PII Scrubbing Processor ở vị trí ngay trước JSONRenderer trong pipeline của structlog. Lý do: Đảm bảo dữ liệu nhạy cảm được che giấu triệt để ở tất cả các cấp độ log (cả message lẫn contextvars) trước khi bị ghi xuống file vật lý `data/logs.jsonl`, ngăn chặn hoàn toàn nguy cơ rò rỉ dữ liệu nhạy cảm ra ổ đĩa hoặc hệ thống lưu trữ log tập trung.
- **Một lỗi/blocker đã gặp:**
  - Khi gọi API Langfuse SDK v4 để truy vấn danh sách trace/observation phục vụ trích xuất evidence, endpoint cũ `client.api.trace.list` trả về lỗi HTTP 410 (do Langfuse Cloud khóa legacy API với các tổ chức tạo sau tháng 9/2026).
- **Cách tìm nguyên nhân và xử lý:**
  - Đọc kỹ thông báo lỗi và tài liệu di trú của Langfuse v4, phát hiện Langfuse v4 đã chuyển toàn bộ việc đọc span/trace sang endpoint `client.api.observations.get_many(trace_id=...)`. Đã điều chỉnh code truy vấn theo chuẩn mới của v4 để lấy chính xác toàn bộ cây observation.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics** là lớp cảnh báo đầu tiên (màn hình radar): cho biết *hệ thống có đang gặp vấn đề không* và *ở thời điểm nào* (thấy P95 vượt ngưỡng).
  - **Logs** là lớp thu hẹp phạm vi: từ khoảng thời gian của metric, lọc log tìm các request bất thường và lấy ra `correlation_id` cụ thể của request đó.
  - **Traces** là lớp giải phẫu chi tiết: dùng `correlation_id` mở cây waterfall trace trên Langfuse để khoanh vùng chính xác *span nào, function nào trong chuỗi xử lý* đã tiêu tốn thời gian hoặc ném ra exception.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Prompt Versioning cho phép quản lý vòng đời prompt tương tự như mã nguồn phần mềm, tách biệt prompt khỏi chu kỳ release code.
  - Token & Cost Tracking giúp phát hiện sớm các hiện tượng prompt injection gây bùng nổ token hoặc model hallucination gây tràn chi phí.
  - SLO và Error Budget cung cấp ranh giới định lượng giữa tốc độ đổi mới tính năng và độ ổn định của hệ thống.
  - Rollback tức thì (qua nhãn `production`) cho phép khôi phục phiên bản an toàn trong vài giây khi phiên bản mới gặp lỗi chất lượng hoặc độ trễ mà không cần chờ quy trình CI/CD.
- **Điều quan trọng nhất đã học:**
  - Hiểu sâu sắc và thực hành trọn vẹn kiến trúc Observability hiện đại cho ứng dụng AI (LLMOps) từ lý thuyết đến triển khai thực tế: từ Structured Logging, Context Propagation, PII Redaction, Distributed Tracing với Langfuse đến Dashboarding, SLO và Incident Response.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  - Hệ thống hiện sử dụng Mock LLM và Mock Vector Store; trong tương lai có thể mở rộng tích hợp với LLM API thật và dịch vụ Vector Database phân tán (như Qdrant/Pinecone) kèm OpenTelemetry exporter hoàn chỉnh.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
