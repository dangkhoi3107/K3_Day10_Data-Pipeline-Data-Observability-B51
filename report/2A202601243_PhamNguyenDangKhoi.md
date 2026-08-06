# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phạm Nguyễn Đăng Khôi |
| MSSV               | 2A202601243                 |
| Khóa/Lớp         | K3              |
| Tên nhóm         | Nhóm B51     |
| Vai trò chính    | Role 1 — Source Ingestion Owner |
| Repository         | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw ingestion từ Crossref | `src/ingestion/crossref.py` — `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | `Settings` (`source_query`, `source_filter`, `max_results=24`) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |

Tôi chỉ nhận ownership cho `src/ingestion/crossref.py`, đúng theo ma trận phân công (mục 6, `phan-cong-5-nguoi.md`). Tôi không phải owner của `src/ingestion/cleaning.py` (thuộc Role 2) và không đưa thay đổi vào file đó trong báo cáo này.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Soạn `report/phan-cong-5-nguoi.md`: chia 12 hàm `TODO(student)` / 8 file thành 5 vai trò zero-conflict, kèm sơ đồ phụ thuộc và lịch trình 210 phút | Cả nhóm | Căn cứ phân công thực tế mà Role 4 (corruption) và Role 5 (integration) trích dẫn đúng "Role 1/4/5" trong báo cáo cá nhân của họ |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement `fetch_source_records`: build params từ `source_query`/`source_filter`/`max_results`, gọi `https://api.crossref.org/works`, retry backoff cho `429`/`503` | `src/ingestion/crossref.py` | `data/raw/crossref_response.json` (245,253 bytes) | File tồn tại trên đĩa, mtime 2026-08-06 12:27 |
| Implement `parse_crossref_payload`: duyệt `payload["message"]["items"]`, chuẩn hoá title/abstract (bỏ tag JATS), ghép author, chọn ngày published theo thứ tự ưu tiên, trích `pdf_url`/`abs_url` | `src/ingestion/crossref.py` | `data/raw/crossref_records.json`: đúng **24 object `PaperRecord`**, khớp `max_results=24` trong `core/config.py` | Đếm số object `paper_id` trong file: 24/24 |
| Implement `load_raw_records`: đọc lại JSON snapshot, map ngược thành `list[PaperRecord]` — dùng cho `REFRESH_SOURCE=false` và bắt buộc dùng lại ở bước Repair | `src/ingestion/crossref.py` | Hàm sẵn sàng cho `corruption_flow.py` (Role 5) | Đọc code: hàm gọi `read_json` + unpack trực tiếp vào `PaperRecord(**item)`, không gọi lại API |

Output cụ thể: `fetch_source_records` đã tạo ra 2 artifact raw trong `data/raw/` với đúng số lượng record cấu hình (24), tất cả record còn lại sau bước lọc `paper_id`/`title`/`summary` rỗng. Đây là input trực tiếp mà Role 2 (`cleaning.py`) và Role 5 (bước Repair trong `corruption_flow.py`) phụ thuộc vào.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Lấy metadata bài báo thật từ Crossref REST API một cách đáng tin cậy (chống lỗi mạng/rate-limit tạm thời), chuẩn hoá thành schema `PaperRecord` nhất quán cho toàn bộ pipeline downstream, và lưu lại snapshot raw để có thể tái sử dụng mà **không cần gọi lại API** — điều kiện bắt buộc cho bước Repair sau này.

### Cách triển khai

- **`fetch_source_records`**: build `params` từ `settings.source_query`, `settings.source_filter`, `settings.max_results`; gọi `GET https://api.crossref.org/works`; nếu status là `429` hoặc `503` thì retry tối đa 4 lần với backoff `2**attempt` giây; sau cùng gọi `raise_for_status()` để lỗi thật không bị nuốt âm thầm. Lưu response thô bằng `write_json` **trước khi** parse, để raw response luôn được giữ lại đúng như Crossref trả về dù bước parse có lỗi.
- **`parse_crossref_payload`**: dùng **DOI làm `paper_id`** (khoá ổn định xuyên suốt pipeline theo "quy tắc vàng #3" cả nhóm thống nhất). Abstract được làm sạch qua `_strip_jats_tags` (regex bỏ tag kiểu `<jats:p>` rồi `normalize_whitespace`). Ngày xuất bản thử lần lượt `published → published-print → published-online → issued` qua `_parse_date_parts`, xử lý được cả trường hợp Crossref chỉ trả `[year]` hoặc `[year, month]` thay vì đủ `[year, month, day]`. Record thiếu `paper_id`/`title`/`summary` bị loại ngay tại bước parse, không đẩy dữ liệu rỗng xuống Role 2.
- **`load_raw_records`**: đọc lại đúng file JSON đã lưu, map ngược thành `PaperRecord` — dùng khi `REFRESH_SOURCE=false` và **bắt buộc** dùng ở bước Repair trong `corruption_flow.py` để đảm bảo dữ liệu phục hồi đến từ cùng một nguồn với baseline, không phụ thuộc vào việc Crossref có trả về đúng tập bài báo cũ hay không tại thời điểm repair.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings.source_query`, `Settings.source_filter` (`from-pub-date:<180 ngày trước>,has-abstract:true`), `Settings.max_results=24` |
| Output                         | `list[PaperRecord]` trong bộ nhớ + `data/raw/crossref_response.json` + `data/raw/crossref_records.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils.normalize_whitespace/read_json/write_json` |
| Module sử dụng output        | `src/ingestion/cleaning.py` (Role 2), `src/pipelines/phase1.py` và bước Repair trong `src/pipelines/corruption_flow.py` (Role 5) |
| Điều kiện lỗi cần xử lý | Crossref trả `429`/`503` → retry backoff rồi mới raise; item thiếu DOI/title/abstract → loại khỏi kết quả parse; `date-parts` thiếu tháng/ngày → mặc định về ngày 1 trong tháng/năm đó thay vì crash |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** `data/raw/crossref_response.json` và `data/raw/crossref_records.json` xuất hiện, số record trong `crossref_records.json` lớn hơn 0 và không vượt quá `max_results`.
- **Kết quả thực tế:** Cả hai file tồn tại trên máy (`crossref_response.json` 245,253 bytes, `crossref_records.json` 59,390 bytes chứa đúng 24 record), mtime 2026-08-06 12:27. Toàn bộ 24 record đều có `paper_id` (DOI) không rỗng.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json` — chỉ chứa metadata công khai của bài báo (title, abstract, author, DOI, URL), không có secret.

> Tôi chưa tự chạy lại toàn bộ `script/run_phase1.py` trên máy này để tạo `baseline_metrics.json` (cần bước cleaning/embedding/evaluation của Role 2/Role 3/Role 5). Phần metrics ở mục 8 dưới đây được trích từ báo cáo của Role 4 và Role 5, không phải số tôi tự tạo ra.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn field nào làm `paper_id` — khoá tra cứu tài liệu xuyên suốt ingestion, cleaning, evaluation, corruption và repair.
- **Các phương án đã cân nhắc:** (1) dùng DOI của Crossref; (2) tự sinh ID tăng dần theo thứ tự trả về từ API; (3) dùng `title` đã chuẩn hoá làm khoá.
- **Phương án đã chọn:** DOI (`item.get("DOI", "")`).
- **Lý do:** DOI là định danh chuẩn quốc tế, duy nhất và ổn định giữa nhiều lần fetch — không đổi khi thứ tự trả về của API thay đổi (loại (2) không đảm bảo điều này) và không đổi khi title bị chuẩn hoá lại nhẹ giữa các lần chạy (loại (3) không đảm bảo unique). Việc này khớp trực tiếp với "quy tắc vàng #3" mà cả nhóm thống nhất trong `phan-cong-5-nguoi.md`: mọi module tra cứu tài liệu qua `paper_id`, không tra theo title.
- **Bằng chứng quyết định phù hợp:** 24/24 record trong `crossref_records.json` có `paper_id` non-null; theo báo cáo Role 4, corruption engine target đúng `paper_id` nằm trong `ground_truth_doc_ids` của test set — chỉ khả thi vì `paper_id` giữ nguyên giá trị DOI ổn định xuyên suốt các bước.

## 6. Một lỗi hoặc blocker đã xử lý

Trong phạm vi `crossref.py`, tôi không gặp lỗi runtime chặn cứng cần debug — lần fetch được xác minh (24/24 record parse hợp lệ) chạy thành công ngay. Rủi ro chính đã được phòng ngừa trước bằng thiết kế thay vì phải sửa sau khi gặp lỗi:

- **Rủi ro đã biết trước (từ `Guide.md`, mục 7):** Crossref có thể trả `429` (rate limit) hoặc `503` (lỗi tạm thời).
- **Cách phòng ngừa:** `fetch_source_records` retry tối đa 4 lần với backoff `2**attempt` giây khi gặp đúng 2 status code này, rồi mới `raise_for_status()` nếu vẫn lỗi — tránh vừa làm hỏng dữ liệu raw (ghi đè bằng response lỗi) vừa tránh im lặng bỏ qua lỗi thật.
- **Cách xác minh:** Đọc code (`crossref.py`, hàm `fetch_source_records`) và quan sát request thành công không cần retry trong lần chạy đã ghi nhận ở mục 4.
- **Điều học được:** Với external API không kiểm soát được, nên tách rõ "lỗi tạm thời nên retry" (429/503) khỏi "lỗi thật nên raise ngay" (4xx khác, lỗi parse) — retry mù mọi lỗi dễ che giấu bug thật.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `fetch_source_records` gọi `api.crossref.org/works`, lưu response thô, parse thành `list[PaperRecord]`, lưu tiếp raw records. Role 2 đọc `crossref_records.json`, chuẩn hoá qua `build_clean_dataframe` thành `papers_clean.csv/json` kèm cột `text_for_embedding`. `retrieval/index.py` (code tham khảo có sẵn) đọc cleaned dataframe, sinh embedding bằng `sentence-transformers/all-MiniLM-L6-v2` và nạp vào ChromaDB.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Role 2 sinh `test_set.json` từ cleaned dataset, mỗi câu hỏi gắn `ground_truth_doc_ids` là danh sách `paper_id` (DOI) đúng. Khi evaluate, hệ thống so khớp `paper_id` các document được retrieval trả về với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, và so câu trả lời của agent với `ground_truth` để tính `mean_token_f1`/`judge_accuracy`.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks (Role 3, `quality.py`) kiểm tra tính đúng đắn cấu trúc của dataset tại một thời điểm — `paper_id` non-null/unique, `title` non-null, độ dài `summary` — trả PASS/FAIL tức thời. Freshness monitoring đo độ "mới" của dữ liệu theo thời gian — dựa vào `age_days`/`published` để xác định có bản ghi nào vượt `freshness_threshold_days=180` hay không, phản ánh dữ liệu có bị lỗi thời hay không chứ không phải có đúng schema hay không.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là đo tác động của **thay đổi dữ liệu**, không phải tác động của bộ câu hỏi khác nhau. Nếu đổi test set giữa 3 trạng thái, chênh lệch metric có thể đến từ việc câu hỏi khác nhau chứ không phải từ corruption/repair — mất khả năng kết luận nhân quả. Đây cũng là lý do `test_set.json` phải "đóng băng" ngay sau khi có `baseline_metrics.json` lần đầu.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên việc `load_raw_records` đọc lại đúng raw snapshot ban đầu (không gọi lại API), chạy lại `build_clean_dataframe` để tái tạo `papers_clean_repaired.csv/json`, rebuild index, evaluate lại trên cùng test set đã đóng băng, và so `repaired_metrics.json` với `baseline_metrics.json` — repair thành công khi các chỉ số (`retrieval_hit_rate`, `mean_token_f1`, quality/freshness status) quay lại xấp xỉ mức baseline.

## 8. Phân tích kết quả

### Metrics chính

> Số liệu dưới đây trích từ báo cáo cá nhân của Role 4 (`NguyenDangDuc_2A202601787.md`) và Role 5 (`01051-DoTuanSon.md`), khớp nhau giữa hai báo cáo độc lập. Tôi không tự chạy lại pipeline evaluation trên máy này nên không tự kiểm chứng lại được các số này — không phải kết quả tôi tự đo.

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.8000 |   1.0000 | Giảm đúng ở corrupted vì Role 4 xoá record trùng `ground_truth_doc_ids` — chứng minh `paper_id` (DOI) tôi dùng làm khoá tra cứu hoạt động đúng xuyên suốt pipeline |
| `mean_token_f1`      |   0.1059 |    0.0649 |   0.1059 | Phục hồi hoàn toàn sau repair, khớp việc `load_raw_records` không làm mất dữ liệu gốc |
| `judge_accuracy`     |        — |         — |        — | Không có trong 2 báo cáo tôi tham chiếu được — cần Role 5 xác nhận thêm |
| `mean_judge_score`   |        — |         — |        — | Chưa có số liệu tôi kiểm chứng được |
| Quality checks         |     PASS |      FAIL |     PASS | FAIL đến từ summary rỗng + duplicate `paper_id` theo báo cáo Role 4 |
| Freshness status       |    FRESH |     STALE |    FRESH | STALE do Role 4 đẩy `published` về năm 2000 trên 3 record |

### Kết luận từ số liệu

1. Xoá record trùng `paper_id` trong `ground_truth_doc_ids` (Role 4) → tài liệu biến mất khỏi vector index → `retrieval_hit_rate` giảm từ 1.0000 xuống 0.8000. Chuỗi nhân quả này chỉ đo được chính xác vì `paper_id` (DOI) do tôi chọn làm khoá là ổn định và duy nhất — nếu dùng title làm khoá, một thay đổi nhỏ khi re-parse có thể làm sai lệch phép so khớp.
2. Repair đọc lại `crossref_records.json` (không gọi lại API) rồi chạy lại cleaning → `retrieval_hit_rate` và `mean_token_f1` phục hồi đúng bằng baseline. Đây là bằng chứng trực tiếp cho việc giữ raw snapshot làm "nguồn sự thật" (single source of truth) là quyết định đúng ở bước ingestion.

Tôi chưa có đủ artifact tự kiểm chứng (`data/results/*.json` hiện trống trên máy tôi) để tự phân tích sâu hơn phần `judge_accuracy`/`mean_judge_score` — sẽ bổ sung sau khi nhóm thống nhất chạy lại pipeline trên một nhánh chung.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot (`crossref_response.json`/`crossref_records.json`) không chỉ là log — nó là điều kiện bắt buộc để bước Repair tồn tại. Không lưu raw đúng cách thì không có gì để "repair về".
2. Một quyết định nhỏ ở ingestion (chọn DOI làm `paper_id`) quyết định cả pipeline có so sánh được baseline/corrupted/repaired một cách có ý nghĩa hay không — lỗi contract ở đầu vào lan xuống toàn bộ evaluation phía sau.
3. Dữ liệu xấu (record bị xoá đúng vào tài liệu test set cần) làm giảm trực tiếp và đo được chất lượng RAG agent (`retrieval_hit_rate` giảm 20 điểm phần trăm) — data quality không phải vấn đề lý thuyết.

### Nếu có thêm thời gian

Viết thêm test cho `parse_crossref_payload` với các payload giả lập thiếu `date-parts`, thiếu `author.family`, hoặc `link` không có bản `application/pdf` — hiện các nhánh fallback này chỉ được xác minh gián tiếp qua 24 record thật, chưa có test case cố ý ép vào nhánh lỗi để đảm bảo không crash khi Crossref trả dữ liệu thiếu trường.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu (metrics ở mục 8 được ghi rõ nguồn là từ báo cáo Role 4/Role 5, không phải tôi tự đo).
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (evaluation/embedding chưa tự chạy trên máy này).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Nguyễn Đăng Khôi
**Ngày xác nhận:** 2026-08-06
