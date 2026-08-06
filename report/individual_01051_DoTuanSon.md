# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| Họ và tên | Đỗ Tuấn Sơn |
| MSSV | 2A202601051 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm B51 |
| Vai trò chính | Role 5 — Pipeline Integration & Evidence Owner |
| Repository | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

Là **Role 5 — Integration**, tôi là nút thắt cuối của cả hai pipeline: lắp ráp các module do 4 thành viên còn lại bàn giao (ingestion, cleaning, eval-set, observability, corruption) thành hai luồng chạy được thật và sinh ra bằng chứng số liệu cuối cùng cho cả nhóm. Tôi **không** sửa code của bất kỳ ai — chỉ gọi lại đúng contract họ đã thống nhất.

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| Baseline Pipeline Orchestration | `src/pipelines/phase1.py::main()` | Settings + module N1/N2/N3 | `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md` | Hoàn thành |
| Baseline Runner | `script/run_phase1.py` | — | Chạy end-to-end 8 bước | Hoàn thành |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py::main()` | Corrupted data (N4) + raw snapshot (N1) + cleaning (N2) | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |
| Corruption Runner | `script/run_corruption_flow.py` | Baseline artifacts | Chạy end-to-end 10 bước | Hoàn thành |
| Evidence & Git Hygiene | `.gitignore`, `git log`, `group_report.md` (mục 3,4,7,10) | Metrics thật | Repo sạch, không lộ secret; số liệu khớp JSON | Hoàn thành |

### Thứ tự gọi hàm tôi chịu trách nhiệm lắp ráp

- **`phase1.py` (baseline, 8 bước):** `load_settings` → `fetch_source_records`/`load_raw_records` (N1) → `build_clean_dataframe` (N2) → lưu clean CSV/JSON → `LocalEmbeddingIndex.build` (reference) → `build_test_set` (N2) → `evaluate_pipeline` (reference) → `run_data_quality_checks` + `build_freshness_report` (N3) → `generate_phase1_report` (N3).
- **`corruption_flow.py` (corruption→repair, 10 bước):** load baseline + clean → `corrupt_clean_dataframe` (N4) → rebuild index corrupted → `evaluate_pipeline` → quality/freshness (N3) → **Repair:** `load_raw_records` (N1) + `build_clean_dataframe` (N2) → rebuild index repaired → `evaluate_pipeline` lại → quality/freshness → `generate_corruption_report` (N3).

---

## 3. Bảng tổng hợp Metrics 3 Trạng thái

> Nguồn số liệu: `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` do hai pipeline tôi lắp ráp sinh ra.

| Metric / Signal | Baseline (Clean) | Corrupted Phase | Repaired Phase |
| :--- | :---: | :---: | :---: |
| `retrieval_hit_rate` | **1.0000** | **0.8000** 📉 | **1.0000** 📈 |
| `mean_token_f1` | **0.1059** | **0.0649** 📉 | **0.1059** 📈 |
| **Data Quality Status** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** |
| **Data Freshness Status** | ✅ **FRESH** | ❌ **STALE** | ✅ **FRESH** |

**Đọc bảng:** corruption của Người 4 trúng đúng `ground_truth_doc_ids` nên metrics **giảm thấy được** (hit-rate 1.0 → 0.8), quality/freshness chuyển FAIL/STALE đúng kỳ vọng. Sau bước Repair, cả hai metric **hồi phục bằng baseline** — chứng minh dữ liệu hỏng là nguyên nhân, và pipeline phục hồi được từ nguồn sạch.

---

## 4. Câu hỏi trọng tâm của vai trò — Vì sao Repair phải đọc lại raw snapshot, KHÔNG fetch lại API?

1. **Tính tái lập & cô lập biến (reproducibility).** Nếu bước repair gọi lại Crossref, tập dữ liệu trả về có thể khác baseline (thêm/bớt bài mới, đổi thứ tự, đổi abstract). Khi đó metrics repaired thay đổi vì *nguồn* đổi, không phải vì ta đã sửa lỗi — mất khả năng so sánh 3 trạng thái trên cùng một tập dữ liệu.
2. **Test set đã đóng băng (quy tắc vàng #4).** `test_set.json` và `ground_truth_doc_ids` khoá theo `paper_id` của baseline. Fetch mới có thể làm biến mất chính những `paper_id` mà test set đang hỏi → nhiều câu hỏi mất ground truth, metrics vô nghĩa.
3. **Repair đúng nghĩa = tái dựng từ nguồn sạch tin cậy, không phụ thuộc mạng.** `corruption_flow.py` (Step 6) gọi `load_raw_records(raw_records_json)` rồi `build_clean_dataframe` lại — cùng đúng hàm cleaning N2 đã dùng ở baseline. Điều này chứng minh raw snapshot là "single source of truth" và pipeline cleaning là idempotent (chạy lại ra kết quả bằng baseline).
4. **Tốn kém & rate-limit.** Tránh gọi API lần hai giúp không dính HTTP 429/503 và pipeline chạy được offline/tất định — quan trọng khi chấm điểm và tái chạy.

---

## 5. Rủi ro tích hợp đã xử lý

| Rủi ro | Nguyên nhân gốc | Cách xử lý |
| :--- | :--- | :--- |
| `phase1.py` chặn bởi 4 người | 3 mũi tên phụ thuộc cứng đổ vào `T5.3` | Làm prep-work T5.1/T5.2 (đọc `retrieval/*`, soạn khung 8 bước) từ phút 0 để không ngồi không |
| Baseline chưa chạy mà đã chạy corruption | `corruption_flow` cần `baseline_metrics.json` | Guard `if not baseline_metrics.exists(): raise RuntimeError` (Step 1) |
| Pipeline lỗi do file reference | Nghi bug trong `retrieval/*` / `metrics.py` | Kiểm ngược contract dữ liệu đầu vào trước (quy tắc vàng #6) — hầu hết là sai schema, không phải bug |
| Lộ secret khi push | `.env` chứa `GOOGLE_API_KEY` | Rà `.gitignore` + `git log --stat` / `git status` trước khi push (T5.8) |

---

## 6. Cam kết cá nhân

- [x] Nội dung báo cáo phản ánh đúng phần việc Role 5 (Integration) và mức hiểu của tôi.
- [x] Có thể giải thích luồng end-to-end từ API ingestion → cleaning → index → RAG evaluation → observability → corruption → repair.
- [x] Mọi kết luận đều được kiểm chứng bằng file artifacts trong `data/results/`, `data/quality/`, `data/reports/`.
- [x] Đã rà `git log`/`.gitignore` — không commit `.env` hay API key vào repo.
