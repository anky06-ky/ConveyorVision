# Báo cáo Chuẩn Hóa và Tích Hợp Dữ Liệu ConveyorVision

**Ngày thực hiện:** 15/10/2026  
**Thư mục dự án:** `D:\ConveyorVision`  
**Mục tiêu bài toán:** Phát hiện và phân loại sản phẩm trên băng chuyền thành 2 lớp:
- **Class 0 (`pass`)**: Chai đạt tiêu chuẩn.
- **Class 1 (`defect`)**: Chai lỗi (móp méo, thiếu nắp, nứt vỡ, nhãn lỗi...).

---

## 1. Kết Quả Xử Lý Dữ Liệu Cũ

Trước đây, repo chứa 1.740 ảnh rời rạc ở thư mục root (`train/`, `valid/`, `test/`) với class duy nhất `0: bottle`, chưa nằm đúng trong cấu trúc chuẩn `data/` của đề xuất và có 2 file `data.yaml` bất đồng bộ.

Pipeline `src/conveyorvision/dataset_manager.py` đã thực hiện:
1. **Di chuyển và chuẩn hóa cấu trúc:** Toàn bộ 1.740 ảnh và file nhãn đã được di chuyển vào:
   - `data/images/{train,val,test}`
   - `data/labels/{train,val,test}`
2. **Đồng bộ tiền tố:** Thêm tiền tố `conveyor_` cho toàn bộ ảnh để tránh xung đột tên file khi gộp với các bộ dữ liệu mới.
3. **Remap nhãn:** Chuyển toàn bộ bounding box `bottle` thành class `0: pass`.
4. **Bảo toàn ảnh âm tính (Background / Negative images):** 69 ảnh nhãn rỗng (không chứa chai) được giữ lại nguyên vẹn theo chuẩn YOLO để giúp mô hình tránh bắt nhầm nền băng chuyền.
5. **Thống nhất cấu hình YAML:** Cả `data/data.yaml` và `data.yaml` ở root đều đã được cập nhật thống nhất trỏ về đường dẫn tuyệt đối `D:/ConveyorVision/data` với 2 class `0: pass` và `1: defect`.

---

## 2. Bảng Phân Bố Chi Tiết Theo Nguồn Dữ Liệu (Phục Vụ Thí Nghiệm E5a)

Bảng phân rã chi tiết số lượng ảnh và bounding boxes theo từng tập và nguồn gốc dữ liệu (provenance tracking) phục vụ phân tích ablation / cross-domain generalization trong **thí nghiệm E5a**:

| Nguồn dữ liệu (Source Dataset) | Tiền tố | Tập | Số ảnh | Box Pass (`0`) | Box Defect (`1`) | Nhãn rỗng (Nền) | Tỷ lệ trong tập |
|---|---|---|---:|---:|---:|---:|---:|
| **1. Conveyor Belt gốc**<br>*(anky06/conveyor-belt-eafpe-bgzzm)* | `conveyor_` | **Train**<br>Val<br>Test<br>**Tổng** | 1.044<br>348<br>348<br>**1.740** | 2.605<br>918<br>902<br>**4.425** | 0<br>0<br>0<br>**0** | 46<br>12<br>11<br>**69** | 61.7%<br>65.3%<br>78.9%<br>**65.3%** |
| **2. Bayo Bottle Detection**<br>*(bayo-et081/bottle-detection-qti1t)* | `bayo_` | **Train**<br>Val<br>Test<br>**Tổng** | 494<br>141<br>71<br>**706** | 350<br>115<br>66<br>**531** | 269<br>68<br>33<br>**370** | 92<br>29<br>13<br>**134** | 29.2%<br>26.5%<br>16.1%<br>**26.5%** |
| **3. Bottle Defects**<br>*(anky06/bottle_defects-tpmcq-kijtp)* | `bottle_defect_` | **Train**<br>Val<br>Test<br>**Tổng** | 154<br>44<br>22<br>**220** | 98<br>19<br>23<br>**140** | 115<br>31<br>8<br>**154** | 0<br>0<br>0<br>**0** | 9.1%<br>8.2%<br>5.0%<br>**8.2%** |
| **TỔNG HỢP TOÀN BỘ (MERGED)** | | **Train**<br>**Val**<br>**Test**<br>**TỔNG CỘNG** | **1.692**<br>**533**<br>**441**<br>**2.666** | **3.053**<br>**1.052**<br>**991**<br>**5.096** | **384**<br>**99**<br>**41**<br>**524** | **138**<br>**41**<br>**24**<br>**203** | **63.5%**<br>**20.0%**<br>**16.5%**<br>**100%** |

---

## 3. Đối Chuẩn Tham Chiếu: Roboflow Cloud RF-DETR (Small)

Kết quả huấn luyện trên Roboflow Cloud với bộ dữ liệu `bottle_defects` (220 ảnh) dùng làm mốc so sánh (Baseline Benchmark) cho mô hình YOLO của dự án:

| Mô hình | Tập đánh giá | mAP@50 | Precision | Recall | F1-Score |
|---|---|---:|---:|---:|---:|
| **Roboflow RF-DETR (Small)** | Valid Set (44 ảnh) | **83.9%** | **90.7%** | **83.0%** | **86.7%** |

> Điểm số này là cơ sở đối chứng thực nghiệm xuất sắc để so sánh với mô hình YOLO fine-tune cục bộ trên toàn bộ 2.666 ảnh băng chuyền.

---

## 4. Kế Hoạch Huấn Luyện Pilot (30 Epochs)

- **Số lượng ảnh Train:** 1.692 ảnh
- **Batch size:** 16 $\rightarrow$ Mỗi epoch có $\lceil 1.692 / 16 \rceil = 106$ bước (iterations).
- **Tổng số bước sau 30 epochs:** $106 \times 30 = 3.180$ bước cập nhật trọng số.
- **Phương án đo lường:** Chạy trước 2–3 epochs đầu để đo latency/thời gian trung bình mỗi epoch, từ đó ngoại suy chính xác tổng thời gian hoàn thành 30 epochs trước khi chạy toàn bộ.

---

## 4. Công Cụ Đã Triển Khai Trong Repo

- **`src/conveyorvision/dataset_manager.py`**:
  - `--migrate`: Chuẩn hóa dữ liệu cũ vào `data/`.
  - `--import-dir <path>`: Nhập và remap một thư mục dataset bất kỳ.
  - `--scan-raw`: Tự động tìm kiếm file ZIP trong `raw_datasets/`, giải nén, remap class và gộp vào `data/`.
  - `--audit`: Kiểm toán số lượng ảnh và box thời gian thực.
- **`raw_datasets/`**: Thư mục lưu trữ các bộ dữ liệu gốc đã tải về.
