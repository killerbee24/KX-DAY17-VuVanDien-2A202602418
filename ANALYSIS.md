# Phân tích kết quả Lab Day 17

Kết quả dưới đây được tạo ngày 03/10/2026 bằng offline mode có tính xác định. Offline mode giúp test và benchmark có thể chạy lại mà không phụ thuộc API key, mạng hoặc biến động đầu ra của LLM.

## Kết quả benchmark

### Standard Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 1,098 | 14,669 | 0.000 | 0.200 | 0 | 0 |
| Advanced | 1,538 | 22,912 | 1.000 | 1.000 | 285 | 0 |

### Long-Context Stress Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 264 | 22,413 | 0.000 | 0.200 | 0 | 0 |
| Advanced | 460 | 14,685 | 1.000 | 1.000 | 235 | 4 |

## Nhận xét

### Vì sao Advanced recall tốt hơn?

Baseline lưu message theo `thread_id`. Recall question sử dụng thread mới nên Baseline không có lịch sử để trả lời. Advanced lưu các fact ổn định theo `user_id` trong `User.md`; do đó tên, nghề nghiệp, nơi ở, sở thích và style vẫn tồn tại khi thread thay đổi.

Advanced đạt recall `1.000` trên cả hai bộ dữ liệu. Extractor cũng xử lý đúng các correction `Đà Nẵng → Huế`, `backend engineer → MLOps engineer`, `Huế → Đà Nẵng` trong stress test, đồng thời bỏ qua `Hà Nội` là nơi đi họp và `product manager` là câu đùa.

### Vì sao Advanced tốn hơn trong hội thoại ngắn?

Ở Standard Benchmark, Advanced xử lý 22,912 prompt tokens so với 14,669 của Baseline, cao hơn khoảng 56.2%. Nguyên nhân là mỗi lượt Advanced phải mang thêm `User.md` và metadata memory. Các thread standard tương đối ngắn nên chưa kích hoạt compact; overhead của persistent memory chưa được bù bằng lợi ích nén lịch sử.

Advanced cũng tạo nhiều output token hơn vì phản hồi có cấu trúc và chứa profile fact. Điều này cho thấy compact memory chủ yếu tối ưu input context, không đảm bảo giảm output token.

### Vì sao compact có lợi trong hội thoại dài?

Ở stress test, Baseline liên tục gửi lại full history nên tổng prompt tokens đạt 22,413. Advanced compact 4 lần, chỉ giữ summary và các message gần nhất, làm prompt tokens giảm còn 14,685 — thấp hơn khoảng 34.5% — trong khi recall vẫn đạt `1.000`.

Kết quả thể hiện trade-off chính của bài lab:

- persistent memory cải thiện recall nhưng tạo chi phí cố định;
- compact memory có overhead ở đoạn đầu;
- lợi ích token chỉ rõ rệt khi context đủ dài;
- thiết kế mạnh hơn cần thêm extraction, conflict handling, lưu file và test.

### Memory growth và rủi ro

Baseline không ghi profile nên memory growth bằng 0. Advanced tăng 285 byte ở standard và 235 byte ở stress test. Với benchmark nhỏ, con số này thấp; trong production, profile có thể phình nếu mọi message đều được lưu hoặc cùng một fact bị ghi lặp.

Các rủi ro còn lại:

- regex có thể hiểu sai câu phức tạp ngoài dataset;
- một correction mơ hồ có thể ghi đè fact đúng;
- summary heuristic có thể bỏ mất chi tiết ít được nhắc lại;
- file Markdown không phù hợp cho nhiều tiến trình ghi đồng thời;
- estimator `len(text) / 4` chỉ dùng để so sánh, không phải số token billing thật.

## Bonus đã triển khai

Bài làm có hai mở rộng phục vụ trực tiếp cho dataset:

1. Structured extraction: profile được lưu dưới dạng các field như `name`, `location`, `profession` và `response_style`.
2. Conflict handling: fact mới được upsert thay vì nối thêm; câu hỏi, câu đùa và địa điểm đi họp không ghi đè profile.

Các test correction/noise chứng minh nghề nghiệp cuối là `MLOps engineer` và nơi ở standard cuối là `Huế`.

## Phạm vi đánh giá

`Response quality` hiện là heuristic dựa trên factual coverage và độ dài hợp lý. `judge_model` đã được cấu hình để dùng Anthropic qua MWAPI nhưng benchmark mặc định không gọi API thật, nhằm giữ kết quả offline lặp lại được và không phát sinh chi phí ngoài ý muốn.
