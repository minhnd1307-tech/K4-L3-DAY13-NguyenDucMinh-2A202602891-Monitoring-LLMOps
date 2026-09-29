# Trạng thái bàn giao Day 13

Cập nhật: 2026-09-29, sau khi hoàn thành CP3 và chuẩn bị nộp CP4.

## Đã làm

- CP0: chạy baseline thật. Kết quả lưu tại `submission/evidence/00-baseline.txt`.
- CP1: commit `8fd64ee` (`cp1`). Correlation ID, structured log và PII scrub hoàn thành; log validator đạt 100/100.
- CP2: commit `85bf336` (`cp2`). Có 26 pytest pass, dashboard validator 6/6, 17 root traces đã đối chiếu log trong project Langfuse cá nhân `day13-k4-l3a-2A202602891`.
- Prompt `day13-chat`: v1 `baseline`, v2 `candidate`; đã promote v2 lên `production`, gọi thử, rồi rollback `production` về v1. Chi tiết trace ID ở `submission/evidence/10-prompt-rollback.txt`.
- Ảnh Langfuse trong `submission/evidence/06-trace-list.png` đến `10b-rollback-v1.png`; ảnh dashboard tại `11-dashboard-overview.png`.
- CP3: Đã nhận file challenge L3A chính thức `day13-k4-l3a-monitoring-llmops-v1`, kịch bản `rag_slow`, seed 1311. Đã chạy incident injection, load test concurrency 5, ghi nhận triệu chứng metric P95 tăng vọt 3,752 ms. Trích xuất log correlation_id `req-f2cbbb3b`, đối chiếu trace ID `15b49cbdf4e66ada4b94803442d57add` trên Langfuse cá nhân và chứng minh span `retrieval` bị nghẽn 2.501s. Tắt incident thành công. Lưu toàn bộ evidence tại `12-incident-metric.txt`, `13-incident-log.txt`, `14-incident-trace.txt`.
- CP4: Đã hoàn thiện toàn diện báo cáo cá nhân `submission/REPORT.md`, cập nhật checklist, kiểm tra 26/26 pytest pass, log validator 100/100, dashboard validator 6/6.
- Đã cấu hình `.gitignore` chặn toàn bộ file challenge và secret/env.

## Hướng dẫn người dùng commit và nộp bài

Theo quy định bắt buộc, người dùng tự thực hiện các lệnh git:
1. Commit CP3:
   ```bash
   git add submission/evidence/12-incident-metric.txt submission/evidence/13-incident-log.txt submission/evidence/14-incident-trace.txt .gitignore
   git commit -m "cp3"
   ```
2. Commit CP4:
   ```bash
   git add submission/REPORT.md submission/evidence/01-pytest.txt submission/evidence/02-log-validator.txt submission/evidence/03-dashboard-validator.txt docs/WORK_STATUS.md
   git commit -m "cp4"
   ```
3. Lấy commit SHA cuối cùng: `git rev-parse HEAD`
4. Cập nhật commit SHA vào mục 1 của `submission/REPORT.md` (nếu cần), rồi amend hoặc commit.
5. Push lên GitHub: `git push origin main`
6. Nộp URL repo và commit SHA lên hệ thống LMS/Codelabs.
