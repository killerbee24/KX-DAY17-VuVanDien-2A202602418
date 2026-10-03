# Completed Lab Implementation

Thư mục `src/` chứa bản triển khai hoàn chỉnh của lab:

- Baseline Agent chỉ nhớ trong cùng thread.
- Advanced Agent dùng `User.md`, structured fact extraction và compact memory.
- Offline mode có tính xác định, không yêu cầu API key.
- Live model hỗ trợ `openai`, `custom`, `gemini`, `anthropic`, `ollama` và `openrouter`.
- MWAPI được cấu hình dưới dạng provider `custom` OpenAI-compatible.
- Benchmark gồm Standard Benchmark và Long-Context Stress Benchmark.
- Test kiểm tra profile, compaction, cross-session recall, prompt load, correction và path sanitization.

Chạy từ thư mục gốc:

```powershell
pytest src/test_agents.py -v
python src/benchmark.py
```

Datasets nằm trong `data/`; kết quả phân tích được ghi trong `ANALYSIS.md`.
