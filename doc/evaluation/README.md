# ConveyorVision — YOLO26 30-Epoch Training & Evaluation Report

Báo cáo kết quả huấn luyện và đánh giá thực nghiệm mô hình thị giác máy tính **YOLO26 Nano** cho bài toán phân loại sản phẩm đạt chuẩn (`pass`) / phế phẩm (`defect`) trên băng chuyền công nghiệp.

---

## 1. Thông Số Huấn Luyện (Training Setup)

| Thông số | Giá trị |
| :--- | :--- |
| **Kiến trúc mô hình** | **YOLO26 Nano** (`yolo26n.pt` native, End-to-end NMS-free) |
| **Số layer / Tham số** | 260 layers, 2,504,580 parameters, 5.9 GFLOPs |
| **Kích thước file trọng số** | **5.45 MB** (phù hợp triển khai biên Edge/IoT/Embedded) |
| **Môi trường huấn luyện** | Google Colab GPU Runtime (NVIDIA L4/T4) |
| **Thời gian huấn luyện** | **463.2 giây (~7.7 phút)** cho 30 epochs (~15.4 giây/epoch) |
| **Quy mô tập dữ liệu** | 2.666 ảnh (Train: 1.692, Val: 533, Test: 441) |
| **Batch size / Image size** | 16 / 640x640 |
| **Optimizer** | AdamW (`lr=0.001667`, `momentum=0.9`) |
| **Trọng số phân loại (`cls`)** | `cls=1.2` (hỗ trợ bù trừ mất cân bằng lớp 10:1) |

---

## 2. Kết Quả Huấn Luyện Trên Tập Validation (533 ảnh)

Tiến trình đo lường qua các mốc epoch trên tập Validation:

| Chỉ số | Epoch 1 | Epoch 10 | Epoch 20 | Epoch 30 (Final) |
| :--- | :---: | :---: | :---: | :---: |
| **Precision (Độ chính xác)** | 56.5% | 71.6% | 77.8% | **78.7%** |
| **Recall (Độ nhạy / Bắt trúng)** | 52.3% | 69.3% | 77.7% | **79.3%** |
| **mAP@50** | 56.8% | 73.3% | 80.6% | **82.0%** |
| **mAP@50-95** | 32.6% | 45.6% | 54.2% | **58.0%** |
| **Box Loss (Train / Val)** | 1.410 / 1.333 | 1.396 / 1.307 | 1.234 / 1.216 | **1.091 / 1.097** |
| **Class Loss (Train / Val)** | 12.19 / 5.704 | 3.344 / 2.972 | 2.644 / 2.459 | **1.775 / 2.276** |

---

## 3. Kết Quả Đánh Giá Độc Lập Trên Tập Test (441 ảnh, 1.032 Bounding Boxes)

Đánh giá bằng lệnh `python src/conveyorvision/evaluate.py --split test --model models/conveyor_yolo26_30ep_best.pt` trên 441 ảnh kiểm thử hoàn toàn độc lập (chưa từng thấy trong quá trình huấn luyện):

| Lớp (Class) | Số lượng ảnh | Số Bounding Box | Precision | Recall | mAP@50 | mAP@50-95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tất cả (Overall)** | **441** | **1.032** | **78.2%** | **75.7%** | **82.5%** | **61.4%** |
| `pass` (Đạt chuẩn) | 381 | 991 | 79.7% | 66.1% | 78.9% | 51.2% |
| `defect` (Lỗi / Phế phẩm) | 36 | 41 | **76.6%** | **85.4%** | **86.2%** | **71.7%** |

> [!NOTE]
> **Điểm nổi bật:** Trên lớp sản phẩm lỗi (`defect`), mô hình đạt độ nhạy **Recall = 85.4%** và **mAP@50 = 86.2%**. Kết quả này chứng minh tham số `cls=1.2` đã phát huy tác dụng tối ưu, giảm thiểu tối đa hiện tượng bỏ sót phế phẩm (False Negative) trên băng chuyền.

---

## 4. Đo Lường Thực Nghiệm Hiệu Năng & Tốc Độ (Inference Benchmark)

* **Thiết bị đo lường thực tế (Empirical):** Intel Core i7-8565U CPU @ 1.80GHz (môi trường laptop văn phòng, không GPU).
  - Preprocess: **3.1 ms**
  - Inference: **125.9 ms**
  - Postprocess: **2.4 ms**
  - **Tốc độ thực tế đo được trên CPU:** **~7.9 FPS** (đủ đáp ứng cho các băng chuyền tốc độ chậm hoặc thiết bị kiểm tra tĩnh).
* **Tốc độ ước tính trên GPU công nghiệp:** Dự kiến **>80 FPS** trên NVIDIA Tesla T4 / RTX 3060 / Jetson Orin Nano, đảm bảo kiểm định thời gian thực mượt mà cho dây chuyền tốc độ cao.

---

## 5. Biểu Đồ Trực Quan Hóa (Visual Analytics)

### 5.1. Tiến trình huấn luyện (Loss & Performance Curves)
![Biểu đồ tiến trình huấn luyện](results.png)

### 5.2. Ma trận nhầm lẫn (Confusion Matrix)
| Tập Validation (533 ảnh) | Tập Test Độc Lập (441 ảnh) |
| :---: | :---: |
| ![Val CM](confusion_matrix_normalized.png) | ![Test CM](test_confusion_matrix_normalized.png) |

### 5.3. Đường cong Precision - Recall (PR Curve)
| Tập Validation | Tập Test Độc Lập |
| :---: | :---: |
| ![Val PR](BoxPR_curve.png) | ![Test PR](test_BoxPR_curve.png) |

---

## 6. Đánh Giá Tổng Quan

1. **Khả năng tổng quát hóa (Generalization):** Chỉ số mAP@50 trên tập Test đạt **82.5%** (cao hơn cả tập Validation 82.0%), cho thấy mô hình học đúng đặc trưng cốt lõi của chai đạt và lỗi, không bị học vẹt hay overfitting.
2. **Sẵn sàng triển khai:** Trọng số `conveyor_yolo26_30ep_best.pt` kết hợp pipeline theo vết ByteTrack trong `inference_conveyor.py` đáp ứng đầy đủ yêu cầu kiểm tra và thống kê sản lượng theo thời gian thực.
