# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| **Họ và tên** | **Nguyễn Đăng Đức** |
| **MSSV** | **2A202601787** |
| **Khóa/Lớp** | K3 |
| **Tên nhóm** | Nhóm B51 |
| **Vai trò chính** | **Role 4 — Data Corruption & Repair-Validation Owner** |
| **Repository** | `https://github.com/dangkhoi3107/K3_Day10_Data-Pipeline-Data-Observability-B51` |
| **Ngày hoàn thành** | 2026-08-06 |

---

## 2. Vai trò và Phạm vi công việc

### Phần việc sở hữu
* **File duy nhất phụ trách**: [src/ingestion/corruption.py](file:///d:/LAB/K3_Day10_Data-Pipeline-Data-Observability-B51/src/ingestion/corruption.py)
* **Nhiệm vụ chính**: Thiết kế và phát triển engine giả lập dữ liệu lỗi có kiểm soát (**Controlled Data Corruption Engine**), đảm bảo các bản ghi bị làm hỏng trùng khớp với bộ câu hỏi đánh giá (`test_set.json`) để chứng minh tác động trực tiếp của dữ liệu xấu lên chất lượng của RAG Agent.

| Module / Deliverable | File / Hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Corruption Engine** | `src/ingestion/corruption.py` <br> `corrupt_clean_dataframe()` | Baseline Cleaned DataFrame (`papers_clean.csv`) | `data/clean/papers_clean_corrupted.csv`<br>`data/clean/papers_clean_corrupted.json`<br>`data/results/corruption_log.json` | **Hoàn thành 100%** |
| **Observability Verification** | Phối hợp với Role 3 (`quality.py`) | Corrupted DataFrame | Báo cáo kiểm định Quality: **FAIL** & Freshness: **STALE** | **Hoàn thành 100%** |

---

## 3. Chi tiết các kịch bản Data Corruption & Phân tích tác động

Trong `src/ingestion/corruption.py`, tôi đã triển khai 4 kịch bản làm hỏng dữ liệu chuyên sâu và mô-đun hóa thành các hàm helper:

### 1. Kịch bản 1: Record Deletion (`_drop_target_records`)
- **Cách thực hiện**: Nhắm mục tiêu và xóa 2 bài báo có `paper_id` nằm trực tiếp trong bộ câu hỏi đánh giá `test_set.json`.
- **Tác động**: Khiến chỉ số tìm kiếm `retrieval_hit_rate` sụt giảm trực tiếp từ **1.0000** xuống **0.8000**.

### 2. Kịch bản 2: Blank Summaries (`_blank_summaries`)
- **Cách thực hiện**: Đổi `summary` của 3 bài báo thành `"N/A"`, cập nhật `summary_chars = 3` và rebuild lại chuỗi `text_for_embedding`.
- **Tác động**: Mất ngữ nghĩa của tài liệu, khiến điểm `mean_token_f1` giảm mạnh từ **0.1059** xuống **0.0649**. Đồng thời làm kiểm tra **Data Quality Validity Check** báo ❌ **FAIL** (< 100 ký tự).

### 3. Kịch bản 3: Stale Publication Dates (`_apply_stale_dates`)
- **Cách thực hiện**: Sửa ngày xuất bản của 3 bài báo thành ngày quá cũ (`2000-01-01`, số ngày tuổi `age_days = 9500`).
- **Tác động**: Vi phạm kiểm tra tính tươi mới dữ liệu, khiến hệ thống giám sát **Data Freshness Check** báo ❌ **STALE** (> 180 ngày).

### 4. Kịch bản 4: Duplicate Rows (`_inject_duplicates`)
- **Cách thực hiện**: Nhân bản 2 bản ghi trùng lặp trong dataset.
- **Tác động**: Gây lãng phí không gian lưu trữ embedding và làm hệ thống **Data Quality Uniqueness Check** báo ❌ **FAIL** (phát hiện trùng `paper_id`).

---

## 4. Phân tích trọng tâm: Kịch bản nào ảnh hưởng Retrieval nặng nhất?

> [!IMPORTANT]
> **Kết luận phân tích chuyên sâu**:
> Kịch bản **Record Deletion (Xóa bản ghi mục tiêu)** ảnh hưởng nặng nề nhất đến khả năng **Retrieval (`retrieval_hit_rate`)** của hệ thống.
> 
> * **Lý do**: Khi tài liệu bị xóa hoàn toàn khỏi cơ sở dữ liệu thô và Vector Database, thuật toán Vector Search (ChromaDB + MiniLM) không thể truy xuất được thông tin liên quan dưới bất kỳ hình thức nào. Khi tài liệu không có trong context, LLM Agent không thể trả lời đúng, kéo `hit_rate` giảm thẳng về 0 đối với các mẫu câu hỏi đó.
> * **Xếp hạng mức độ ảnh hưởng**:
>   1. **Record Deletion**: Ảnh hưởng nghiêm trọng nhất tới Retrieval Hit Rate (Mất hoàn toàn khả năng tìm kiếm tài liệu).
>   2. **Blank Summary**: Ảnh hưởng nghiêm trọng thứ hai tới Token F1 Score & Answer Accuracy (Tài liệu vẫn được lấy ra nhưng không chứa nội dung để trả lời).
>   3. **Stale Date & Duplicates**: Ảnh hưởng tới tính quan sát (Data Observability & Freshness) và chi phí vận hành, không làm giảm trực tiếp Hit Rate nếu text vẫn còn.

---

## 5. Bảng tổng hợp Metrics 3 Trạng thái

| Metric / Signal | Baseline (Clean) | Corrupted Phase (Sau Corruption) | Repaired Phase (Sau Repair) | Tác động nhận xét |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.8000** 📉 | **1.0000** 📈 | Giảm 20% do kịch bản xóa bản ghi target |
| `mean_token_f1` | **0.1059** | **0.0649** 📉 | **0.1059** 📈 | Giảm gần 40% do rỗng summary & mất thông tin |
| **Data Quality Status** | ✅ **PASS** | ❌ **FAIL** | ✅ **PASS** | Báo lỗi rỗng summary & duplicate rows |
| **Data Freshness Status** | ✅ **FRESH** | ❌ **STALE** | ✅ **FRESH** | Báo lỗi ngày xuất bản quá hạn (> 180 ngày) |

---

## 6. Cam kết cá nhân

- [x] Báo cáo thể hiện đúng 100% công việc và kết quả triển khai code của tôi (`src/ingestion/corruption.py`).
- [x] Tôi có thể giải thích chi tiết cơ chế làm hỏng dữ liệu và tác động của nó tới pipeline RAG.
- [x] Mọi chỉ số đều trùng khớp với artifacts thực tế trong thư mục `data/`.
- [x] Cam kết không chứa API key hay thông tin bảo mật trong repository.
