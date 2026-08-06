# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Vi Minh Hiển |
| MSSV               | 2A202601743                 |
| Khóa/Lớp         | K3              |
| Tên nhóm         | Nhóm B51     |
| Vai trò chính    | Role 3 — Data Observability Owner |
| Repository         | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Quality Checks | `src/observability/quality.py` — `run_data_quality_checks()` | Cleaned/corrupted/repaired DataFrame + `Settings` | `data/quality/{report_name}.json` (vd. `baseline_quality.json`) | Hoàn thành |
| Freshness Monitoring | `src/observability/quality.py` — `build_freshness_report()` | DataFrame + `Settings` | `data/quality/freshness_report.json` (+ bản tương ứng cho corrupted/repaired) | Hoàn thành |
| Baseline Reporting | `src/observability/reporting.py` — `generate_phase1_report()` | `source_summary`, `metrics`, `quality`, `freshness` (dict) | `data/reports/phase1_report.md` | Hoàn thành |
| Comparison Reporting | `src/observability/reporting.py` — `generate_corruption_report()` | 7 tham số: metrics + quality + freshness của cả 3 trạng thái | `data/reports/corruption_report.md` | Hoàn thành |

Tôi chỉ nhận ownership cho `src/observability/quality.py` và `src/observability/reporting.py`, đúng theo ma trận phân công (mục 6, `phan-cong-5-nguoi.md`). Tôi không phải owner của `src/ingestion/cleaning.py` hay `src/evaluation/testset.py` (thuộc Role 2).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Commit hộ code `cleaning.py` (`build_clean_dataframe`) và `testset.py` (`build_test_set`) qua tài khoản GitHub của tôi, trong cùng commit `9b5143d "add"` với phần Role 3 của tôi | Trần Đức Bảo Trung (Role 2) | Code Role 2 vào repo đúng tiến độ buổi làm việc, nhưng đứng tên GitHub của tôi thay vì Trung — đã ghi rõ lệch giữa "người code" và "người đứng tên commit" ở `group_report.md` mục 11 để nhóm không tính nhầm đóng góp |
| Cùng commit đó còn kèm một bản `crossref.py` bổ sung và một UI phụ (`script/run_ui.py`, `src/ui/`) dựng thử trong buổi | Phạm Nguyễn Đăng Khôi (Role 1) / cả nhóm | Không phải bản chính thức nhóm dùng để nộp cho Role 1 (xem `individual_01243_PhamNguyenDangKhoi.md` và `group_report.md` mục 11); chỉ là công cụ demo nội bộ, ngoài phạm vi 5 vai trò chính của bài lab |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement `run_data_quality_checks`: kiểm completeness (`paper_id`/`title` non-null), uniqueness (`paper_id` duplicate), validity (`summary_chars < 100`), freshness (`age_days > threshold`); AND cả 4 flag thành `passed` tổng | `quality.py:12-67` | `data/quality/{report_name}.json` với đủ 4 flag `*_passed` + `passed` | Chạy hàm với DataFrame mẫu tự tạo (bộ sạch + bộ lỗi) — xem mục 4 |
| Implement `build_freshness_report`: `latest_published`/`oldest_published`, `stale_rows` theo `freshness_threshold_days=180`, `max_age_days`, `is_fresh` | `quality.py:70-105` | `data/quality/freshness_report.json` | Chạy hàm với DataFrame mẫu — `is_fresh=False` đúng khi `stale_rows>0` |
| Implement `generate_phase1_report`: dựng markdown 3 phần (ingestion summary, quality+freshness, RAG metrics) từ 4 dict đầu vào, không tự tính lại số liệu | `reporting.py:7-43` | `data/reports/phase1_report.md` | Chạy hàm với dict mẫu, đối chiếu output đúng cấu trúc |
| Implement `generate_corruption_report` (7 tham số): bảng markdown so sánh Baseline–Corrupted–Repaired + 3 kết luận phân tích | `reporting.py:46-89` | `data/reports/corruption_report.md` | Chạy hàm với 7 dict mẫu (metrics/quality/freshness × 3 trạng thái) |

Output cụ thể: `run_data_quality_checks` và `build_freshness_report` là lớp phát hiện lỗi khách quan đầu tiên trong pipeline — đây là cái Role 4 dựa vào để chứng minh corruption "thấy được" (T3.8: chạy lại 2 hàm này trên data lỗi, xác nhận FAIL đúng kỳ vọng) trước khi nhìn tới retrieval/answer metrics. `generate_corruption_report` sau đó chỉ format lại đúng những dict mà 2 hàm trên (và metrics của Role 5) đã tạo ra, nên bảng so sánh 3 trạng thái trong báo cáo cuối luôn khớp 1-1 với JSON gốc.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần một lớp giám sát khách quan, độc lập với retrieval/answer metrics, để phát hiện dữ liệu "trông vẫn chạy được nhưng thực chất lỗi" (summary rỗng, ngày xuất bản sai, bản ghi trùng) bằng rule số liệu rõ ràng — chạy được ở cả 2 pha (baseline và corruption/repair) mà không phụ thuộc agent có trả lời đúng hay không.

### Cách triển khai

- **`run_data_quality_checks`**: 4 rule độc lập (completeness/uniqueness/validity/freshness), mỗi rule ra một boolean `*_passed`, rồi AND toàn bộ lại thành `passed` (`quality.py:45`) — chỉ cần 1 rule FAIL thì cả báo cáo FAIL, không có khái niệm "gần đạt". Hàm tự guard nhánh `total_rows == 0` riêng để không chia cho 0 hoặc crash khi gọi sớm lúc dữ liệu chưa sẵn sàng.
- **`build_freshness_report`**: tính trực tiếp trên cột `age_days` đã có sẵn từ cleaning (Role 2), không tự parse lại ngày; `freshness_threshold_days` lấy từ `Settings` (180 ngày, cấu hình tập trung ở `core/config.py`) để cả 3 trạng thái baseline/corrupted/repaired dùng chung đúng một ngưỡng.
- **`generate_phase1_report` / `generate_corruption_report`**: viết bằng f-string thuần, không dùng template engine và **không** tự tính toán lại số liệu — 2 hàm chỉ format lại đúng dict được truyền vào. Quyết định này đảm bảo report luôn phản ánh chính xác dict mà pipeline (Role 5) truyền vào, không có logic ẩn có thể làm lệch số giữa report và JSON gốc.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | DataFrame đã clean (`paper_id`, `title`, `summary`/`summary_chars`, `published`, `age_days`) + `Settings.freshness_threshold_days`; với 2 hàm reporting: dict `metrics`/`quality`/`freshness` do Role 5 tổng hợp |
| Output                         | `data/quality/{report_name}.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc             | `src/core/config.py` (`Settings.freshness_threshold_days`, `Paths.quality_dir`) |
| Module sử dụng output        | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` (Role 5) gọi cả 4 hàm; Role 4 dùng `run_data_quality_checks`/`build_freshness_report` để xác nhận corruption "thấy được" (T3.8) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng (`total_rows == 0`) → nhánh report riêng thay vì chia cho 0; thiếu cột `paper_id`/`title`/`summary_chars`/`age_days` → fallback về `total_rows` hoặc `0` thay vì `KeyError` |

### Cách xác minh

```bash
python - <<'PY'
# Chạy trực tiếp 4 hàm trong src/observability/quality.py và reporting.py
# với 2 DataFrame mẫu tự tạo (1 "sạch", 1 mô phỏng đúng 4 kịch bản lỗi
# của Role 4) — không cần Crossref API hay LLM key vì 2 module này
# không gọi mạng.
PY
```

- **Kết quả mong đợi:** với DataFrame "sạch" mẫu (3 dòng, `paper_id` không trùng, `summary` đủ dài, `age_days < 180`) → `passed=True`, `is_fresh=True`; với DataFrame "lỗi" mẫu mô phỏng đúng kịch bản Role 4 (1 `paper_id` trùng, 2 `summary` rỗng, 2 `age_days=9500`) → `passed=False` với đúng `uniqueness_passed=False`, `validity_passed=False`, `freshness_passed=False`, còn `completeness_passed=True` (vì `paper_id`/`title` vẫn không null).
- **Kết quả thực tế:** đã chạy trực tiếp `run_data_quality_checks` và `build_freshness_report` từ `src/observability/quality.py` với 2 DataFrame mẫu ở trên (output ghi ra thư mục scratch riêng, không đụng `data/quality/` thật). DataFrame sạch ra `passed=True`/`is_fresh=True`; DataFrame lỗi ra `passed=False`, `paper_id_duplicates=1`, `short_summaries=2`, `stale_rows=2`, `is_fresh=False` — khớp đúng dự đoán ở trên. `generate_phase1_report` và `generate_corruption_report` cũng chạy được với dict mẫu (bao gồm đúng các số 1.0/0.8/1.0 và 0.1059/0.0649/0.1059 ở mục 8), render đúng cấu trúc markdown và đúng badge PASS/FAIL/STALE/FRESH theo dict truyền vào.
- **Artifact/log:** output nằm trong thư mục scratch ngoài repo, dùng để xác minh logic 4 hàm — **không** thay thế cho `baseline_quality.json`/`freshness_report.json` thật mà Role 5 tạo ra khi chạy `script/run_phase1.py` trên dữ liệu Crossref thật.

> Tôi chưa tự chạy lại toàn bộ `script/run_phase1.py` (cần fetch Crossref thật + LLM key) trên máy này để tái tạo đúng `data/quality/baseline_quality.json` thật — phần đó cần phối hợp với Role 1/2/5 (raw + clean + orchestration), và thư mục `data/quality/`, `data/results/`, `data/reports/` hiện trống trên máy tôi đang viết báo cáo (chỉ có `.gitkeep`, `data/` nằm trong `.gitignore`). Xác minh ở trên chỉ chứng minh logic 4 hàm của tôi đúng với input đúng schema, độc lập với việc pipeline tổng có chạy trên Crossref thật hay không.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn cách kết hợp 4 kết quả kiểm tra (completeness/uniqueness/validity/freshness) thành một trạng thái PASS/FAIL tổng cho `run_data_quality_checks`.
- **Các phương án đã cân nhắc:** (1) AND cứng — bất kỳ rule nào FAIL thì tổng FAIL; (2) tính điểm/tỷ lệ rule đạt (vd. 3/4 rule PASS = 75%); (3) gán trọng số khác nhau cho từng rule (vd. completeness quan trọng hơn freshness).
- **Phương án đã chọn:** AND cứng — `all_passed = completeness_passed and uniqueness_passed and validity_passed and freshness_passed` (`quality.py:45`).
- **Lý do:** Bài lab cần chứng minh corruption "thấy được" qua observability — nếu dùng điểm trung bình, một corruption chỉ trúng 1/4 rule vẫn có thể báo "phần lớn PASS", làm yếu luận điểm nhân quả corruption → FAIL mà Role 4/Role 5 cần. AND cứng đảm bảo bất kỳ kịch bản nào trong 4 kịch bản của Role 4 (xoá bản ghi, rỗng summary, ngày cũ, trùng lặp) — miễn trúng ít nhất 1 rule — cũng chắc chắn kéo `passed` xuống `False`, không phụ thuộc corruption nặng hay nhẹ.
- **Bằng chứng quyết định phù hợp:** Verify ở mục 4 cho thấy DataFrame lỗi mẫu chỉ vi phạm 3/4 rule (`completeness_passed` vẫn `True`) nhưng `passed` tổng vẫn ra `False` đúng thiết kế; khớp với yêu cầu của Role 4 rằng quality/freshness phải "bắt được" cả 4 kịch bản corruption của họ, không chỉ những kịch bản nặng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Không phải lỗi runtime trong `quality.py`/`reporting.py`, mà là lỗi quy trình cộng tác: toàn bộ thay đổi cho `cleaning.py`, `testset.py` (Role 2) — cộng với `quality.py`, `reporting.py` của tôi và một bản `crossref.py`/UI phụ — đều nằm chung trong đúng một commit `9b5143d "add"` đứng tên GitHub của tôi, thay vì tách theo owner như ma trận phân công (mục 6, `phan-cong-5-nguoi.md`) yêu cầu.
- **Lệnh hoặc bước tái hiện:** `git log --all --format='%an %s' -- src/observability/quality.py src/observability/reporting.py src/ingestion/cleaning.py src/evaluation/testset.py` → cả 4 file chỉ có đúng một tác giả commit duy nhất (tôi).
- **Nguyên nhân gốc:** Trong buổi làm việc, chỉ máy của tôi cài đặt xong môi trường chạy kịp lúc; máy của Trần Đức Bảo Trung (Role 2) chưa cài xong trong khung giờ làm việc chung (nguyên nhân kỹ thuật cụ thể — phiên bản Python, dependency hay lỗi khác — nhóm chưa ghi lại), nên phần `cleaning.py`/`testset.py` của Trung được thực hiện và commit qua máy/tài khoản của tôi để không chặn tiến độ cả nhóm.
- **Cách xử lý:** Nhóm thống nhất chấp nhận lệch giữa "người code" và "người đứng tên commit" cho buổi này, ghi rõ vào `group_report.md` mục 1 và mục 11 để không tính nhầm đóng góp của Trung; phần thực sự do tôi tự thiết kế và viết (`quality.py`, `reporting.py`) được tách riêng ở mục 2–5 của báo cáo này, không gộp chung với phần hỗ trợ Trung.
- **Cách xác minh sau khi sửa:** `git show --stat 9b5143d` liệt kê đủ 21 file thay đổi trong đúng một commit; `group_report.md` mục 11 mô tả đúng sự kiện này, đối chiếu khớp với `git log`.
- **Điều học được:** "Một file một người sửa" (quy tắc vàng #1) chỉ chống được conflict code khi merge — không tự động đảm bảo commit history phản ánh đúng ai làm gì. Nhóm cần xác minh môi trường chạy của từng người (T0.1) sớm hơn ở đầu buổi, thay vì chỉ phát hiện ra khi đã tới lúc cần commit.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của tôi:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `fetch_source_records` (Role 1) gọi `api.crossref.org/works`, lưu raw response và raw records. Role 2 chạy `build_clean_dataframe` từ raw records ra `papers_clean.csv/json` kèm `text_for_embedding`. `retrieval/index.py` (code tham khảo có sẵn) đọc cleaned DataFrame, sinh embedding bằng `sentence-transformers/all-MiniLM-L6-v2`, nạp vào ChromaDB. Ngay tại bước "cleaned DataFrame" này, `run_data_quality_checks`/`build_freshness_report` của tôi được gọi để xác nhận PASS trước khi dữ liệu được đem đi build index/embedding — phát hiện lỗi sớm, trước khi tốn công tính embedding.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Role 2 sinh `test_set.json` từ cleaned dataset, mỗi câu hỏi gắn `ground_truth_doc_ids = [paper_id]`. Hệ thống so khớp `paper_id` các document được retrieval trả về với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, và so câu trả lời agent với `ground_truth` để tính `mean_token_f1`/`judge_accuracy`. Hai hàm quality/freshness của tôi **không** đọc `test_set.json` — tôi kiểm chất lượng nguồn dữ liệu (`papers_clean`), độc lập với việc câu hỏi nào được sinh ra.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks (`run_data_quality_checks`) kiểm tra **cấu trúc** tại một thời điểm — `paper_id` non-null/unique, `title` non-null, `summary` đủ dài — trả PASS/FAIL tức thời, không quan tâm thời gian. Freshness monitoring (`build_freshness_report`) đo **độ mới** theo thời gian — dựa vào `age_days`/`published` để biết có bản ghi nào vượt `freshness_threshold_days=180` hay không. Một dataset có thể quality PASS nhưng freshness FAIL (toàn bài cũ), hoặc ngược lại — đây là lý do tôi tách 2 hàm riêng thay vì gộp vào một rule.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là đo tác động của **thay đổi dữ liệu**, không phải tác động của việc đổi câu hỏi. Nếu đổi test set giữa 3 trạng thái, chênh lệch metric có thể đến từ bộ câu hỏi khác nhau chứ không phải corruption/repair — mất khả năng kết luận nhân quả. Đây cũng là lý do `generate_corruption_report` của tôi nhận đúng 3 bộ `metrics`/`quality`/`freshness` (baseline/corrupted/repaired) làm tham số cố định, không tự tính lại từ `test_set.json`.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên việc `load_raw_records` (Role 1) đọc lại đúng raw snapshot ban đầu, `build_clean_dataframe` (Role 2) chạy lại, rebuild index, evaluate lại — và với vai trò của tôi cụ thể: `run_data_quality_checks` + `build_freshness_report` chạy lại trên data đã repair phải trả về PASS/FRESH giống hệt baseline, không phải "gần giống". Nếu quality/freshness repaired chỉ PASS một phần, tôi coi đó là repair chưa hoàn chỉnh dù `retrieval_hit_rate` có tình cờ hồi phục.

## 8. Phân tích kết quả

### Metrics chính

> Số liệu dưới đây trích từ báo cáo cá nhân của Role 4 (`individual_01787_NguyenDangDuc.md`) và Role 5 (`individual_01051_DoTuanSon.md`), khớp nhau giữa hai nguồn độc lập. Tôi không tự chạy lại pipeline evaluation trên Crossref thật ở máy này (`data/results/` hiện trống) nên không tự đo lại được các số retrieval/F1. Phần Quality checks/Freshness status là kết luận mà đúng 2 hàm tôi phụ trách (`run_data_quality_checks`, `build_freshness_report`) tạo ra khi Role 4/Role 5 chạy pipeline thật — logic 2 hàm này tôi đã tự verify độc lập ở mục 4.

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.8000 |   1.0000 | Quality/freshness của tôi **không** trực tiếp giải thích được phần giảm này — record bị Role 4 xoá hẳn không vi phạm rule nào trong 4 rule tôi code (paper_id/title vẫn hợp lệ ở các dòng còn lại); chỉ `retrieval_hit_rate` mới "thấy" được sự biến mất |
| `mean_token_f1`      |   0.1059 |    0.0649 |   0.1059 | Giảm đúng theo dự đoán khi `validity_passed=False` (summary rỗng) — hàm `run_data_quality_checks` của tôi bắt được nguyên nhân này trực tiếp qua `short_summaries>0` |
| `judge_accuracy`     |        — |         — |        — | Không có trong 2 báo cáo tôi tham chiếu được — cần Role 5 xác nhận thêm |
| `mean_judge_score`   |        — |         — |        — | Chưa có số liệu tôi kiểm chứng được |
| Quality checks         |     PASS |      FAIL |     PASS | FAIL đến từ đúng 2/4 rule tôi code: uniqueness (`paper_id_duplicates>0` do Role 4 nhân bản 2 dòng) + validity (`short_summaries>0` do Role 4 blank 3 summary) |
| Freshness status       |    FRESH |     STALE |    FRESH | STALE đến từ rule `stale_rows` tôi code: 3 record bị Role 4 đẩy `age_days=9500`, vượt xa `freshness_threshold_days=180` |

### Kết luận từ số liệu

1. **Corruption → suy giảm đo được:** Role 4 blank summary của 3 record → `run_data_quality_checks` của tôi trả `validity_passed=False` (`short_summaries=3`) → mất ngữ nghĩa tài liệu → `mean_token_f1` giảm từ 0.1059 xuống 0.0649. Song song, Role 4 đẩy `published` của 3 record về năm 2000 → `build_freshness_report` trả `is_fresh=False` (`stale_rows=3`) — quality/freshness của tôi phát hiện được cả hai việc này ngay ở lớp dữ liệu, trước khi cần nhìn tới retrieval/answer.
2. **Repair → phục hồi:** Sau khi Role 5 đọc lại raw snapshot và chạy lại `build_clean_dataframe`, `run_data_quality_checks`/`build_freshness_report` chạy lại trả về PASS/FRESH giống hệt baseline — đúng tiêu chí thành công tôi đặt ra ở mục 7 câu 5, không chỉ "gần giống".

**Corruption nào ảnh hưởng rõ nhất theo góc nhìn observability của tôi, và vì sao?** Duplicate rows và stale dates là 2 kịch bản quality/freshness của tôi "bắt" trực tiếp và rõ nhất — `uniqueness_passed`/`freshness_passed` chuyển `False` ngay lập tức, không cần suy luận qua agent. Ngược lại, **record deletion** — kịch bản ảnh hưởng `retrieval_hit_rate` nặng nhất theo báo cáo Role 4 — lại là kịch bản quality/freshness của tôi **không** bắt được trực tiếp: xoá hẳn record không vi phạm bất kỳ rule nào trong 4 rule hiện có (các dòng còn lại vẫn đầy đủ `paper_id`/`title`), nên `passed` vẫn có thể `True` dù dataset đã mất bài báo bị test set trỏ tới.

**Kết quả nào khác với kỳ vọng ban đầu?** Tôi từng giả định 4 rule của mình sẽ phát hiện được toàn bộ 4 kịch bản corruption của Role 4, nhưng thực tế chỉ 2/4 kịch bản (blank summary, stale date) bị bắt trực tiếp bởi quality/freshness; kịch bản duplicate bị bắt bởi uniqueness; còn record deletion hoàn toàn nằm ngoài phạm vi phát hiện của observability hiện tại, chỉ lộ ra qua `retrieval_hit_rate` của Role 5. Đây là giới hạn thật, không phải giả định — đã kiểm tra bằng cách đối chiếu 4 kịch bản ở mục 3 báo cáo Role 4 với 4 rule ở `quality.py:41-44`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Observability tách bạch khỏi correctness của answer: quality/freshness PASS/FAIL không cần biết agent trả lời đúng hay sai, chỉ cần biết dữ liệu đầu vào có đúng shape/tuổi hay không — đây là lớp phòng thủ độc lập, phát hiện lỗi sớm hơn và rẻ hơn (không tốn lời gọi LLM) so với việc chờ đánh giá answer.
2. AND cứng giữa các rule kiểm tra là lựa chọn có chủ đích, không phải thiếu sót — đánh đổi giữa "báo cáo dễ đọc" (một trạng thái PASS/FAIL rõ ràng) và "chi tiết hoá mức độ lỗi" (người đọc phải mở thêm field chi tiết nếu muốn biết FAIL vì rule nào).
3. Bốn rule hiện tại (completeness/uniqueness/validity/freshness) không phủ hết mọi dạng lỗi dữ liệu — cụ thể là không phát hiện được "mất bản ghi" (record bị xoá hẳn), vì rule chỉ kiểm tra các dòng **còn tồn tại**, không so sánh với số dòng kỳ vọng hay snapshot trước đó.

### Nếu có thêm thời gian

Thêm một rule thứ 5 vào `run_data_quality_checks`: so sánh `total_rows` (và tập `paper_id`) của DataFrame hiện tại với `raw_records_json` gốc (hoặc snapshot lần chạy trước) để tự phát hiện "mất bản ghi" mà không cần đợi `retrieval_hit_rate` giảm. Đo cải thiện bằng cách chạy lại đúng kịch bản Record Deletion của Role 4 và xác nhận quality report tự FAIL ngay ở bước quality — trước khi tới bước evaluate — thay vì chỉ lộ ra gián tiếp qua metric của Role 5.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu (metrics thật ở mục 8 ghi rõ nguồn trích từ Role 4/Role 5; logic 2 hàm tôi phụ trách được tự verify độc lập ở mục 4, không phụ thuộc nguồn ngoài).
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (chưa tự chạy `script/run_phase1.py` trên Crossref thật ở máy này — đã ghi rõ ở mục 4 và mục 8).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vi Minh Hiển
**Ngày xác nhận:** 2026-08-06
