# Checkpoints thực hiện Lab Day 17: Memory Systems for AI Agent

Tài liệu này chia bài lab thành các checkpoint có thể thực hiện và kiểm tra độc lập. Chỉ chuyển sang checkpoint tiếp theo khi phần **Điều kiện hoàn thành** của checkpoint hiện tại đã đạt.

## Tổng quan tiến độ

- [x] Checkpoint 0 — Chuẩn bị môi trường và đọc scaffold
- [x] Checkpoint 1 — Cấu hình model và ứng dụng
- [x] Checkpoint 2 — Xây dựng persistent memory với `User.md`
- [x] Checkpoint 3 — Trích xuất và cập nhật profile facts
- [x] Checkpoint 4 — Xây dựng compact memory
- [x] Checkpoint 5 — Hoàn thiện Baseline Agent
- [x] Checkpoint 6 — Hoàn thiện Advanced Agent
- [x] Checkpoint 7 — Viết và chạy test cốt lõi
- [x] Checkpoint 8 — Xây dựng Standard Benchmark
- [x] Checkpoint 9 — Xây dựng Long-Context Stress Benchmark
- [x] Checkpoint 10 — Phân tích kết quả và hoàn thiện báo cáo
- [x] Checkpoint 11 — Bonus hướng tới 90–100 điểm
- [x] Checkpoint 12 — Kiểm tra và bàn giao cuối cùng

---

## Checkpoint 0 — Chuẩn bị môi trường và đọc scaffold

### Mục tiêu

Hiểu cấu trúc repo và có môi trường Python chạy được.

### Công việc

- [x] Sử dụng Python `>= 3.11`.
- [x] Tạo virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

- [x] Cài các package cần thiết:

```powershell
pip install langchain langgraph langchain-openai langchain-google-genai langchain-anthropic langchain-ollama langchain-openrouter python-dotenv tabulate pytest
```

- [x] Đọc `README.md`, `Guide.md` và `Rubric.md`.
- [x] Đọc lần lượt các file trong `src/`.
- [x] Kiểm tra `state/` và `.env` đã nằm trong `.gitignore`.
- [x] Xác nhận hai dataset có thể đọc dưới dạng UTF-8 JSON.

### Điều kiện hoàn thành

- [x] Chạy được `python --version` và phiên bản từ 3.11 trở lên.
- [x] Import được `pytest`.
- [x] Hiểu sự khác nhau giữa short-term, persistent và compact memory.
- [x] Biết rằng chế độ offline là bắt buộc để test không cần API key; chế độ live là phần mở rộng.

---

## Checkpoint 1 — Cấu hình model và ứng dụng

### Mục tiêu

Tạo được cấu hình chung cho toàn bộ lab mà không phụ thuộc cứng vào một LLM provider.

### File thực hiện

- `src/model_provider.py`
- `src/config.py`

### Công việc trong `model_provider.py`

- [x] Hoàn thiện `ProviderConfig`.
- [x] Viết `normalize_provider()`.
- [x] Chuẩn hóa alias/lỗi chính tả như `anthorpic` thành `anthropic`.
- [x] Từ chối provider không được hỗ trợ bằng lỗi dễ hiểu.
- [x] Viết `build_chat_model()` cho:
  - [x] `openai`
  - [x] `custom`
  - [x] `gemini`
  - [x] `anthropic`
  - [x] `ollama`
  - [x] `openrouter`
- [x] Chỉ khởi tạo model thật khi chạy live mode.

### Công việc trong `config.py`

- [x] Xác định đúng `base_dir`.
- [x] Cấu hình `data_dir = base_dir / "data"`.
- [x] Cấu hình `state_dir = base_dir / "state"`.
- [x] Tự động tạo `state_dir` nếu chưa có.
- [x] Đọc `.env` bằng `python-dotenv` nếu có.
- [x] Đọc provider, model name, API key và base URL từ biến môi trường.
- [x] Đặt giá trị mặc định hợp lý cho `compact_threshold_tokens`.
- [x] Đặt giá trị mặc định hợp lý cho `compact_keep_messages`.
- [x] Tạo cấu hình model chính và judge model.
- [x] Trả về một `LabConfig` hoàn chỉnh từ `load_config()`.

### Điều kiện hoàn thành

- [x] `load_config()` chạy được khi không có API key.
- [x] Thư mục `state/` được tạo tự động.
- [x] Config chứa đúng đường dẫn `data/` và `state/`.
- [x] Offline mode không cố kết nối tới provider.

### Kiểm tra nhanh

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from config import load_config; print(load_config())"
```

---

## Checkpoint 2 — Xây dựng persistent memory với `User.md`

### Mục tiêu

Mỗi người dùng có một profile Markdown bền vững, đọc lại được giữa các thread.

### File thực hiện

- `src/memory_store.py`

### Công việc

- [x] Viết `estimate_tokens()`.
- [x] Chuỗi rỗng trả về `0` token.
- [x] Kết quả token luôn là số nguyên không âm.
- [x] Viết `UserProfileStore.path_for()`.
- [x] Sanitize `user_id` để tránh path traversal.
- [x] Dùng cấu trúc `state/profiles/<user_id>/User.md`.
- [x] Viết `read_text()`.
- [x] Khi file chưa tồn tại, trả về profile mặc định hoặc chuỗi rỗng hợp lệ.
- [x] Viết `write_text()` và tự tạo thư mục cha.
- [x] Ghi file bằng UTF-8.
- [x] Viết `edit_text()` và trả về trạng thái có thay đổi hay không.
- [x] Viết `file_size()` theo số byte thật trên đĩa.
- [x] Cân nhắc thêm `facts()` để đọc profile thành dictionary.
- [x] Cân nhắc thêm `upsert_fact()` để cập nhật một field mà không tạo dòng trùng.

### Điều kiện hoàn thành

- [x] Có thể tạo `User.md` cho một user mới.
- [x] Có thể đọc lại đúng tiếng Việt.
- [x] Có thể sửa một fact đã tồn tại.
- [x] `file_size()` thay đổi sau khi ghi thêm nội dung.
- [x] `user_id` không thể thoát khỏi thư mục `profiles/`.

---

## Checkpoint 3 — Trích xuất và cập nhật profile facts

### Mục tiêu

Chỉ lưu những thông tin người dùng ổn định và xử lý đúng các bản đính chính.

### File thực hiện

- `src/memory_store.py`

### Công việc

- [x] Viết `extract_profile_updates()`.
- [x] Trích xuất được:
  - [x] tên
  - [x] nơi ở
  - [x] nghề nghiệp
  - [x] sở thích kỹ thuật
  - [x] món ăn/đồ uống yêu thích
  - [x] pet
  - [x] style trả lời
- [x] Bỏ qua message chỉ chứa câu hỏi.
- [x] Không lưu câu đùa thành nghề nghiệp thật.
- [x] Không coi nơi đi họp/du lịch là nơi ở.
- [x] Khi có correction, fact mới ghi đè fact cũ.
- [x] Không giữ đồng thời `Đà Nẵng` và `Huế` làm nơi ở hiện tại.
- [x] Không giữ đồng thời `backend engineer` và `MLOps engineer` làm nghề hiện tại.
- [x] Không ghi lặp cùng một fact nhiều lần vào `User.md`.

### Ca kiểm tra bắt buộc

- [x] `"Mình tên là DũngCT"` tạo fact tên `DũngCT`.
- [x] `"Mình ở Đà Nẵng"` tạo fact nơi ở `Đà Nẵng`.
- [x] `"Giờ mình đang ở Huế chứ không còn ở Đà Nẵng"` cập nhật nơi ở thành `Huế`.
- [x] `"Giờ chuyển sang MLOps engineer"` cập nhật nghề nghiệp.
- [x] `"Hay là chuyển sang product manager"` không làm thay đổi nghề nghiệp.
- [x] `"Bay ra Hà Nội họp hai ngày"` không làm thay đổi nơi ở.

### Điều kiện hoàn thành

- [x] Profile cuối cùng phản ánh fact mới nhất.
- [x] Các message gây nhiễu không làm hỏng profile.
- [x] Profile ngắn gọn, có cấu trúc và không bị trùng lặp.

---

## Checkpoint 4 — Xây dựng compact memory

### Mục tiêu

Nén lịch sử hội thoại dài nhưng vẫn giữ summary và các message gần nhất.

### File thực hiện

- `src/memory_store.py`

### Công việc

- [x] Viết `summarize_messages()`.
- [x] Summary ngắn hơn đáng kể so với raw messages.
- [x] Summary giữ được fact và ý chính quan trọng.
- [x] Khởi tạo state riêng cho từng `thread_id`.
- [x] State có tối thiểu:
  - [x] `messages`
  - [x] `summary`
  - [x] `compactions`
- [x] Viết `CompactMemoryManager.append()`.
- [x] Thêm đúng `role` và `content` của message.
- [x] Tính token của summary và recent messages.
- [x] Kích hoạt compact khi vượt threshold.
- [x] Chuyển message cũ vào summary.
- [x] Giữ lại đúng `keep_messages` gần nhất.
- [x] Tăng `compactions` sau mỗi lần nén.
- [x] Viết `context()`.
- [x] Viết `compaction_count()`.
- [x] Tránh vòng lặp nếu một message riêng lẻ đã vượt threshold.

### Điều kiện hoàn thành

- [x] Thread ngắn chưa bị compact.
- [x] Thread dài có `compactions > 0`.
- [x] Sau compact, số raw messages giảm.
- [x] Recent messages vẫn còn nguyên.
- [x] Summary không chứa nguyên văn toàn bộ lịch sử cũ.

---

## Checkpoint 5 — Hoàn thiện Baseline Agent

### Mục tiêu

Tạo agent đối chứng chỉ nhớ trong cùng một thread.

### File thực hiện

- `src/agent_baseline.py`

### Công việc

- [x] State được lưu theo `thread_id`, không theo `user_id`.
- [x] Viết `reply()`.
- [x] Ưu tiên offline path khi `force_offline=True`.
- [x] Viết `_reply_offline()`.
- [x] Lưu user message vào session.
- [x] Sinh response ngắn, ổn định và có tính xác định.
- [x] Lưu assistant response vào session.
- [x] Tính token của response.
- [x] Tính context được xử lý trong mỗi lượt.
- [x] Cộng dồn `token_usage` theo thread.
- [x] Cộng dồn `prompt_tokens_processed` theo thread.
- [x] Viết `token_usage()`.
- [x] Viết `prompt_token_usage()`.
- [x] Giữ `compaction_count()` luôn bằng `0`.
- [x] Không đọc hoặc ghi `User.md`.
- [x] `_maybe_build_langchain_agent()` không làm hỏng offline mode.

### Điều kiện hoàn thành

- [x] Baseline nhớ nội dung vừa nói trong cùng thread.
- [x] Baseline không nhớ tên hoặc nghề nghiệp khi chuyển sang thread mới.
- [x] Baseline không tạo file profile.
- [x] Lịch sử dài làm `prompt_tokens_processed` tăng mạnh.

---

## Checkpoint 6 — Hoàn thiện Advanced Agent

### Mục tiêu

Kết hợp short-term, persistent và compact memory trong một agent.

### File thực hiện

- `src/agent_advanced.py`

### Công việc

- [x] Khởi tạo `UserProfileStore`.
- [x] Khởi tạo `CompactMemoryManager`.
- [x] Viết `reply()`.
- [x] Viết `_reply_offline()` theo đúng thứ tự:
  - [x] trích xuất fact
  - [x] cập nhật `User.md`
  - [x] append user message
  - [x] ước lượng prompt context
  - [x] tạo response
  - [x] append assistant response
  - [x] cập nhật token counters
- [x] Viết `_estimate_prompt_context_tokens()`.
- [x] Context bao gồm profile, summary và recent messages.
- [x] Viết `_offline_response()`.
- [x] Trả lời được câu hỏi về tên.
- [x] Trả lời được câu hỏi về nghề nghiệp hiện tại.
- [x] Trả lời được câu hỏi về nơi ở hiện tại.
- [x] Trả lời được câu hỏi về sở thích và style.
- [x] Viết `token_usage()`.
- [x] Viết `prompt_token_usage()`.
- [x] Viết `memory_file_size()`.
- [x] Viết `compaction_count()`.
- [x] Không hard-code `DũngCT`, `Huế`, `Đà Nẵng` hoặc `MLOps engineer` trong logic trả lời.
- [x] `_maybe_build_langchain_agent()` không làm hỏng offline mode.

### Điều kiện hoàn thành

- [x] Advanced nhớ được fact khi chuyển sang thread mới.
- [x] Advanced ưu tiên correction mới nhất.
- [x] Advanced tạo và cập nhật đúng `User.md`.
- [x] Hội thoại dài kích hoạt compact memory.
- [x] Response được tạo từ memory, không từ đáp án benchmark.

---

## Checkpoint 7 — Viết và chạy test cốt lõi

### Mục tiêu

Kiểm chứng hành vi memory thay vì chỉ kiểm tra chương trình có chạy.

### File thực hiện

- `src/test_agents.py`

### Công việc

- [x] Viết `make_config(tmp_path)`.
- [x] Trỏ `state_dir` vào thư mục tạm.
- [x] Đặt compact threshold thấp để test nhanh.
- [x] Viết `test_user_markdown_read_write_edit()`.
- [x] Viết `test_compact_trigger()`.
- [x] Viết `test_cross_session_recall()`.
- [x] Viết `test_compact_reduces_prompt_load_on_long_thread()`.
- [x] Test Advanced nhớ qua thread mới.
- [x] Test Baseline quên qua thread mới.
- [x] Test Baseline có `compactions == 0`.
- [x] Test Advanced có `compactions > 0` trong thread dài.
- [x] Test correction nơi ở.
- [x] Test correction nghề nghiệp.
- [x] Test bỏ qua câu đùa `product manager`.
- [x] Test bỏ qua chuyến đi họp ở `Hà Nội`.

### Điều kiện hoàn thành

- [x] Tất cả test chạy offline.
- [x] Test không ghi dữ liệu vào `state/` thật.
- [x] Các test cốt lõi đều pass.

### Lệnh kiểm tra

```powershell
pytest src/test_agents.py -v
```

---

## Checkpoint 8 — Xây dựng Standard Benchmark

### Mục tiêu

So sánh Baseline và Advanced trên 10 hội thoại thông thường.

### File thực hiện

- `src/benchmark.py`
- `data/conversations.json`

### Công việc

- [x] Viết `load_conversations()` và đọc JSON bằng UTF-8.
- [x] Viết `recall_points()`.
- [x] Chọn và ghi rõ cách tính partial recall.
- [x] Viết `heuristic_quality()`.
- [x] Viết `run_agent_benchmark()`.
- [x] Dùng cùng input cho cả hai agent.
- [x] Dùng conversation ID làm thread huấn luyện/ngữ cảnh.
- [x] Hỏi recall trong thread mới.
- [x] Không truyền `expected_contains` vào agent.
- [x] Không để câu hỏi recall của trước làm rò rỉ đáp án cho câu sau.
- [x] Cộng dồn agent output tokens.
- [x] Cộng dồn prompt tokens processed.
- [x] Tính recall trung bình.
- [x] Tính response quality trung bình.
- [x] Đo memory growth theo byte.
- [x] Cộng tổng số compactions.
- [x] Viết `format_rows()`.

### Sáu cột bắt buộc

- [x] `Agent tokens only`
- [x] `Prompt tokens processed`
- [x] `Cross-session recall`
- [x] `Response quality`
- [x] `Memory growth (bytes)`
- [x] `Compactions`

### Điều kiện hoàn thành

- [x] Standard Benchmark có hàng Baseline và Advanced.
- [x] Advanced có recall cao hơn Baseline.
- [x] Baseline có memory growth bằng `0`.
- [x] Advanced có profile memory lớn hơn `0`.
- [x] Kết quả không phụ thuộc API key.

---

## Checkpoint 9 — Xây dựng Long-Context Stress Benchmark

### Mục tiêu

Chứng minh compact memory giúp giảm tổng prompt context trong hội thoại dài.

### File thực hiện

- `src/benchmark.py`
- `data/advanced_long_context.json`

### Công việc

- [x] Load stress dataset riêng.
- [x] Chạy Baseline và Advanced trên cùng 16 lượt dài.
- [x] Dùng state/profile sạch trước khi benchmark nếu cần.
- [x] Hỏi recall trong thread mới.
- [x] Kiểm tra Advanced nhớ:
  - [x] `DũngCT Stress`
  - [x] `MLOps engineer`
  - [x] `Đà Nẵng`
  - [x] style `3 bullet`
- [x] Kiểm tra không chọn nhầm:
  - [x] `Huế`
  - [x] `Hà Nội`
  - [x] `product manager`
- [x] Xác nhận Advanced có ít nhất một compaction.
- [x] So sánh tổng prompt tokens processed.
- [x] In bảng Long-Context Stress Benchmark.
- [ ] Nếu có thời gian, thêm recall cho bốn abstraction: readiness, externality, uncertainty và efficiency.

### Điều kiện hoàn thành

- [x] Baseline có `compactions == 0`.
- [x] Advanced có `compactions > 0`.
- [x] Advanced xử lý ít prompt token hơn Baseline trong stress test.
- [x] Advanced vẫn trả lời đúng profile sau compact.
- [x] Summary không làm mất correction quan trọng.

---

## Checkpoint 10 — Phân tích kết quả và hoàn thiện báo cáo

### Mục tiêu

Giải thích được kết quả benchmark và trade-off của thiết kế.

### Công việc

- [x] Ghi lại bảng kết quả Standard Benchmark.
- [x] Ghi lại bảng kết quả Stress Benchmark.
- [x] Giải thích vì sao Baseline quên khi đổi thread.
- [x] Giải thích vì sao `User.md` cải thiện cross-session recall.
- [x] Giải thích vì sao Advanced có thể tốn hơn trong hội thoại ngắn.
- [x] Giải thích vì sao full history làm tổng prompt cost tăng nhanh.
- [x] Giải thích vì sao compact chủ yếu tối ưu input/prompt tokens.
- [x] Phân biệt `Agent tokens only` và `Prompt tokens processed`.
- [x] Phân tích memory growth theo byte.
- [x] Nêu rủi ro profile phình to.
- [x] Nêu rủi ro lưu sai fact.
- [x] Nêu rủi ro summary làm mất chi tiết.
- [x] Nêu chi phí tăng thêm về code, test và guardrail.

### Điều kiện hoàn thành

- [x] Phần phân tích dựa trên số liệu benchmark thực tế.
- [x] Không kết luận rằng Advanced luôn tốt hơn ở mọi chỉ số.
- [x] Có nhận xét rõ về trade-off giữa recall, token cost và độ phức tạp.

---

## Checkpoint 11 — Bonus hướng tới 90–100 điểm

### Mục tiêu

Bổ sung ít nhất một cơ chế memory có giá trị thực tế và kiểm chứng được.

### Chọn ít nhất một hướng

- [ ] Confidence threshold trước khi ghi fact.
- [x] Structured entity extraction.
- [ ] Conflict handling có metadata.
- [ ] Memory decay theo thời gian hoặc tần suất.
- [ ] Timestamp cho từng fact.
- [ ] Nguồn gốc/provenance của fact.
- [ ] Atomic write hoặc versioning cho `User.md`.
- [ ] LLM-based summary có fallback offline.

### Yêu cầu cho bonus đã chọn

- [x] Nêu vấn đề mà bonus giải quyết.
- [x] Viết test chứng minh bonus hoạt động.
- [x] So sánh trước và sau khi thêm bonus.
- [x] Nêu ảnh hưởng đến recall.
- [x] Nêu ảnh hưởng đến token hoặc memory growth.
- [x] Nêu rủi ro mới do bonus tạo ra.

### Điều kiện hoàn thành

- [x] Bonus không làm hỏng bốn test cốt lõi.
- [x] Có bằng chứng bằng test hoặc benchmark, không chỉ mô tả lý thuyết.

---

## Checkpoint 12 — Kiểm tra và bàn giao cuối cùng

### Mục tiêu

Đảm bảo bài có thể chạy lại từ đầu và phản ánh đúng yêu cầu rubric.

### Kiểm tra code

- [x] Không còn `NotImplementedError` trong luồng bắt buộc.
- [x] Không còn `TODO` ảnh hưởng tới offline mode, test hoặc benchmark.
- [x] Không hard-code đáp án dataset.
- [x] Naming giữa Baseline và Advanced nhất quán.
- [x] Code tách trách nhiệm rõ ràng.
- [x] File được đọc/ghi bằng UTF-8.
- [x] Không commit `.env`.
- [x] Không commit `state/`.
- [x] Không commit cache hoặc file tạm.

### Chạy kiểm tra

```powershell
pytest src/test_agents.py -v
python src/benchmark.py
```

### Kết quả bàn giao bắt buộc

- [x] Tất cả test pass.
- [x] Có bảng Standard Benchmark.
- [x] Có bảng Long-Context Stress Benchmark.
- [x] Mỗi bảng có đủ sáu chỉ số.
- [x] Baseline quên qua thread mới.
- [x] Advanced nhớ qua thread mới.
- [x] Correction được xử lý đúng.
- [x] Stress benchmark kích hoạt compact.
- [x] Advanced giảm prompt load trong hội thoại dài.
- [x] Có phần phân tích trade-off.

---

## Definition of Done toàn bài

Bài lab được xem là hoàn thành khi đáp ứng đồng thời các điều kiện sau:

- [x] Hai agent chạy được ở offline mode mà không cần API key.
- [x] Baseline chỉ có within-thread memory.
- [x] Advanced có short-term, persistent và compact memory.
- [x] `User.md` lưu đúng fact ổn định và cập nhật correction.
- [x] Compact memory thực sự làm giảm raw context.
- [x] Bốn test cốt lõi đều pass.
- [x] Hai benchmark chạy được trên cùng dữ liệu cho cả hai agent.
- [x] Kết quả thể hiện đúng khác biệt về recall, prompt cost, memory growth và compaction.
- [x] Phần phân tích giải thích được lợi ích, chi phí và rủi ro của hệ thống memory.
