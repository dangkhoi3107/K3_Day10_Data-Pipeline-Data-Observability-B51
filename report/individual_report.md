# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| Họ và tên | Student Lead |
| MSSV | Student_ID |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm Data Observability Lab |
| Vai trò chính | Data Engineer & Pipeline Developer |
| Repository | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| External Data Ingestion | `src/ingestion/crossref.py` | Crossref REST API | `data/raw/crossref_response.json`, `crossref_records.json` | Hoàn thành |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py` | `list[PaperRecord]` | `data/clean/papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| Data Corruption Engine | `src/ingestion/corruption.py` | Cleaned DataFrame | `data/clean/papers_clean_corrupted.csv`, `corruption_log.json` | Hoàn thành |
| Frozen Eval Set Builder | `src/evaluation/testset.py` | Cleaned DataFrame | `data/eval/test_set.json` (10 samples) | Hoàn thành |
| Observability Reporting | `src/observability/quality.py`, `reporting.py` | DataFrames & Metrics | `data/quality/baseline_quality.json`, `freshness_report.json`, `corruption_report.md` | Hoàn thành |
| Pipeline Orchestration | `src/pipelines/phase1.py`, `corruption_flow.py` | Settings & Modules | Baseline & Corruption Flow Pipelines | Hoàn thành |

---

## 3. Bảng tổng hợp Metrics 3 Trạng thái

| Metric / Signal | Baseline (Clean) | Corrupted Phase | Repaired Phase |
| :--- | :---: | :---: | :---: |
| `retrieval_hit_rate` | **1.0000** | **0.8000** 📉 | **1.0000** 📈 |
| `mean_token_f1` | **0.1059** | **0.0649** 📉 | **0.1059** 📈 |
| **Data Quality Status** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** |
| **Data Freshness Status** | ✅ **FRESH** | ❌ **STALE** | ✅ **FRESH** |

---

## 4. Cam kết cá nhân

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Có thể giải thích luồng end-to-end từ API ingestion đến RAG evaluation.
- [x] Mọi kết luận đều được kiểm chứng bằng file artifacts trong `data/`.
- [x] Không chứa API key hay file nhạy cảm `.env` trong Git repo.
