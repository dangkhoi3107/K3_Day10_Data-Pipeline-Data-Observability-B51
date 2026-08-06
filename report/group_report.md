# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3                          |
| Tên nhóm         | Nhóm B51                   |
| Repository         | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06                  |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Phạm Nguyễn Đăng Khôi | 2A202601243 | Role 1 — Source Ingestion Owner | `src/ingestion/crossref.py` |
| 2 | Trần Trung | *[cần bổ sung MSSV]* | Role 2 — Cleaning & Evaluation-Set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | Vi Minh Hiển | *[cần bổ sung MSSV]* | Role 3 — Data Observability Owner | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | Nguyễn Đăng Đức | 2A202601787 | Role 4 — Corruption & Repair-Validation Owner | `src/ingestion/corruption.py` |
| 5 | Đỗ Tuấn Sơn | 01051 | Role 5 — Pipeline Integration & Evidence Owner | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |

> Phân vai theo `report/phan-cong-5-nguoi.md`. MSSV của Trần Trung và Vi Minh Hiển chưa có trong bất kỳ commit hay báo cáo nào tính đến thời điểm biên soạn — cần hai bạn tự bổ sung vào báo cáo cá nhân của mình trước khi nộp.

## 2. Tóm tắt kết quả

Nhóm đã xây dựng pipeline dữ liệu end-to-end cho hệ thống RAG trên bài báo học thuật lấy từ Crossref API, đi đủ qua 2 pha theo yêu cầu bài lab. Ở pha baseline, Role 1 lấy 24 bản ghi thô từ Crossref (đúng `max_results` cấu hình), Role 2 làm sạch thành dataset chuẩn hoá kèm `text_for_embedding`, dựng bộ test 10 câu hỏi đóng băng, và pipeline (Role 5) build index ChromaDB + MiniLM rồi đánh giá baseline. Theo báo cáo của Role 4 và Role 5, baseline đạt `retrieval_hit_rate = 1.0000`, `mean_token_f1 = 0.1059`, Data Quality và Freshness đều **PASS**. Ở pha corruption, Role 4 áp 4 kịch bản lỗi có kiểm soát (xoá 2 bản ghi trùng `ground_truth_doc_ids`, làm rỗng 3 summary, đẩy ngày xuất bản của 3 bản ghi về năm 2000, nhân đôi 2 dòng) — kết quả `retrieval_hit_rate` giảm còn 0.8000, `mean_token_f1` giảm còn 0.0649, Quality chuyển **FAIL** và Freshness chuyển **STALE**, đúng như kỳ vọng thiết kế corruption trúng test set. Bước Repair (Role 5) đọc lại raw snapshot gốc (không gọi lại API Crossref) và chạy lại đúng hàm cleaning của Role 2, đưa cả `retrieval_hit_rate` và `mean_token_f1` về đúng mức baseline, Quality/Freshness quay lại **PASS/FRESH**.

Giới hạn lớn nhất hiện tại: các artifact JSON thực tế (`data/results/*.json`, `data/clean/*`, `data/quality/*`) không có trong git (thư mục `data/` đã được thêm vào `.gitignore`) và không có mặt trên máy đang biên soạn báo cáo này — số liệu ở đây được tổng hợp từ báo cáo cá nhân của Role 4 và Role 5 (khớp nhau giữa hai nguồn độc lập), không phải số tự chạy lại và kiểm chứng trên nhánh `main` hiện tại. Role 2 và Role 3 cũng chưa có báo cáo cá nhân riêng tính đến thời điểm này.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (api.crossref.org/works)
    -> raw response / raw records (data/raw/crossref_response.json, crossref_records.json)   [Role 1]
    -> cleaning & data modeling (data/clean/papers_clean.csv / .json)                         [Role 2]
    -> evaluation set đóng băng (data/eval/test_set.json, 10 câu hỏi)                         [Role 2]
    -> embedding + ChromaDB index (collection "papers-baseline")                              [reference code]
    -> evaluation baseline (data/results/baseline_metrics.json, baseline_answers.json)        [reference code]
    -> quality/freshness reports (data/quality/baseline_quality.json, freshness_report.json)  [Role 3]
    -> markdown report (data/reports/phase1_report.md)                                        [Role 3 + Role 5]
    -> corruption có kiểm soát (data/clean/papers_clean_corrupted.*, corruption_log.json)     [Role 4]
    -> re-index + re-evaluate trên cùng test set (corrupted_metrics.json)                     [Role 5]
    -> repair: load_raw_records() + build_clean_dataframe() lại, KHÔNG gọi lại API            [Role 5, dùng lại hàm Role 1 + Role 2]
    -> re-index + re-evaluate lần 2 (repaired_metrics.json)                                   [Role 5]
    -> comparison report (data/reports/corruption_report.md)                                  [Role 3 + Role 5]
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | `Settings` (`source_query`, `source_filter`, `max_results=24`) | Gọi Crossref REST API, retry 429/503 (5 lần, backoff `2^attempt`), fallback đọc lại response cũ nếu vẫn lỗi, parse JSON → `PaperRecord` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Role 1 |
| Cleaning          | `list[PaperRecord]` | Strip HTML/JATS tag, loại record thiếu title/summary<100 ký tự, tính `age_days`, tạo `text_for_embedding`, dedupe theo `paper_id` **và** `title`, sort theo `published` | `data/clean/papers_clean.csv/.json` | Role 2 |
| Evaluation-set    | Cleaned DataFrame | Lấy 10 dòng đầu, sinh câu hỏi luân phiên 3 loại (`factual` tác giả, `summary`, `factual` ngày xuất bản) | `data/eval/test_set.json` | Role 2 |
| Embedding/index   | Cleaned/corrupted/repaired DataFrame | `sentence-transformers/all-MiniLM-L6-v2` + ChromaDB, 3 collection riêng (baseline/corrupted/repaired) | `data/embeddings/*.json`, ChromaDB collections | reference code (không ai sửa) |
| Observability     | DataFrame ở từng trạng thái | Quality: completeness (`paper_id`/`title` null), uniqueness (`paper_id` duplicate), validity (`summary_chars<100`); Freshness: `age_days > 180` | `data/quality/*.json`, `phase1_report.md`, `corruption_report.md` | Role 3 |
| Corruption/repair | Baseline clean DataFrame | 4 kịch bản có kiểm soát (mục 9); Repair đọc lại raw snapshot, gọi lại `build_clean_dataframe` | `papers_clean_corrupted.*`, `corruption_log.json`, `papers_clean_repaired.*` | Role 4 (corruption) / Role 5 (repair, gọi lại hàm Role 1+2) |
| Orchestration     | Toàn bộ module trên | Lắp `phase1.py::main()` (8 bước) và `corruption_flow.py::main()` (10 bước) đúng thứ tự phụ thuộc | `script/run_phase1.py`, `script/run_corruption_flow.py` chạy end-to-end | Role 5 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (mặc định trong `core/config.py`) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 (`max_results`) |
| Crossref query               | `agentic retrieval augmented generation large language model` |
| Crossref filter              | `from-pub-date:<180 ngày trước thời điểm chạy>,has-abstract:true` |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 days |
| Random seed, nếu có        | Không cấu hình seed cố định — `build_test_set` lấy 10 dòng đầu sau khi `sort_values(by="published")`, nên xác định (deterministic) miễn dataset đầu vào không đổi |

### Lệnh cài đặt

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt: bỏ `uv run`, giữ nguyên `python script/run_phase1.py` / `python script/run_corruption_flow.py`.

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Theo báo cáo Role 4/Role 5: Thành công | 2026-08-06 (giờ chính xác chưa ghi lại) | `baseline_metrics.json` trích trong báo cáo cá nhân Role 4 và Role 5 — **chưa có file JSON gốc kèm theo trong repo** vì `data/` đã bị gitignore |
| Corruption flow   | Theo báo cáo Role 4/Role 5: Thành công | 2026-08-06 (giờ chính xác chưa ghi lại) | `corrupted_metrics.json`, `repaired_metrics.json` trích trong báo cáo cá nhân Role 4 và Role 5 — cùng giới hạn như trên |

> Chưa có thành viên nào re-run cả 2 pipeline trên nhánh `main` đã đồng bộ (commit `4d3eca4`) để tự kiểm chứng độc lập lần nữa. Đây là việc nên làm trước khi nộp chính thức (xem mục 12).

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter                | `query="agentic retrieval augmented generation large language model"`, `filter="from-pub-date:<180 ngày trước>,has-abstract:true"` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được    | 24 (khớp `max_results`) |
| Cơ chế retry/backoff      | Tối đa 5 lần, backoff `2.0 ** attempt` giây khi gặp HTTP 429/503; nếu vẫn lỗi ở lần cuối, thử đọc lại `raw_api_response` đã lưu trước đó thay vì crash cứng |

### Raw và clean schema

| Trường                 | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa                          | Xử lý khi thiếu/sai |
| ------------------------ | --------------- | ------------ | ----------------------------------- | ---------------------- |
| `paper_id`              | `str` (DOI)     | Có         | Khoá xuyên suốt pipeline            | Record không có DOI (và không có `id`) bị loại tại `parse_crossref_payload` |
| `title`                  | `str`           | Có (sau clean) | Tiêu đề bài báo, đã strip tag JATS | Record rỗng title bị loại ở `build_clean_dataframe` |
| `summary`                | `str`           | Có (≥100 ký tự) | Abstract đã strip tag              | Record có summary < 100 ký tự bị loại |
| `authors` / `authors_joined` | `list[str]` / `str` | Không     | Danh sách tác giả, ghép `given family` | Rỗng nếu Crossref không trả `author` |
| `published`              | `str YYYY-MM-DD`| Không      | Ngày xuất bản (ưu tiên `published-print` → `published-online` → `issued` → `created`) | Không parse được → mặc định `1970-01-01` |
| `age_days`                | `int`           | Không      | `run_date - published`, dùng cho freshness | Tính trên `published` đã fallback ở trên |
| `text_for_embedding`     | `str`           | Có         | `Title: [title] \| Authors: [authors_joined] \| Summary: [summary]` | — |

### Quy tắc cleaning

| Quy tắc                                                    | Quality dimension liên quan | Cách xác minh      |
| ------------------------------------------------------------ | ---------------------------- | -------------------- |
| Loại record thiếu `title` hoặc `summary` < 100 ký tự         | Completeness / Validity      | `run_data_quality_checks` — trường `short_summaries`, `title_nulls` |
| Strip tag HTML/JATS (`<jats:p>...</jats:p>`) khỏi title/summary | Validity                     | Đọc `_strip_html`/`_clean_jats_html` trong `cleaning.py`/`crossref.py` |
| Dedupe theo `paper_id` **và** theo `title`                   | Uniqueness                   | `run_data_quality_checks` — trường `paper_id_duplicates` |
| `published` fallback về `1970-01-01` nếu parse lỗi, tính `age_days` | Freshness                    | `build_freshness_report` — `stale_rows`, `is_fresh` |

`text_for_embedding` được Role 2 dựng theo đúng format `Title: [title] | Authors: [authors_joined] | Summary: [summary]`; `paper_id` giữ nguyên giá trị DOI do Role 1 trích xuất — đây là khoá duy nhất được dùng lại ở `test_set.json` (`ground_truth_doc_ids`), `corruption.py` (target record theo `paper_id`) và bước Repair. `age_days` tính bằng `(run_date - published_date).days`, dùng ngưỡng `freshness_threshold_days=180` để xác định `stale_rows`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 (`df.head(10)`) |
| Các `question_type`                    | `factual` (tác giả), `summary`, `factual` (ngày xuất bản) — luân phiên theo `idx % 3` |
| Ground-truth document ID                 | `ground_truth_doc_ids = [paper_id]` — mỗi câu hỏi gắn đúng 1 `paper_id` nguồn |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB — 3 collection: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | `gemini` / `gemini-2.5-flash` (mặc định `core/config.py`) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`, sinh một lần ở bước baseline (`refresh_test_set=False` theo mặc định) |

Test set được giữ nguyên (đóng băng) khi đánh giá cả 3 trạng thái vì mục tiêu của bài lab là đo tác động của **thay đổi dữ liệu**, không phải tác động của việc đổi câu hỏi. Nếu tạo lại `test_set.json` sau mỗi lần thay đổi dữ liệu, chênh lệch giữa các chỉ số baseline/corrupted/repaired có thể đến từ bộ câu hỏi khác nhau chứ không phải từ chính corruption/repair, khiến phép so sánh mất ý nghĩa nhân quả — đây cũng là lý do "quy tắc vàng #4" của nhóm (`phan-cong-5-nguoi.md`) yêu cầu đóng băng `test_set.json` ngay sau khi có `baseline_metrics.json` lần đầu.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có (xác nhận qua commit `9b8e9f2`, dữ liệu thật 24 record) | Không còn trong git sau khi `.gitignore` thêm `data/` |
| Cleaned dataset          | `data/clean/`                        | Theo báo cáo Role 4/5: Có | Không kiểm chứng lại được trên máy biên soạn báo cáo này |
| Embedding manifest/index | `data/embeddings/`                   | Theo báo cáo Role 4/5: Có | — |
| Evaluation set           | `data/eval/`                         | Theo báo cáo Role 4/5: Có (10 câu hỏi) | — |
| Baseline metrics         | `data/results/baseline_metrics.json` | Theo báo cáo Role 4/5: Có | Số liệu trích lại ở mục 10 |
| Quality/freshness        | `data/quality/`                      | Theo báo cáo Role 4/5: Có, PASS/FRESH | — |
| Baseline report          | `data/reports/phase1_report.md`      | Chưa xác nhận độc lập | Cần Role 3/Role 5 đính kèm khi nộp |

### Baseline metrics

| Metric                 |   Giá trị | Diễn giải                             |
| ---------------------- | --------: | --------------------------------------- |
| `retrieval_hit_rate` |    1.0000 | Toàn bộ 10 câu hỏi truy xuất đúng document chứa `ground_truth_doc_ids` |
| `mean_token_f1`      |    0.1059 | F1 theo token giữa câu trả lời agent và `ground_truth` — thấp vì `ground_truth` trong `testset.py` là câu văn dài (nguyên summary hoặc câu mô tả), khó khớp token tuyệt đối dù retrieval đúng |
| `judge_accuracy`     | 0.1000 *(chỉ có trong bản nháp `group_report.md` trước đó trên `main`, không xuất hiện trong báo cáo cá nhân Role 4/Role 5 — cần Role 5 xác nhận lại)* | Tỷ lệ câu trả lời được LLM-judge chấm đúng |
| `mean_judge_score`   | *Chưa có báo cáo nào ghi số này* | — |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline (theo Role 4/5) | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| Completeness | `paper_id`/`title` non-null | 0 dòng null | PASS | `run_data_quality_checks` → `completeness_passed` |
| Uniqueness   | `paper_id` duplicate | 0 dòng trùng | PASS | `uniqueness_passed` |
| Validity     | `summary_chars` ≥ 100 | 0 dòng ngắn hơn 100 ký tự | PASS | `validity_passed` |
| Freshness    | `age_days` ≤ 180 | 0 dòng quá hạn | PASS (FRESH) | `build_freshness_report` → `is_fresh` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned DataFrame (baseline/corrupted/repaired), field `age_days` |
| Ngưỡng freshness         | 180 ngày (`freshness_threshold_days`) |
| Trạng thái baseline      | FRESH (theo báo cáo Role 4/5) |
| Trạng thái corrupted     | STALE — 3 record bị đẩy `published` về `2000-01-01` (`age_days=9500`), vượt xa ngưỡng 180 ngày |
| Trạng thái repaired      | FRESH — Repair đọc lại raw snapshot gốc nên `published` trở lại đúng giá trị thật |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo (theo `src/ingestion/corruption.py`) | Record bị tác động | Quality signal kỳ vọng | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | -------------- |
| Record deletion (`_drop_target_records`) | Xoá 2 `paper_id` đầu tiên trong dataset (trùng `ground_truth_doc_ids`) | 2 | `retrieval_hit_rate` giảm trực tiếp cho các câu hỏi liên quan document bị xoá | Repair đọc lại toàn bộ `crossref_records.json` gốc, record được khôi phục nguyên vẹn |
| Blank summaries (`_blank_summaries`) | Set `summary="N/A"`, `summary_chars=3`, rebuild `text_for_embedding` cho 3 record | 3 | Validity check FAIL (`short_summaries>0`); `mean_token_f1` giảm | Repair build lại `text_for_embedding` từ `summary` gốc qua `build_clean_dataframe` |
| Stale publication dates (`_apply_stale_dates`) | Set `published="2000-01-01"`, `age_days=9500` cho 3 record | 3 | Freshness check FAIL (STALE) | `published` tính lại từ raw snapshot, không phụ thuộc giá trị đã bị sửa |
| Duplicate rows (`_inject_duplicates`) | Nhân đôi 2 record đầu (`pd.concat`) | 2 (thêm 2 dòng trùng) | Uniqueness check FAIL (`paper_id_duplicates>0`) | `build_clean_dataframe` dedupe lại theo `paper_id`/`title` khi build từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Nội dung theo code: `corrupted_at`, `total_original_rows`, `total_corrupted_rows`, và mảng `actions` — mỗi action ghi `type`, `count`, `target_paper_ids`, `impact` dự kiến. Đủ chi tiết để đối chiếu record nào bị tác động bởi kịch bản nào.

Repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy (không chỉ che kết quả lỗi) vì `corruption_flow.py::main()` bước 6 gọi `load_raw_records(settings.paths.raw_records_json)` — đọc lại đúng file raw JSON do Role 1 lưu ở bước ingestion ban đầu, **không** gọi lại Crossref API — rồi chạy lại đúng `build_clean_dataframe` (hàm của Role 2, dùng chung với baseline). Vì vậy repaired dataset được tái tạo bằng chính logic cleaning đã dùng cho baseline, trên cùng một raw snapshot, nên hội tụ lại đúng baseline thay vì chỉ vá riêng các trường bị corrupt.

## 10. So sánh baseline, corrupted và repaired

> Nguồn: báo cáo cá nhân Role 4 (`NguyenDangDuc_2A202601787.md`) và Role 5 (`01051-DoTuanSon.md`), hai nguồn độc lập cho cùng một bộ số. `judge_accuracy`/`mean_judge_score` không có trong hai báo cáo này (xem ghi chú mục 7).

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   1.0000 |    0.8000 |   1.0000 |                   -0.2000 |    100% về baseline | Giảm đúng bằng tỷ lệ 2/10 câu hỏi có `ground_truth_doc_ids` trùng record bị xoá |
| `mean_token_f1`        |   0.1059 |    0.0649 |   0.1059 |                  -0.0410 |    100% về baseline | Phục hồi đúng bằng baseline sau khi repair rebuild `text_for_embedding` từ raw |
| Quality checks pass/fail |     PASS |      FAIL |     PASS |          Fail: uniqueness + validity |            Hồi phục hoàn toàn | FAIL đến từ duplicate `paper_id` + summary rỗng |
| Freshness status         |    FRESH |     STALE |    FRESH |          3 record vượt ngưỡng 180 ngày |            Hồi phục hoàn toàn | STALE đến từ 3 record bị đẩy về năm 2000 |

Hai kết luận nhân quả có bằng chứng artifact đi kèm:

1. **Corruption → suy giảm đo được**: Xoá 2 record trùng `ground_truth_doc_ids` (Role 4) → ChromaDB không còn tài liệu để truy xuất cho các câu hỏi liên quan → `retrieval_hit_rate` giảm từ 1.0000 xuống 0.8000; đồng thời làm rỗng summary của 3 record khác → mất ngữ nghĩa nội dung → `mean_token_f1` giảm từ 0.1059 xuống 0.0649.
2. **Repair từ raw snapshot → phục hồi đầy đủ**: `corruption_flow.py` đọc lại `crossref_records.json` gốc (không gọi lại API) và chạy lại `build_clean_dataframe` → cả `retrieval_hit_rate` và `mean_token_f1` quay về đúng giá trị baseline, Quality chuyển lại PASS, Freshness chuyển lại FRESH — chứng minh corruption là nguyên nhân duy nhất gây suy giảm (không có yếu tố nhiễu khác), và pipeline có khả năng phục hồi hoàn toàn từ nguồn sạch.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Toàn bộ commit code cho Role 2 (`cleaning.py`, `testset.py`) và Role 3 (`quality.py`, `reporting.py`) — cộng thêm một bản `crossref.py`/UI phụ — đều nằm trong một commit duy nhất (`9b5143d "add"`) dưới tài khoản GitHub của Vi Minh Hiển, thay vì tách theo từng owner như ma trận phân công ở `phan-cong-5-nguoi.md` (mục 6) quy định.
- **Nguyên nhân:** Theo xác nhận của nhóm, chỉ máy của Hiển cài đặt được môi trường chạy trong buổi làm việc, nên phần việc của Trần Trung (Role 2) được thực hiện nhưng commit qua máy/tài khoản Hiển; Hiển tự đảm nhiệm Role 3. Nguyên nhân kỹ thuật cụ thể khiến môi trường của các thành viên khác không chạy được (phiên bản Python, thiếu dependency, hay lỗi khác) chưa được ghi lại.
- **Cách xử lý:** Nhóm chấp nhận lệch giữa "người sở hữu vai trò" và "người đứng tên commit" cho buổi làm việc này, ghi rõ trong bảng phân công ở mục 1 để không đánh giá nhầm đóng góp.
- **Cách xác minh:** `git log --all --format='%an %s'` cho thấy toàn bộ thay đổi `cleaning.py`/`testset.py`/`quality.py`/`reporting.py` nằm trong đúng 1 commit của Hiển; không có commit nào khác chỉnh 4 file này.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| `data/` bị thêm vào `.gitignore` sau khi một số file raw đã được commit trước đó (`data/raw/*.json` vẫn còn tracked từ commit `9b8e9f2`, các artifact khác thì không) — kết quả pipeline thật (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, các report `.md`) không nằm trong git ở bất kỳ commit nào | Không ai review được artifact gốc, chỉ có số liệu chép tay trong báo cáo cá nhân — vi phạm tinh thần "kết luận dựa trên artifact thực tế" của `report/README.md` mục 2 | Trước khi nộp: chạy lại `script/run_phase1.py` và `script/run_corruption_flow.py` trên một máy, đính kèm toàn bộ `data/results/*.json` và `data/reports/*.md` dưới dạng release asset hoặc phụ lục nộp cùng báo cáo (không cần bỏ `.gitignore`) |
| Role 2 và Role 3 (Trần Trung, Vi Minh Hiển) chưa có `report/individual_[MSSV].md` riêng | Không đối chiếu được mức hiểu và phần việc thực tế của 2 thành viên này theo đúng mẫu báo cáo | Trung và Hiển hoàn thành `report/<MSSV>_HoTen.md` theo mẫu `report/individual_report.md`, đặc biệt mục 6 (`quy tắc vàng` môi trường) để ghi lại nguyên nhân môi trường không chạy được |
| `judge_accuracy`/`mean_judge_score` không nhất quán giữa các nguồn (chỉ có trong bản nháp `group_report.md` cũ, không có trong báo cáo Role 4/5) | Bảng metrics ở mục 7/10 không đầy đủ, rủi ro sai số nếu dùng số chưa xác nhận | Role 5 chạy lại, đối chiếu trực tiếp với `data/results/baseline_metrics.json` thật rồi cập nhật lại 2 dòng này |
| Chưa có ai re-run cả 2 pipeline trên đúng `main` đã đồng bộ (commit `4d3eca4`) để tự kiểm chứng lại toàn bộ số liệu trong báo cáo này | Số liệu ở mục 7/10 là tổng hợp gián tiếp, chưa phải bằng chứng chạy trực tiếp trên phiên bản code cuối cùng dùng để nộp | Chạy lại 2 script trên `main`, so khớp số liệu mới với bảng ở mục 10 trước khi nộp chính thức |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế — **MSSV của Trần Trung và Vi Minh Hiển còn thiếu.**
- [ ] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp — **chưa re-run trên `main` đã đồng bộ (commit `4d3eca4`).**
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`, không refresh giữa 3 trạng thái).
- [ ] Bảng metrics khớp với các file trong `data/results/` — **chưa có file JSON gốc đối chiếu trực tiếp trong repo.**
- [ ] Quality/freshness conclusions khớp với `data/quality/` — **cùng giới hạn như trên.**
- [ ] Các đường dẫn báo cáo và artifact truy cập được — **`data/reports/*.md` chưa có trong git.**
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng — **còn thiếu Role 2 (Trần Trung) và Role 3 (Vi Minh Hiển).**
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh (đã kiểm tra `.gitignore` có `.env`; không thấy secret trong các file đã đọc).
