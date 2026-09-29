# Alert và runbook

Các alert đọc event trong `data/logs.jsonl`, chỉ tính khi mẫu số có dữ liệu và gửi tới Slack `#day13-alerts`.

## Alert 1

- Tên: `high_request_latency`; severity: warning; owner: `api-oncall`.
- Điều kiện: P95 `response_sent.latency_ms` > 3000 ms liên tục 5 phút. Liên quan SLO request thành công dưới 3000 ms.
- Ảnh hưởng: người dùng chờ câu trả lời lâu.
- Kiểm tra: (1) xác nhận P95 và khung thời gian trên dashboard; (2) lọc log `response_sent` chậm để lấy `correlation_id`; (3) mở trace cùng ID, so độ dài retrieval và generation.
- Mitigation: nếu retrieval chậm, giảm tải hoặc dùng fallback tài liệu; nếu generation chậm, giảm concurrency và kiểm tra model/TTFT. Khôi phục khi P95 dưới ngưỡng ổn định 5 phút.

## Alert 2

- Tên: `high_request_error_rate`; severity: critical; owner: `api-oncall`.
- Điều kiện: `request_failed / request_received` > 2% liên tục 5 phút. Request lỗi cũng tiêu thụ error budget SLO.
- Ảnh hưởng: người dùng không nhận được câu trả lời.
- Kiểm tra: (1) xác nhận tỷ lệ lỗi và loại lỗi; (2) lấy `correlation_id` từ log `request_failed`; (3) xem trace cùng ID để tìm span lỗi.
- Mitigation: rollback thay đổi gần nhất nếu lỗi bắt đầu sau deploy; nếu retrieval timeout, bật fallback và kiểm tra dịch vụ truy xuất. Khôi phục khi error rate dưới 2% ổn định 5 phút.

## Alert 3

- Tên: `low_retrieval_success`; severity: warning; owner: `rag-oncall`.
- Điều kiện: `tool_success=true / tool_success!=null` < 90% liên tục 10 phút. Dùng cả `response_sent` và `request_failed` để đếm thành công/thất bại.
- Ảnh hưởng: câu trả lời thiếu ngữ cảnh hoặc request thất bại.
- Kiểm tra: (1) xác nhận retrieval success và quality proxy; (2) lọc log theo `tool_name=retrieval` lấy request thất bại; (3) mở trace cùng `correlation_id` và xem retrieval span.
- Mitigation: dùng fallback tài liệu có sẵn và kiểm tra vector store/index. Khôi phục khi success rate trên 90% ổn định 10 phút.
