# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Đức Bảo Trung |
| MSSV               | 2A202601269                 |
| Khóa/Lớp         | K3              |
| Tên nhóm         | Nhóm B51     |
| Vai trò chính    | Role 2 — Cleaning & Evaluation-Set Owner |
| Repository         | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Cleaning & Data Modeling | `src/ingestion/cleaning.py` — `build_clean_dataframe()` | `list[PaperRecord]` (Role 1) + `run_date` | DataFrame trong bộ nhớ → `data/clean/papers_clean.csv`/`.json` | Hoàn thành |
| Frozen Evaluation Set | `src/evaluation/testset.py` — `build_test_set()` | Cleaned DataFrame | `data/eval/test_set.json` (đóng băng sau Checkpoint C3) | Hoàn thành |

Tôi chỉ nhận ownership cho `src/ingestion/cleaning.py` và `src/evaluation/testset.py`, đúng theo ma trận phân công (mục 6, `phan-cong-5-nguoi.md`). Tôi không phải owner của `src/observability/quality.py`/`reporting.py` (thuộc Role 3).

### Việc hỗ trợ ngoài phạm vi chính

Không có việc hỗ trợ module khác nằm ngoài phạm vi Role 2. Điểm cần nêu rõ không phải là tôi làm thêm việc của ai, mà ngược lại: chính phần việc Role 2 của tôi (`build_clean_dataframe`, `build_test_set`) được viết và chạy thử trên máy của Vi Minh Hiển rồi commit qua tài khoản GitHub của bạn ấy (commit `9b5143d "add"`), vì môi trường chạy trên máy tôi chưa cài xong kịp trong buổi làm việc chung — xem chi tiết ở mục 6.

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement `build_clean_dataframe`: strip HTML/JATS (`_strip_html`), loại record thiếu `title` hoặc `summary` < 100 ký tự, parse `published` (fallback `1970-01-01` nếu lỗi), tính `age_days`, ghép `authors_joined`/`categories_joined`, dựng `text_for_embedding`, dedupe theo `paper_id` rồi theo `title`, sort giảm dần theo `published` | `cleaning.py:19-88` (dùng `_strip_html`, `cleaning.py:11-16`) | DataFrame trong bộ nhớ → `data/clean/papers_clean.csv`/`.json` | Chạy hàm với 4 `PaperRecord` mẫu (1 hợp lệ, 1 summary ngắn, 1 trùng `paper_id`, 1 ngày lỗi) — xem mục 4 |
| Implement `build_test_set`: lấy `df.head(10)` (= 10 bài **mới nhất**, vì `df` đã sort giảm dần theo `published`), sinh câu hỏi luân phiên factual(authors)/summary/factual(date) theo `idx % 3`, gắn `ground_truth_doc_ids=[paper_id]` | `testset.py:10-67` | `data/eval/test_set.json` | Chạy hàm trên DataFrame mẫu — xem mục 4 |

Output cụ thể: `build_clean_dataframe` là bước đầu tiên cả nhóm phụ thuộc vào sau Role 1 — Role 3 (`quality.py`), Role 4 (`corruption.py`) và Role 5 (index/embedding) đều đọc trực tiếp `papers_clean.csv`/`.json` do hàm này tạo ra. `build_test_set` tạo ra `test_set.json` — bộ câu hỏi "đóng băng" mà cả 3 trạng thái baseline/corrupted/repaired dùng chung để so sánh có ý nghĩa.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Biến raw records (có thể chứa tag HTML/JATS, ngày tháng không đồng nhất giữa các nguồn, khả năng trùng lặp) thành một DataFrame sạch, đúng contract cột mà `retrieval/index.py::_build_documents` (code tham khảo có sẵn) đòi hỏi — đồng thời tạo một bộ câu hỏi đánh giá cố định, dùng lại được cho cả 3 trạng thái dữ liệu (baseline/corrupted/repaired).

### Cách triển khai

- **`build_clean_dataframe`**: lọc record theo 2 điều kiện cứng — `title` rỗng **hoặc** `summary` (sau `_strip_html`) < 100 ký tự — trước khi đưa vào `rows`. Ngưỡng 100 ký tự này chính là "contract" mà Role 3 dùng lại nguyên trạng trong `run_data_quality_checks` (`short_summaries = summary_chars < 100`), và cũng là ngưỡng mà Role 4 khai thác trực tiếp khi thiết kế kịch bản "blank summary" (set `summary="N/A"`, chỉ 3 ký tự — chắc chắn dưới ngưỡng). Sau khi lọc, dedupe 2 bước: `drop_duplicates(subset=["paper_id"])` rồi `drop_duplicates(subset=["title"])` (`cleaning.py:86`, giữ dòng xuất hiện **đầu tiên**) — phòng trường hợp Crossref trả về 2 DOI khác nhau cho cùng một bài (bản preprint và bản đã xuất bản). Cuối cùng `sort_values(by="published", ascending=False)` — **sắp xếp giảm dần**, bài mới nhất lên đầu `DataFrame`.
- **`build_test_set`**: lấy đúng `df.head(10)` — vì `df` đã được sort giảm dần theo `published` ở bước cleaning, 10 dòng đầu chính là **10 bài mới nhất**, không phải chọn ngẫu nhiên. Đây là chi tiết quan trọng: nó giải thích trực tiếp vì sao kịch bản "Record Deletion" của Role 4 (xoá 2 `paper_id` đầu tiên trong dataset, theo báo cáo của Đức) luôn trúng `ground_truth_doc_ids` — 2 dòng đầu dataset (sau sort giảm dần) gần như chắc chắn nằm trong 10 dòng đầu mà `build_test_set` chọn làm câu hỏi.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `list[PaperRecord]` từ Role 1 (`crossref.py`) + `run_date`; với `build_test_set`: cleaned DataFrame |
| Output                         | `data/clean/papers_clean.csv`/`.json` (cột `paper_id, title, summary, authors_joined, categories_joined, published, age_days, summary_chars, text_for_embedding, ...`); `data/eval/test_set.json` (10 câu hỏi, schema `id/question_type/question/ground_truth/ground_truth_doc_ids`) |
| Module phụ thuộc             | `src/ingestion/crossref.py` (`PaperRecord`) |
| Module sử dụng output        | `retrieval/index.py` (embedding/index), `src/observability/quality.py` (Role 3), `src/ingestion/corruption.py` (Role 4), `src/pipelines/phase1.py`/`corruption_flow.py` (Role 5) |
| Điều kiện lỗi cần xử lý | `title` rỗng hoặc `summary` quá ngắn → loại record; `published` không parse được (`ValueError`/`TypeError`) → fallback `1970-01-01` thay vì crash; `records` rỗng → trả `pd.DataFrame()` rỗng thay vì lỗi; `df` rỗng khi gọi `build_test_set` → `raise ValueError` rõ ràng thay vì lỗi mập mờ khi `.head(10)` trên DataFrame rỗng |

### Cách xác minh

```bash
python - <<'PY'
# Chạy trực tiếp build_clean_dataframe (cleaning.py) và build_test_set
# (testset.py) với 4 PaperRecord mẫu tự tạo — không cần Crossref API vì
# 2 hàm này không gọi mạng.
PY
```

- **Kết quả mong đợi:** với 4 record mẫu (1 hợp lệ có tag `<jats:p>`, 1 summary ngắn 10 ký tự, 1 trùng `paper_id` với record hợp lệ, 1 có `published="not-a-date"`) → còn lại 2 dòng sau lọc + dedupe (record summary ngắn bị loại ở bước lọc; record trùng `paper_id` bị gộp ở bước dedupe); tag HTML bị strip khỏi `title`; dòng ngày lỗi có `published="1970-01-01"` và `age_days` tính đúng theo mốc đó. `build_test_set` trên 2 dòng còn lại phải trả 2 câu hỏi, loại `factual`/`summary` luân phiên, `ground_truth_doc_ids` khớp đúng `paper_id` nguồn.
- **Kết quả thực tế:** đã chạy trực tiếp `build_clean_dataframe` và `build_test_set` từ `src/ingestion/cleaning.py`/`src/evaluation/testset.py` với 4 `PaperRecord` mẫu ở trên (không đụng `data/` thật). Kết quả: 4 record vào → 2 dòng ra (`10.1/aaa`, `10.1/ccc`) đúng dự đoán; `<jats:p>` bị strip khỏi title; dòng `10.1/ccc` có `published="1970-01-01"`, `age_days=20671` (tính đến mốc `run_date=2026-08-06` dùng trong test) — khớp công thức `(run_date - 1970-01-01).days`; `text_for_embedding` đúng format `Title: ... | Authors: ... | Summary: ...`. `build_test_set` trả 2 câu hỏi (`q1` loại `factual`, `q2` loại `summary`), `ground_truth_doc_ids` khớp đúng `paper_id` của từng dòng.
- **Artifact/log:** output ghi vào thư mục scratch riêng ngoài repo, dùng để xác minh logic 2 hàm — **không** thay thế cho `data/clean/papers_clean.json`/`data/eval/test_set.json` thật mà Role 5 tạo ra khi chạy `script/run_phase1.py` trên dữ liệu Crossref thật (`data/clean/`, `data/eval/` hiện trống trên máy tôi, chỉ có `.gitkeep`).

> Tôi chưa tự chạy lại toàn bộ `script/run_phase1.py` trên Crossref thật ở máy này (cần Role 1 phối hợp raw data + Role 5 orchestration) — lý do cụ thể ghi ở mục 6. Xác minh ở trên chứng minh logic 2 hàm của tôi đúng với input đúng schema, độc lập với việc pipeline tổng có chạy trên Crossref thật hay không.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn ngưỡng để xác định một `summary` là "hợp lệ" trước khi đưa record vào `text_for_embedding` và index.
- **Các phương án đã cân nhắc:** (1) không lọc gì, giữ nguyên toàn bộ record Role 1 trả về; (2) lọc theo độ dài ký tự với một ngưỡng cụ thể; (3) lọc bằng NLP (vd. yêu cầu summary có tối thiểu N câu hoàn chỉnh, tránh đếm ký tự đơn thuần).
- **Phương án đã chọn:** (2) — ngưỡng **100 ký tự** (`cleaning.py:40`, `len(summary) < 100` → loại).
- **Lý do:** Cần một rule đơn giản, xác định (deterministic), và **dùng lại được nguyên trạng** ở module khác — đúng "quy tắc vàng #2" (không đổi contract giữa buổi) mà nhóm thống nhất. Phương án (3) phức tạp, không deterministic, khó cả nhóm thống nhất trong thời gian ngắn; phương án (1) sẽ đẩy record gần như rỗng nội dung vào embedding, làm nhiễu retrieval mà không cách nào phát hiện được ở lớp dữ liệu.
- **Bằng chứng quyết định phù hợp:** Verify ở mục 4 cho thấy summary "Too short." (10 ký tự) bị loại đúng theo ngưỡng. Quan trọng hơn: Role 3 (`quality.py`) dùng lại đúng field `summary_chars < 100` để tính `short_summaries` trong `run_data_quality_checks`, và Role 4 chủ động khai thác đúng ngưỡng này khi thiết kế kịch bản corruption "blank summary" (set `summary="N/A"`, 3 ký tự). Ba module độc lập (`cleaning.py` của tôi, `quality.py` của Hiển, `corruption.py` của Đức) đang thống nhất dùng chung đúng một định nghĩa "summary hợp lệ" — bằng chứng cụ thể là nhóm không hề phải họp lại để thống nhất lại ngưỡng này giữa buổi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Máy tôi không cài đặt xong môi trường chạy (`uv sync` / `pip install -e .`) trong khung giờ làm việc chung của nhóm, nên không thể tự chạy và tự verify `build_clean_dataframe`/`build_test_set` trên máy mình tại thời điểm đó. Traceback cụ thể không được ghi lại lúc đó.
- **Lệnh hoặc bước tái hiện:** Không có — đây là lỗi cài đặt môi trường, không phải lỗi trong code, nên không có bước tái hiện bằng lệnh Python cụ thể.
- **Nguyên nhân gốc:** Chưa xác định. Nhóm chưa ghi lại nguyên nhân kỹ thuật cụ thể (phiên bản Python không khớp, thiếu dependency hệ thống, hay lỗi mạng khi cài) khiến việc cài đặt trên máy tôi thất bại trong buổi làm việc (xem `group_report.md` mục 11).
- **Cách xử lý (workaround tạm thời):** Phần code Role 2 (`build_clean_dataframe`, `build_test_set`) được viết và chạy thử trên máy của Vi Minh Hiển, commit qua tài khoản GitHub của bạn ấy (commit `9b5143d "add"`) để không chặn tiến độ chung của nhóm. Nhóm đã thống nhất ghi rõ điều này ở `group_report.md` mục 1 và mục 11 để không tính nhầm đóng góp.
- **Cách xác minh sau khi sửa:** `git log --all --format='%an %s' -- src/ingestion/cleaning.py src/evaluation/testset.py` cho thấy cả 2 file chỉ có đúng một tác giả commit (Vi Minh Hiển) — khớp với mô tả sự việc ở trên và với `group_report.md` mục 11.
- **Nếu chưa xử lý xong:**
  - **Phạm vi bị ảnh hưởng:** Chỉ môi trường phát triển cá nhân trên máy tôi — không ảnh hưởng đến code đã merge vào `main` (đã chạy được, không còn `TODO(student)`/`NotImplementedError` trong `cleaning.py`/`testset.py`).
  - **Những gì đã loại trừ:** Chưa loại trừ được giả thuyết cụ thể nào (phiên bản Python, dependency, mạng) vì chưa có traceback được ghi lại từ buổi làm việc đó.
  - **Bước tiếp theo:** Cài lại môi trường theo đúng hướng dẫn (`uv sync` hoặc `pip install -e .`), chạy `uv run python script/run_phase1.py` trên máy mình, đối chiếu `data/clean/papers_clean.json` và `data/eval/test_set.json` tự tạo ra với số liệu đã có trong báo cáo Role 4/Role 5, để tự xác nhận `build_clean_dataframe`/`build_test_set` chạy đúng trên máy mình trước khi nộp chính thức.
- **Điều học được:** "Code đã hoàn thành" (đã merge, đã chạy được trên máy người khác) không đồng nghĩa với "tôi tự kiểm chứng được trên máy mình" — hai việc này cần được ghi tách bạch rõ ràng trong báo cáo cá nhân, không gộp chung làm một.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `fetch_source_records` (Role 1) gọi `api.crossref.org/works`, lưu raw response và raw records. Tôi (Role 2) chạy `build_clean_dataframe` từ `list[PaperRecord]` ra `papers_clean.csv`/`.json`, kèm cột `text_for_embedding`. `retrieval/index.py` (code tham khảo có sẵn) đọc cleaned DataFrame, sinh embedding bằng `sentence-transformers/all-MiniLM-L6-v2`, nạp vào ChromaDB.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `build_test_set` của tôi lấy `df.head(10)` (10 bài mới nhất, vì `df` đã sort giảm dần theo `published`), sinh câu hỏi luân phiên 3 loại theo `idx % 3`, gắn `ground_truth_doc_ids = [paper_id]` cho từng câu. Hệ thống so khớp `paper_id` các document được retrieval trả về với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, và so câu trả lời agent với `ground_truth` để tính `mean_token_f1`/`judge_accuracy`.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks (Role 3) kiểm tra cấu trúc dữ liệu tại một thời điểm — bao gồm đúng ngưỡng `summary_chars < 100` mà tôi dùng để lọc record ở `build_clean_dataframe`. Freshness monitoring đo độ mới theo `age_days`, cũng là cột tôi tính trong `build_clean_dataframe`. Cả hai đều đọc trực tiếp output của tôi, nhưng đo hai khía cạnh khác nhau: một đo "đúng cấu trúc", một đo "còn mới hay không".
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là đo tác động của **thay đổi dữ liệu**, không phải tác động của việc đổi câu hỏi. `test_set.json` do tôi tạo ra một lần duy nhất ở bước baseline rồi đóng băng — nếu tạo lại sau mỗi lần dữ liệu thay đổi, `build_test_set` có thể chọn ra 10 dòng khác (vì `df.head(10)` phụ thuộc thứ tự sort, mà corruption/repair có thể làm thay đổi thứ tự này), khiến phép so sánh mất ý nghĩa nhân quả.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Với vai trò của tôi cụ thể: `build_clean_dataframe` phải là hàm **idempotent** — chạy lại trên đúng raw snapshot ban đầu (do `load_raw_records` của Role 1 đọc lại, không gọi API) phải cho ra kết quả giống hệt lần chạy baseline (cùng số dòng, cùng `paper_id`, cùng `text_for_embedding`). Nếu repaired dataset khác baseline dù dùng cùng raw snapshot, đó là dấu hiệu `build_clean_dataframe` có phần không tất định (non-deterministic) cần xem lại.

## 8. Phân tích kết quả

### Metrics chính

> Số liệu dưới đây trích từ báo cáo cá nhân của Role 4 (`individual_01787_NguyenDangDuc.md`) và Role 5 (`individual_01051_DoTuanSon.md`), khớp nhau giữa hai nguồn độc lập. Tôi không tự chạy lại pipeline evaluation trên Crossref thật ở máy này (`data/results/` hiện trống) nên không tự đo lại được các số này.

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.8000 |   1.0000 | Theo báo cáo Đức, corruption xoá đúng "2 `paper_id` đầu tiên trong dataset" — vì `build_clean_dataframe` của tôi sort giảm dần theo `published`, 2 dòng đầu chính là 2 bài mới nhất, và cũng nằm trong `df.head(10)` mà `build_test_set` của tôi chọn làm câu hỏi — đây là lý do corruption "trúng" `ground_truth_doc_ids` một cách gần như chắc chắn, không phải ngẫu nhiên |
| `mean_token_f1`      |   0.1059 |    0.0649 |   0.1059 | Giảm khi Role 4 blank summary — đúng cơ chế: `text_for_embedding` của tôi ghép trực tiếp `summary` vào chuỗi, nên summary rỗng kéo theo `text_for_embedding` gần như vô nghĩa |
| `judge_accuracy`     |        — |         — |        — | Không có trong 2 báo cáo tôi tham chiếu được |
| `mean_judge_score`   |        — |         — |        — | Chưa có số liệu tôi kiểm chứng được |
| Quality checks         |     PASS |      FAIL |     PASS | FAIL từ `short_summaries`/`paper_id_duplicates` — cả hai field này tính trực tiếp trên output của `build_clean_dataframe` |
| Freshness status       |    FRESH |     STALE |    FRESH | STALE từ `age_days` — cột tôi tính trong `build_clean_dataframe`, dùng lại nguyên trạng bởi `build_freshness_report` của Role 3 |

### Kết luận từ số liệu

1. **Corruption → suy giảm đo được:** Role 4 xoá 2 `paper_id` đầu dataset (theo thứ tự sort giảm dần mà `build_clean_dataframe` của tôi tạo ra) → các `paper_id` này luôn nằm trong `ground_truth_doc_ids` (vì cùng nằm trong `df.head(10)` mà `build_test_set` chọn) → `retrieval_hit_rate` giảm đo được (1.0000 → 0.8000). Đây là hệ quả trực tiếp của cách tôi thiết kế `build_test_set` chọn mẫu theo thứ tự thay vì ngẫu nhiên — dễ dự đoán, nhưng cũng dễ bị "trúng" bởi corruption nhắm vào đầu dataset.
2. **Repair → phục hồi:** Sau khi Role 5 đọc lại raw snapshot và gọi lại đúng `build_clean_dataframe`, `retrieval_hit_rate` và `mean_token_f1` quay về đúng baseline — bằng chứng cho thấy hàm của tôi là idempotent như kỳ vọng ở mục 7 câu 5.

**Corruption nào ảnh hưởng rõ nhất theo góc nhìn Role 2, và vì sao?** Record deletion, vì nó khai thác trực tiếp cách tôi thiết kế `build_test_set` (chọn mẫu theo thứ tự `head(10)` sau sort, không phải random) — nếu `build_test_set` chọn mẫu ngẫu nhiên thay vì lấy 10 dòng đầu, kịch bản "xoá 2 `paper_id` đầu tiên" của Role 4 sẽ không còn chắc chắn trúng `ground_truth_doc_ids`.

**Kết quả nào khác với kỳ vọng ban đầu?** Tôi ban đầu nghĩ việc `build_test_set` chọn 10 dòng đầu (thay vì random) chỉ là chi tiết vô hại để kết quả deterministic; thực tế nó tạo ra một liên kết ngầm giữa thứ tự sort ở `cleaning.py` và việc corruption "chắc chắn trúng" test set ở `corruption.py` — hai module tưởng độc lập lại khoá chặt với nhau qua thứ tự dòng của DataFrame.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một ngưỡng đơn giản, deterministic (100 ký tự cho `summary`) dễ để nhiều module khác dùng lại đúng — miễn cả nhóm thống nhất một lần và không đổi giữa buổi (quy tắc vàng #2).
2. Thứ tự sort ở bước cleaning — tưởng chừng là chi tiết nhỏ — quyết định trực tiếp bộ câu hỏi nào được `build_test_set` chọn, và qua đó quyết định corruption nào "chắc chắn trúng" test set. Hai module tưởng độc lập (cleaning, testset) thực ra khoá chặt với nhau qua thứ tự dòng DataFrame.
3. "Code đã merge và chạy được" khác với "tôi tự chạy và kiểm chứng được trên máy mình" — bài học trực tiếp từ blocker môi trường ở mục 6, không phải điều tôi biết trước khi gặp phải.

### Nếu có thêm thời gian

Thêm lựa chọn chọn mẫu ngẫu nhiên có seed cố định (`df.sample(10, random_state=...)`) thay cho `df.head(10)`, để `build_test_set` không phụ thuộc thứ tự sort của `build_clean_dataframe` — vẫn giữ tính deterministic (nhờ seed) nhưng giảm rủi ro corruption luôn "trúng" chỉ vì nhắm vào đầu dataset. Đo cải thiện bằng cách chạy lại kịch bản Record Deletion của Role 4 trên cả 2 cách chọn mẫu (head vs. random-seeded) và so sánh xác suất `paper_id` bị xoá rơi vào `ground_truth_doc_ids`.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu (metrics thật ở mục 8 ghi rõ nguồn trích từ Role 4/Role 5; logic 2 hàm tôi phụ trách được tự verify độc lập ở mục 4).
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (chưa tự chạy `script/run_phase1.py` trên Crossref thật ở máy này — lý do ghi rõ ở mục 6).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Đức Bảo Trung
**Ngày xác nhận:** 2026-08-06
