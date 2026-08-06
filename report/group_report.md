# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| :--- | :--- |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm Data Observability Lab |
| Repository | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | :--- | :--- | :--- | :--- |
| 1 | Học viên | Student_ID | Data Engineer & Pipeline Lead | External API Ingestion (`crossref.py`), Data Cleaning (`cleaning.py`) |
| 2 | Thành viên 2 | Student_ID_2 | Evaluation & RAG Specialist | Frozen Test Set Builder (`testset.py`), RAG Evaluator (`metrics.py`) |
| 3 | Thành viên 3 | Student_ID_3 | Observability & QA Lead | Quality & Freshness Monitoring (`quality.py`, `reporting.py`) |
| 4 | Thành viên 4 | Student_ID_4 | Orchestration & Experiment | Phase 1 & Corruption Flow (`phase1.py`, `corruption_flow.py`, `corruption.py`) |

---

## 2. Tóm tắt kết quả

Nhóm đã xây dựng thành công pipeline dữ liệu end-to-end cho hệ thống RAG bài báo khoa học từ Crossref API. 
1. **Baseline Pipeline**: Lấy 24 bản ghi thô từ Crossref, làm sạch dữ liệu, tạo vector store ChromaDB (MiniLM 384 dimensions), chốt bộ test 10 câu hỏi đóng băng (`test_set.json`), đạt `retrieval_hit_rate = 1.0` (100%) và Data Quality/Freshness đạt **PASS**.
2. **Controlled Corruption**: Giả lập 4 dạng lỗi (xóa bản ghi mục tiêu, rỗng summary, ngày cũ year 2000, thêm dòng trùng). Kết quả làm `retrieval_hit_rate` giảm xuống 0.8 (80%) và Data Quality/Freshness báo lỗi **FAIL**.
3. **Pipeline Repair**: Tái tạo lại dữ liệu sạch từ **raw snapshot JSON**, giúp phục hồi `retrieval_hit_rate` về lại 1.0 (100%) và Data Quality đạt **PASS**.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response (crossref_response.json) / raw records (crossref_records.json)
    -> cleaning & data modeling (papers_clean.csv / json)
    -> embedding + ChromaDB index (papers-baseline)
    -> evaluation baseline (baseline_metrics.json, baseline_answers.json)
    -> quality/freshness reports (baseline_quality.json, freshness_report.json)
    -> controlled corruption (papers_clean_corrupted.csv / json, corruption_log.json)
    -> re-index & re-evaluate (corrupted_metrics.json, corrupted_quality.json)
    -> repair từ raw records snapshot (papers_clean_repaired.csv / json)
    -> comparison report (corruption_report.md)
```

---

## 4. Cách tái hiện kết quả

### Cấu hình môi trường

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 days |

### Lệnh chạy pipeline

```bash
# Phase 1 Baseline
python script/run_phase1.py

# Phase 2 Corruption Flow & Repair
python script/run_corruption_flow.py
```

---

## 5. Ingestion, cleaning và data contract

### Quy tắc Cleaning
- Stripping HTML/XML tags (ví dụ `<jats:p>`) khỏi tiêu đề và tóm tắt.
- Loại bỏ các dòng có tiêu đề rỗng hoặc tóm tắt < 100 ký tự.
- Gộp tác giả thành `authors_joined`, thể loại thành `categories_joined`.
- Tính `published` format YYYY-MM-DD và `age_days`.
- Tạo cột `text_for_embedding` = `Title: [title] | Authors: [authors] | Summary: [summary]`.

---

## 6. Kết quả so sánh 3 trạng thái (Baseline vs Corrupted vs Repaired)

| Metric / Observability Signal | Baseline (Clean) | Corrupted | Repaired | Nhận xét |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.8000** | **1.0000** | Phục hồi hoàn toàn về 100% |
| `mean_token_f1` | **0.1059** | **0.0649** | **0.1059** | Sụt giảm ở trạng thái lỗi và phục hồi sau khi repair |
| `judge_accuracy` | **0.1000** | **0.0000** | **0.1000** | Phản ánh chính xác chất lượng câu trả lời |
| **Data Quality Status** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** | Phát hiện trùng lặp và summary rỗng |
| **Data Freshness Status** | ✅ **FRESH** | ❌ **STALE** | ✅ **FRESH** | Phát hiện mốc ngày bị đẩy về năm 2000 |

---

## 7. Kết luận có quan hệ nhân quả

1. **Dữ liệu thô lỗi -> Suy giảm RAG Retrieval**: Khi xóa bản ghi mục tiêu thuộc bộ test set, Vector DB không thể trích xuất đúng document ID, dẫn đến `retrieval_hit_rate` giảm từ 1.0000 xuống 0.8000.
2. **Observability phát hiện lỗi -> Phục hồi dữ liệu**: Quality check phát hiện 2 bản ghi trùng lặp và 3 bản ghi bị đẩy ngày về năm 2000. Thực hiện Repair từ `crossref_records.json` khôi phục lại 100% chỉ số chất lượng và hiệu năng tìm kiếm.
