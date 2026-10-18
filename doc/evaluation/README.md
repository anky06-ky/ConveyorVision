# ConveyorVision — YOLO26 30-Epoch Training & Evaluation Report

Báo cáo kết quả huấn luyện mô hình thị giác máy tính **YOLO26 Nano** cho hệ thống phát hiện và phân loại sản phẩm đạt chuẩn (`pass`) / phế phẩm (`defect`) trên băng chuyền công nghiệp.

---

## 1. Thông Số Huấn Luyện (Training Setup)

| Thông số | Giá trị |
| :--- | :--- |
| **Kiến trúc mô hình** | **YOLO26 Nano** (`yolo26n.pt` native, End-to-end NMS-free) |
| **Số layer / Tham số** | 260 layers, 2,504,580 parameters, 5.9 GFLOPs |
| **Kích thước file trọng số** | **5.45 MB** (phù hợp triển khai biên Edge/IoT/Embedded) |
| **Phần cứng huấn luyện** | NVIDIA Tesla T4 GPU (Google Colab Runtime) |
| **Thời gian huấn luyện** | **463.2 giây (~7.7 phút)** cho 30 epochs (~15.4 giây/epoch) |
| **Số lượng ảnh** | 2.666 ảnh (Train: 1.692, Val: 533, Test: 441) |
| **Batch size / Image size** | 16 / 640x640 |
| **Optimizer** | AdamW (`lr=0.001667`, `momentum=0.9`) |
| **Trọng số phân loại (`cls`)** | `cls=1.2` (hỗ trợ bù trừ mất cân bằng lớp 10:1) |

---

## 2. Kết Quả Đo Lường & Chỉ Số Hiệu Năng (Performance Metrics)

| Chỉ số | Epoch 1 | Epoch 10 | Epoch 20 | Epoch 30 (Final) |
| :--- | :---: | :---: | :---: | :---: |
| **Precision (Độ chính xác)** | 56.5% | 71.6% | 77.8% | **78.7%** |
| **Recall (Độ nhạy / Bắt trúng)** | 52.3% | 69.3% | 77.7% | **79.3%** |
| **mAP@50** | 56.8% | 73.3% | 80.6% | **82.0%** |
| **mAP@50-95** | 32.6% | 45.6% | 54.2% | **58.0%** |
| **Box Loss (Train / Val)** | 1.410 / 1.333 | 1.396 / 1.307 | 1.234 / 1.216 | **1.091 / 1.097** |
| **Class Loss (Train / Val)** | 12.19 / 5.704 | 3.344 / 2.972 | 2.644 / 2.459 | **1.775 / 2.276** |

---

## 3. Biểu Đồ Trực Quan Hóa (Visual Analytics)

### 3.1. Tiến trình huấn luyện (Loss & Performance Curves)
![Biểu đồ tiến trình huấn luyện](results.png)

### 3.2. Ma trận nhầm lẫn chuẩn hóa (Normalized Confusion Matrix)
![Ma trận nhầm lẫn chuẩn hóa](confusion_matrix_normalized.png)

### 3.3. Đường cong Precision - Recall (PR Curve)
![Đường cong PR](BoxPR_curve.png)

---

## 4. Đánh Giá & Nhận Xét Chuyên Môn

1. **Tốc độ hội tụ và độ ổn định:**
   - Hàm mất mát phân loại (`cls_loss`) giảm liên tục từ `12.19` xuống `1.775` mà không có hiện tượng nổ gradient.
   - Validation loss giảm đều theo train loss, chứng minh mô hình **không bị overfitting** (quá khớp).

2. **Khả năng bắt lỗi trên băng chuyền:**
   - Chỉ số **mAP@50 đạt 82.0%** và **Recall đạt 79.3%** trên tập dữ liệu thực tế có độ phức tạp cao (nhiều góc chiếu, chai móp méo, mất nắp).
   - Mô hình sẵn sàng được tích hợp vào pipeline kiểm định thời gian thực qua camera với tốc độ inference dự kiến **>80 FPS** trên GPU và **>15 FPS** trên CPU.
