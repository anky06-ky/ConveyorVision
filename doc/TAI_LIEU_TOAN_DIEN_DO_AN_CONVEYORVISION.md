# TÀI LIỆU KỸ THUẬT TOÀN DIỆN & KIẾN TRÚC HỆ THỐNG
## HỆ THỐNG THỊ GIÁC MÁY TÍNH KIỂM ĐỊNH BĂNG CHUYỀN THỜI GIAN THỰC (CONVEYORVISION 2.0)

---

## THÔNG TIN TỔNG QUAN DỰ ÁN

* **Tên đồ án:** ConveyorVision — Real-time Conveyor Defect Inspection & Multi-Object Sorting System
* **Phiên bản hệ thống:** 2.0.0 Stable (Phát hành: Tháng 10/2026)
* **Lĩnh vực ứng dụng:** Thị giác máy tính công nghiệp (Industrial Computer Vision), Tự động hóa sản xuất (Factory Automation), Đảm bảo chất lượng (Quality Assurance/QC)
* **Kiến trúc cốt lõi:** YOLO26 / YOLOv8 Nano + ByteTrack Multi-object Tracking + Industrial State Machine + FastAPI Asynchronous Backend + Dark Glassmorphism HMI Web Dashboard
* **Tiêu chuẩn thiết kế:** Chuẩn giao diện HMI ISO 9241-210, kiểm toán dữ liệu ISO 9001 / HACCP, mã nguồn mở phân phối dưới giấy phép MIT License

---

## MỤC LỤC CHI TIẾT

1. [Chương 1: Bối Cảnh Công Nghiệp & Bài Toán Kỹ Thuật](#chuong-1)
2. [Chương 2: Kiến Trúc Tổng Thể Hệ Thống](#chuong-2)
3. [Chương 3: Kỹ Thuật Dữ Liệu & Phân Tích Rò Rỉ Cận Trùng (Near-Duplicate Leakage)](#chuong-3)
4. [Chương 4: Mô Hình Thị Giác Sâu YOLO26 / YOLOv8 Nano](#chuong-4)
5. [Chương 5: Thuật Toán Theo Vết ByteTrack & Dự Đoán Chuyển Động](#chuong-5)
6. [Chương 6: Cỗ Máy Trạng Thái & Cơ Chế Phán Quyết Đa Khung Hình (Multi-Frame Voting)](#chuong-6)
7. [Chương 7: Phân Hệ Kiểm Định Đa Vật Thể (Chai & Dị Vật Băng Chuyền)](#chuong-7)
8. [Chương 8: Kỹ Thuật Backend & Tối Ưu Hóa Độ Trễ Thấp (< 50ms)](#chuong-8)
9. [Chương 9: Thiết Kế Giao Diện HMI / Frontend Công Nghiệp](#chuong-9)
10. [Chương 10: Đảm Bảo Chất Lượng, Kiểm Thử Tự Động & CI/CD Pipeline](#chuong-10)
11. [Chương 11: Danh Mục Mã Nguồn & Hướng Dẫn Bảo Trì Hệ Thống](#chuong-11)
12. [Chương 12: Tích Hợp Phần Cứng Ngoại Vi & Định Hướng Triển Khai Thực Địa](#chuong-12)
13. [Phụ lục: Bảng Thuật Ngữ Chuyên Ngành (Glossary)](#phu-luc)

---

<a name="chuong-1"></a>
## CHƯƠNG 1: BỐI CẢNH CÔNG NGHIỆP & BÀI TOÁN KỸ THUẬT

### 1.1. Thực Trạng Trong Dây Chuyền Sản Xuất Đóng Chai Công Nghiệp
Trong các ngành công nghiệp sản xuất nước giải khát, bia rượu, dược phẩm và hóa mỹ phẩm, công đoạn kiểm soát chất lượng (QC) vỏ chai và mức chiết rót là khâu bắt buộc trước khi đóng gói và xuất xưởng. Mỗi dây chuyền băng tải vận hành với tốc độ từ 1.000 đến hơn 10.000 sản phẩm mỗi giờ.

Các khuyết tật ngoại quan phát sinh thường xuyên bao gồm:
1. **Móp méo thân chai (Body Deformity):** Do va đập cơ khí trên băng tải hoặc lỗi phôi nhựa/thủy tinh.
2. **Rách nhãn, lệch nhãn, mất nhãn (Label Defects):** Do trục dán keo hoặc áp lực nhiệt không đồng đều.
3. **Lệch nắp, hở nắp, thiếu nắp (Cap Misalignment/Missing Cap):** Gây rò rỉ chất lỏng và mất vệ sinh an toàn thực phẩm.
4. **Vơi mức nước (Underfill Level):** Sai lệch thể tích đóng gói theo quy chuẩn đo lường.
5. **Nứt vỡ, trầy xước bề mặt:** Tiềm ẩn nguy cơ nổ vỡ khi chịu áp suất gas carbonat.

Bên cạnh lỗi của bản thân sản phẩm đóng chai, trong môi trường sản xuất thực tế còn phát sinh **dị vật / vật thể lạ ngoại lai** rơi vào băng chuyền (như cốc uống nước, vỏ hộp carton, lon nước ngọt, điện thoại di động, công cụ bảo trì). Một hệ thống QC thông minh không chỉ phát hiện phế phẩm chai mà còn phải phân biệt được đâu là sản phẩm mục tiêu và đâu là dị vật ngoài luồng để đưa ra cảnh báo phù hợp.

### 1.2. Hạn Chế Của Các Giải Pháp Hiện Hữu
* **Kiểm định thủ công bằng mắt người:** Công nhân làm việc trong ca kéo dài 8–12 tiếng đối mặt với hiện tượng mỏi mắt, giảm khả năng tập trung sau 20 phút quan sát liên tục, dẫn đến tỷ lệ bỏ sót lỗi (False Negative) lên tới 15–20%. Chi phí nhân sự cao và không thể đáp ứng dây chuyền tốc độ cao.
* **Hệ thống Machine Vision truyền thống (Cognex, Keyence, Omron):** Hoạt động dựa trên thuật toán xử lý ảnh hình thái học cổ điển (edge detection, template matching, thresholding). Các hệ thống này cực kỳ nhạy cảm với điều kiện ánh sáng thay đổi, đòi hỏi phòng che sáng chuyên dụng và có chi phí đầu tư ban đầu rất lớn (từ 15.000$ đến 50.000$ mỗi trạm kiểm định), gây trở ngại lớn cho các nhà máy vừa và nhỏ (SMEs).

### 1.3. Mục Tiêu Kỹ Thuật Của Hệ Thống ConveyorVision
Dự án **ConveyorVision** được định vị là giải pháp Thị giác Máy tính Công nghiệp thông minh dựa trên Deep Learning với các tiêu chí thiết kế vượt trội:
* **Tốc độ thời gian thực (Real-time Pacing):** Đạt tốc độ xử lý 22–25 FPS ngay trên CPU phổ thông không cần GPU đắt đỏ; độ trễ từ camera đến giao diện hiển thị người dùng dưới 50 ms.
* **Độ chính xác cao:** Đạt chỉ số $mAP_{50} \ge 99\%$ và $F_1\text{-score} \ge 0.98$ trong phân loại khuyết tật.
* **Theo vết & Chống đếm trùng tuyệt đối:** Ứng dụng ByteTrack kết hợp cỗ máy trạng thái (FSM) và Multi-frame Voting, đảm bảo mỗi sản phẩm chỉ được đếm một lần duy nhất trong suốt hành trình qua băng tải.
* **Phân loại đa vật thể thông minh:** Hỗ trợ chế độ nhận diện đồng thời Chai lọ đạt/lỗi và các Dị vật ngoại lai trên cùng một luồng quan sát.
* **Chi phí triển khai tối thiểu:** Hoàn toàn chạy được trên PC thông thường, kết nối camera USB hoặc IP camera chuẩn RTSP, giao diện web HMI hiện đại không cần cài đặt phần mềm phụ trợ.

---

<a name="chuong-2"></a>
## CHƯƠNG 2: KIẾN TRÚC TỔNG THỂ HỆ THỐNG

### 2.1. Sơ Đồ Kiến Trúc Phân Lớp 4 Tầng (Layered Architecture)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TẦNG 1: THU NHẬN HÌNH ẢNH (HARDWARE & INGESTION)                 │
│  [USB Webcam 0]       [Camera Công Nghiệp RTSP]      [Video MP4 Thử Nghiệm] [Upload]    │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │ OpenCV VideoCapture (Buffer Size = 1)
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TẦNG 2: NHẬN DIỆN THỊ GIÁC SÂU (AI DEEP LEARNING)                │
│  Ultralytics YOLO26 / YOLOv8 Nano (Anchor-Free Decoupled Head, Resolution 480p / 640p) │
│  Output: Bounding Boxes [x1, y1, x2, y2], Class ID (0: Pass, 1: Defect), Confidence    │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │ Raw Detections List
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                 TẦNG 3: THEO VẾT & PHÁN QUYẾT ĐA KHUNG HÌNH (TRACKING & FSM)            │
│  - ByteTrack (Kalman Filter 8D + Hungarian IoU Matching 2 giai đoạn)                   │
│  - Cơ chế Multi-frame Voting: min_observation_votes >= 3 frames                        │
│  - Cỗ máy trạng thái: INSPECTING ──► DEFECT (Chốt ngay) / PASS (Sau lost buffer=30)     │
│  - Bù trừ nhãn tại chỗ (In-place Correction) & Triệt tiêu đếm trùng                    │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │ State-annotated Frame & Telemetry JSON
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                    TẦNG 4: DỊCH VỤ WEB BACKEND & GIAO DIỆN HMI CÔNG NGHIỆP             │
│  - FastAPI Web Server + Uvicorn Async Engine                                           │
│  - Luồng MJPEG Streaming đồng bộ bằng threading.Condition (< 50ms Latency)             │
│  - WebSocket Telemetry: Đẩy FPS, KPI đếm, trạng thái cờ báo động thời gian thực        │
│  - HMI Single Page Application (Dark Glassmorphism, Web Audio Buzzer, 6 Phân Hệ)       │
│  - Kiểm toán dữ liệu: Xuất tự động CSV, báo cáo kỹ thuật PDF, cẩm nang UI/UX PDF       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Luồng Vận Hành Dữ Liệu Thời Gian Thực (End-to-End Dataflow)
1. **Worker Thread** khởi tạo camera hoặc mở tệp video, đọc khung hình nguyên bản với `cv2.CAP_PROP_BUFFERSIZE = 1` để không bị tích lũy khung hình trễ trong hàng đợi driver.
2. Khung hình được thu nhỏ về độ phân giải suy luận (chuẩn: 480px hoặc 640px) và nạp vào mô hình YOLO26n.
3. Toàn bộ các hộp bao (bounding boxes) cùng điểm tin cậy được chuyển cho bộ theo vết `ByteTrack`. Bộ lọc Kalman dự đoán vị trí của các track ID hiện hữu và thuật toán Hungary tiến hành ghép nối.
4. Cỗ máy trạng thái `State Machine` kiểm tra lịch sử của từng `track_id`:
   * Nếu phát hiện nhãn `defect` với điểm tin cậy cao, chuyển trạng thái track thành `DEFECT`, phát cờ cảnh báo `hazard_alert = True`.
   * Nếu track chỉ thấy `pass` nhưng chưa đủ 3 frames, gán trạng thái tạm thời `INSPECTING`.
   * Khi chai di chuyển ra khỏi tầm quét của camera và biến mất liên tục 30 frames (`lost_track_buffer`), hệ thống chính thức chốt nhãn `PASS`.
5. Worker vẽ lớp đồ họa HUD lên khung hình (Reticles 4 góc, Bounding box phân màu, nhãn định danh `#ID Nhãn Conf`, cờ cảnh báo nhấp nháy đỏ).
6. Khung hình đã vẽ được nén sang định dạng JPEG và kích hoạt biến điều kiện `threading.Condition.notify_all()`.
7. Endpoint `/stream` truyền khung hình JPEG dạng multipart tới trình duyệt; song song đó kết nối WebSocket đẩy dữ liệu số liệu (FPS, tổng Pass, Defect, Other) tới giao diện HMI để cập nhật các ô nhớ tại chỗ (In-place Reactive DOM).

---

<a name="chuong-3"></a>
## CHƯƠNG 3: KỸ THUẬT DỮ LIỆU & PHÂN TÍCH RÒ RỈ CẬN TRÙNG (NEAR-DUPLICATE LEAKAGE)

### 3.1. Phân Phối Tập Dữ Liệu Chuẩn Hóa
Bộ dữ liệu của hệ thống được trích xuất và chuẩn hóa từ tập dữ liệu băng chuyền công nghiệp gồm tổng cộng **2.666 ảnh**, phân chia thành 3 phân tập theo tỷ lệ tiêu chuẩn Machine Learning:
* **Tập Huấn luyện (Train Set):** 1.692 ảnh (~63.5%) — Dùng để tối ưu hóa trọng số mạng nơ-ron qua thuật toán Gradient Descent.
* **Tập Kiểm định (Validation Set):** 533 ảnh (~20.0%) — Dùng để theo dõi hàm mất mát qua từng epoch, tinh chỉnh siêu tham số và áp dụng kỹ thuật dừng sớm (Early Stopping).
* **Tập Kiểm thử (Test Set):** 441 ảnh (~16.5%) — Dùng để đánh giá độc lập năng lực tổng quát hóa của mô hình cuối cùng.

Cấu trúc thư mục được quản lý nhất quán thông qua tệp `data/data.yaml`:
```yaml
path: data
train: images/train
val: images/val
test: images/test

names:
  0: pass
  1: defect
```

### 3.2. Chuẩn Hóa Không Gian Nhãn (Label Mapping & Re-indexing)
Tập dữ liệu gốc từ Roboflow ban đầu chứa nhiều lớp nhãn rời rạc (`good`, `flaw`, `crack`, `label_defect`, `cap_missing`). Script [dataset_manager.py](file:///d:/ConveyorVision/src/conveyorvision/dataset_manager.py) thực hiện việc ánh xạ và chuẩn hóa toàn bộ về 2 lớp nhị phân công nghiệp:
* `Class 0 (pass)`: Chai hoàn hảo, đầy đủ nắp, nhãn ngay ngắn, thân chai nguyên vẹn.
* `Class 1 (defect)`: Mọi dạng khuyết tật (móp méo, nứt vỡ, rách nhãn, thiếu nắp, vơi mức chiết).

### 3.3. Phân Tích Khoa Học Chuyên Sâu: Hiện Tượng Ảnh Cận Trùng (Near-Duplicate Data Leakage)
Trong quá trình kiểm định khoa học của dự án, nhóm kỹ sư đã thực hiện phân tích đối sánh đặc trưng hình ảnh giữa tập Train và tập Test bằng thuật toán **Perceptual Hash (pHash)** và **Structural Similarity Index (SSIM)**:

1. **Phát hiện thực nghiệm:** Tìm thấy **53 đến 54 cặp ảnh** giữa tập Train và tập Test có độ tương đồng cấu trúc thị giác cực kỳ cao ($pHash \le 4$ hoặc $SSIM \ge 0.92$). Đặc biệt, 23 trên tổng số 36 ảnh có nhãn `defect` trong tập Test nằm trong nhóm ứng viên cận trùng này.
2. **Nguyên nhân cốt lõi:** Các hình ảnh ban đầu được trích xuất (frame extraction) từ các đoạn video băng tải quay liên tục với tần số cao (30 FPS). Khi phân chia ngẫu nhiên (random splitting) ở cấp độ ảnh đơn lẻ (image-level split), các khung hình liền kề chỉ cách nhau vài phần mười giây (với góc quay, phông nền và chai giống hệt nhau) đã vô tình bị phân bổ: một khung vào tập Train và một khung vào tập Test.
3. **Ý nghĩa khoa học đối với chỉ số kiểm định:**
   * Điểm số kiểm thử đạt $mAP_{50} = 0.995$ cần được nhìn nhận một cách khách quan là **cận trên lý tưởng (Upper Bound)** trong điều kiện môi trường quan sát cố định.
   * Khi đánh giá Recall của lớp `defect` tại ngưỡng cắt tĩnh $conf = 0.25$, ma trận nhầm lẫn ghi nhận $80.6\%$ do một số khuyết tật nhỏ bị chia ngưỡng; tuy nhiên khi tính toán tích phân toàn dải Precision-Recall ($mAP_{50}$), độ bao phủ đạt $85.4\%$ đến $99.5\%$.
4. **Giải pháp chuẩn hóa dài hạn đã triển khai:**
   * Xây dựng công cụ [video_io.py](file:///d:/ConveyorVision/src/conveyorvision/video_io.py) sinh tệp nhật ký `data/manifest.csv` lưu trữ thông tin: `video_id`, `frame_idx`, `timestamp_s`.
   * Đề xuất phương pháp phân tập theo phiên quay độc lập (**Session-based Split**): Toàn bộ khung hình của cùng một `video_id` chỉ được nằm trọn vẹn trong một phân tập duy nhất (hoặc Train, hoặc Test), triệt tiêu hoàn toàn hiện tượng rò rỉ dữ liệu giữa các frame liền kề.

---

<a name="chuong-4"></a>
## CHƯƠNG 4: MÔ HÌNH THỊ GIÁC SÂU YOLO26 / YOLOV8 NANO

### 4.1. Kiến Trúc Mạng Nơ-ron Tích Chập (Deep CNN Architecture)
Mô hình **YOLO26 Nano** kế thừa và tối ưu hóa từ kiến trúc Ultralytics tiên tiến:
* **Backbone (Mạng xương sống):** Cấu trúc mạng tích chập sâu kết hợp các khối C2f (Cross-Stage Partial with 2 Convolutions) và SPPF (Spatial Pyramid Pooling - Fast). Khối SPPF thực hiện trích xuất và gộp đặc trưng ở các kích thước receptive field khác nhau ($5\times5, 9\times9, 13\times13$) mà không làm tăng kích thước tham số, giúp nhận diện hiệu quả cả các vết nứt nhỏ lẫn biến dạng thân chai lớn.
* **Neck (Cổ mạng):** Cấu trúc PANet (Path Aggregation Network) hai chiều (Top-down và Bottom-up FPN), kết hợp hài hòa đặc trưng ngữ nghĩa mức cao (high-level semantic) và đặc trưng không gian hình học mức thấp (low-level geometric localization).
* **Head (Đầu phân loại & Tọa độ):** Kiến trúc Decoupled Head phân tách hoàn toàn nhánh dự đoán tọa độ hộp bao (Bounding Box Regression) và nhánh dự đoán lớp thực thể (Classification). Cơ chế Anchor-free dự đoán trực tiếp độ lệch tọa độ từ điểm tâm, loại bỏ sự phụ thuộc vào các tỷ lệ hộp neo cố định.

### 4.2. Hàm Tổn Thất Đa Thành Phần (Multi-task Loss Formulation)
Tổng hàm mất mát trong quá trình huấn luyện là sự kết hợp có trọng số của 3 hàm thành phần:

$$\mathcal{L}_{total} = \lambda_{box} \mathcal{L}_{CIoU} + \lambda_{cls} \mathcal{L}_{BCE} + \lambda_{dfl} \mathcal{L}_{DFL}$$

Trong đó:
1. **$\mathcal{L}_{CIoU}$ (Complete Intersection over Union Loss):** Tối ưu hóa tọa độ hộp bao dựa trên diện tích giao cắt, khoảng cách tâm Euclid giữa hộp thực tế và hộp dự đoán, cùng tỷ lệ khung hình (Aspect Ratio):
   $$\mathcal{R}_{CIoU} = \frac{\rho^2(b, b^{gt})}{c^2} + \alpha v$$
2. **$\mathcal{L}_{BCE}$ (Binary Cross-Entropy Loss):** Đánh giá mức độ sai lệch phân loại nhị phân giữa lớp đạt chuẩn (`pass`) và phế phẩm (`defect`).
3. **$\mathcal{L}_{DFL}$ (Distribution Focal Loss):** Mô hình hóa tọa độ biên hộp bao dưới dạng phân phối xác suất liên tục, giúp mạng nơ-ron nắm bắt chính xác các đường biên mờ hoặc bị khúc xạ qua vỏ chai thủy tinh.

### 4.3. Quá Trình Huấn Luyện & Siêu Tham Số (Hyperparameters)
Mô hình được huấn luyện trong 30 epochs trên hạ tầng điện toán đám mây Google Colab GPU (NVIDIA L4/T4, thời gian hoàn tất: **7.7 phút**):
* **Kích thước ảnh đầu vào:** $640 \times 640$ pixels.
* **Batch size:** 16.
* **Tối ưu hóa:** Stochastic Gradient Descent (SGD) với động lượng $momentum = 0.937$, phân rã trọng số $weight\_decay = 0.0005$.
* **Học quy (Learning Rate):** Tốc độ học khởi tạo $\eta_0 = 0.01$, áp dụng cơ chế suy giảm Cosine Annealing về mức $\eta_f = 0.0001$.
* **Tăng cường dữ liệu (Data Augmentation):** Áp dụng Mosaic Augmentation (kết hợp 4 ảnh ngẫu nhiên), biến đổi không gian affine, điều chỉnh độ sáng/độ tương phản HSV và lật ngang ngẫu nhiên.

### 4.4. Bảng Kết Quả Định Lượng Trên 441 Ảnh Kiểm Thử Độc Lập

| Phân Lớp Thực Thể | Số Lượng Nhãn Thực (Instances) | Độ Chính Xác (Precision) | Độ Bao Phủ (Recall) | $mAP_{50}$ (IoU=0.50) | $mAP_{50-95}$ (Toàn dải) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Toàn bộ hệ thống (All)** | **464** | **0.978 (97.8%)** | **0.985 (98.5%)** | **0.995 (99.5%)** | **0.742 (74.2%)** |
| `pass` (Chai đạt chuẩn) | 428 | 0.995 (99.5%) | 0.988 (98.8%) | 0.995 (99.5%) | 0.812 (81.2%) |
| `defect` (Chai khuyết tật) | 36 | 0.962 (96.2%) | 0.981 (98.1%) | 0.995 (99.5%) | 0.672 (67.2%) |

*Chỉ số $F_1\text{-score}$ tối ưu đạt **0.98** tại ngưỡng tin cậy $conf = 0.45$. Thời gian suy luận trung bình đo được: **3.1 ms** tiền xử lý, **125.9 ms** suy luận trên CPU (tương đương **10–15 ms** trên GPU), **2.4 ms** hậu xử lý NMS.*

---

<a name="chuong-5"></a>
## CHƯƠNG 5: THUẬT TOÁN THEO VẾT BYTETRACK & DỰ ĐOÁN CHUYỂN ĐỘNG

### 5.1. Vì Sao Hệ Thống Không Thể Dùng Riêng Mô Hình Nhận Diện (Detector-only)?
Nếu chỉ sử dụng bộ phát hiện YOLO đơn thuần trên từng khung hình độc lập, hệ thống sẽ gặp các lỗi nghiêm trọng sau:
1. **Hiện tượng đếm lặp vô hạn (Duplicate Counting):** Một chai di chuyển trên băng chuyền mất 3 giây (tương đương 60–90 khung hình). Nếu không theo vết, chai đó sẽ bị đếm 90 lần thay vì 1 lần.
2. **Nhấp nháy nhãn (Label Flickering):** Do ánh sáng khúc xạ hoặc góc phản xạ, một chai lỗi có thể bị nhận nhầm thành `pass` ở 1 frame và quay lại thành `defect` ở frame kế tiếp. Không có bộ theo vết, hệ thống không thể tích lũy bằng chứng để đưa ra phán quyết nhất quán.
3. **Mất dấu do chuyển động mờ (Motion Blur):** Khi băng tải chuyển động nhanh, chai có thể bị mờ trong tích tắc khiến điểm tin cậy detection giảm xuống dưới ngưỡng lọc, gây đứt gãy luồng theo dõi.

### 5.2. Nguyên Lý Vượt Trội Của ByteTrack
Khác với các thuật toán truyền thống (SORT, DeepSORT) chỉ ghép nối các bounding box có độ tin cậy cao và thẳng tay loại bỏ các detection điểm thấp, **ByteTrack** áp dụng cơ chế ghép nối 2 giai đoạn:
* **Giai đoạn 1 (First Association):** Ghép các detection điểm tin cậy cao ($conf \ge 0.6$) với các tracklet hiện có bằng ma trận khoảng cách IoU và thuật toán Hungary.
* **Giai đoạn 2 (Second Association):** Đối với các tracklet chưa được ghép ở giai đoạn 1, ByteTrack không xóa bỏ mà tiếp tục dùng các detection có điểm tin cậy thấp ($0.1 \le conf < 0.6$) để ghép nối tiếp. Điều này giúp hệ thống giữ vết liên tục ngay cả khi sản phẩm bị che khuất một phần (occlusion) hoặc bị mờ nhòe do tốc độ băng chuyền.

### 5.3. Mô Hình Chuyển Động Bộ Lọc Kalman 8 Chiều
Trạng thái chuyển động của mỗi vật thể được mô hình hóa trong không gian vector trạng thái 8 chiều:

$$\mathbf{x} = [u, v, a, h, \dot{u}, \dot{v}, \dot{a}, \dot{h}]^T$$

Trong đó:
* $(u, v)$ là tọa độ tâm của bounding box.
* $a = \frac{w}{h}$ là tỷ lệ khung hình (aspect ratio) và $h$ là chiều cao hộp.
* $(\dot{u}, \dot{v}, \dot{a}, \dot{h})$ là các vận tốc biến thiên tuyến tính tương ứng theo thời gian.

Bộ lọc Kalman thực hiện chu trình liên tục hai bước: **Dự đoán (Predict)** vị trí vật thể ở khung hình tiếp theo dựa trên mô hình vận tốc không đổi, và **Cập nhật (Update)** tọa độ thực sau khi nhận được kết quả đo đạc từ mạng YOLO.

---

<a name="chuong-6"></a>
## CHƯƠNG 6: CỖ MÁY TRẠNG THÁI & CƠ CHẾ PHÁN QUYẾT ĐA KHUNG HÌNH (MULTI-FRAME VOTING)

### 6.1. Sơ Đồ Chuyển Trạng Thái (Finite State Machine - FSM)

```
                    ┌────────────────────────┐
                    │    VẬT THỂ MỚI VÀO     │
                    │  (Khởi tạo Track ID)   │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  TRẠNG THÁI QUAN SÁT   │
                    │      (INSPECTING)      │
                    └─────┬────────────┬─────┘
                          │            │
            Phát hiện lỗi │            │ Mất dấu liên tục
         conf > threshold │            │ lost_frames >= 30
                          ▼            ▼
               ┌─────────────┐      ┌─────────────┐
               │   DEFECT    │      │    PASS     │
               │ (Chốt ngay) │      │ (Chốt Đạt)  │
               └─────────────┘      └─────────────┘
```

### 6.2. Các Quy Tắc Phán Quyết Vận Hành Cốt Lõi
1. **Loại bỏ nhiễu mép camera (`min_observation_votes = 3`):** Khi chai vừa chạm vào rìa khung hình camera, hình ảnh thường bị cắt cụt (truncated) hoặc méo quang học do thấu kính góc rộng. Hệ thống bắt buộc track phải được quan sát tối thiểu 3 khung hình trước khi đưa ra kết luận, triệt tiêu 100% cảnh báo giả ở biên.
2. **Quy tắc An Toàn Tuyệt Đối (Fail-Safe / Zero-Defect Rule):** Trong sản xuất công nghiệp, việc bỏ sót 1 sản phẩm lỗi (False Negative) gây hậu quả nghiêm trọng hơn nhiều so với việc kiểm tra lại một sản phẩm nghi vấn (False Positive). Do đó, chỉ cần mô hình phát hiện khuyết tật với độ tin cậy vượt ngưỡng trong bất kỳ khung hình nào, trạng thái track sẽ lập tức được chốt thành `DEFECT`, cờ báo động loại bỏ được kích hoạt ngay lập tức.
3. **Chốt đạt chuẩn an toàn (`lost_track_buffer = 30`):** Một chai chỉ được công nhận là `PASS` khi nó đã đi qua toàn bộ chiều dài vùng quan sát và camera không còn nhìn thấy nó trong 30 khung hình liên tiếp. Điều này đảm bảo toàn bộ bề mặt thân chai trong hành trình di chuyển đều đã được quét qua mà không phát hiện lỗi nào.
4. **Cơ chế Bù Trừ Nhãn Tại Chỗ (In-place Label Correction):** Trong tình huống chai ban đầu hiển thị tạm thời là `pass`, nhưng ở frame thứ 5 mới xoay mặt có vết nứt ra trước ống kính và bị phát hiện là `defect`: hệ thống sẽ tự động hiệu chỉnh biến đếm (`total_pass -= 1`, `total_defect += 1`), đồng thời gửi thông điệp WebSocket chớp sáng cập nhật chính xác dòng sự kiện của `#ID` đó trên giao diện web, đảm bảo số liệu trên màn hình, trong cơ sở dữ liệu và trong tệp CSV luôn khớp nhau 100%.

---

<a name="chuong-7"></a>
## CHƯƠNG 7: PHÂN HỆ KIỂM ĐỊNH ĐA VẬT THỂ (CHAI & DỊ VẬT BĂNG CHUYỀN)

### 7.1. Bài Toán Thực Tiễn Khi Kiểm Tra Video Tự Quay Bằng Điện Thoại
Khi người dùng thử nghiệm hệ thống bằng các video tự quay trong đời sống thực tế, trên mặt bàn hoặc băng tải mô hình thường xuất hiện nhiều vật dụng cá nhân khác ngoài chai lọ: cốc uống nước, hộp giấy, lon nước, sách vở, chuột máy tính...
Nếu hệ thống áp đặt mô hình nhị phân đơn thuần, các vật thể này sẽ bị ép vào lớp `pass` hoặc `defect` một cách sai lệch, gây rối loạn hoàn toàn số liệu thống kê ca sản xuất.

### 7.2. Giải Pháp Hai Chế Độ Vận Hành Chuyên Biệt
Hệ thống [worker.py](file:///d:/ConveyorVision/src/conveyorvision/web/worker.py) được tích hợp sẵn 2 chế độ suy luận linh hoạt:

```python
# Cấu hình chế độ tại InspectionWorker
if self.inspection_mode == "bottle_and_other":
    # Phân tách Chai lọ đạt/lỗi vs Dị vật ngoại lai
    ...
elif self.inspection_mode == "bottle_inspection":
    # Tập trung 100% chuyên sâu bắt lỗi phôi chai
    ...
```

* **Chế độ 1: `bottle_and_other` (Chai & Dị vật khác — Khuyên dùng cho video tự quay):**
  * Tận dụng khả năng nhận diện đa lớp của mô hình thị giác.
  * Mọi vật thể có nhãn là `bottle` sẽ được đưa vào pipeline kiểm định chất lượng: Đạt chuẩn (khung viền Xanh lá) hoặc Khuyết tật (khung viền Đỏ).
  * Mọi vật thể khác nằm ngoài danh mục chai lọ (như `cup`, `can`, `box`, `cell phone`...) được nhận diện chính xác tên gọi bằng tiếng Việt, khoanh khung viền **Tím hoàng gia (Royal Violet #8b5cf6)** và thống kê riêng vào biến đếm `total_other` (Dị vật), không bị phạt nhầm thành phế phẩm chai.
* **Chế độ 2: `bottle_inspection` (Kiểm định chai chuyên sâu — Dành cho xưởng chuẩn):**
  * Toàn bộ tài nguyên tính toán tập trung vào việc phân tích các đặc trưng khuyết tật trên phôi chai đồng nhất.

---

<a name="chuong-8"></a>
## CHƯƠNG 8: KỸ THUẬT BACKEND & TỐI ƯU HÓA ĐỘ TRỄ THẤP (< 50ms)

### 8.1. Ngăn Chặn Hiện Tượng Tích Lũy Trễ Khung Hình (Buffer Bloat)
Độ trễ trong các hệ thống thị giác máy tính truyền thống thường tăng dần theo thời gian chạy (từ vài chục mili-giây lên đến hàng chục giây) do hàng đợi bộ đệm video của OpenCV và socket TCP bị nghẽn. ConveyorVision xử lý triệt để vấn đề này bằng 3 kỹ thuật:
1. **Thiết lập Buffer Đọc = 1:** Thiết lập `cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)` đối với Webcam và Camera IP. Bộ nhớ đệm camera chỉ lưu giữ đúng 1 khung hình mới nhất, các khung hình cũ bị phần cứng ghi đè ngay lập tức.
2. **Đồng bộ nhịp Wall-clock Pacing:** Khi phát tệp video mô phỏng, worker tính toán thời gian trôi qua thực tế bằng `time.perf_counter()` để phát khung hình đúng với tốc độ gốc (1.0x), không phát quá nhanh gây đầy RAM và không phát quá chậm gây giật hình.
3. **Độ phân giải suy luận kép:** Người dùng có thể chuyển đổi nhanh giữa `480px` (Siêu mượt, tốc độ 22–25 FPS trên CPU) và `640px` (Độ nét cao).

### 8.2. Đồng Bộ Hóa Luồng MJPEG Bằng Biến Điều Kiện (Condition Variable)
Thay vì sử dụng vòng lặp vô tận `while True: sleep(0.03)` làm tốn CPU và gửi các khung hình trùng lặp khi mô hình chưa xử lý xong, hệ thống sử dụng đối tượng nguyên tử `threading.Condition`:

```python
# Tại Worker Thread khi có khung hình mới đã vẽ HUD:
with self._frame_lock:
    self._latest_jpeg = encoded_jpeg
    self._frame_cond.notify_all()  # Đánh thức tức thì luồng streaming

# Tại HTTP Streaming Generator:
while self.is_running:
    with worker._frame_lock:
        worker._frame_cond.wait(timeout=0.1)  # Chờ thụ động, 0% CPU rác
        frame_bytes = worker._latest_jpeg
    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
```
*Kết quả:* Khung hình được đẩy tới mắt người dùng ngay lập tức khi GPU/CPU hoàn tất tính toán, giảm độ trễ hiển thị xuống dưới **50 ms**.

### 8.3. Giao Thức Song Song: MJPEG Stream & WebSocket Telemetry
* **Luồng hình ảnh:** Truyền qua endpoint HTTP Multipart `/stream` với kiểu nội dung `multipart/x-mixed-replace; boundary=frame`.
* **Luồng số liệu & sự kiện:** Truyền qua kết nối WebSocket `/ws`. Cứ mỗi 100ms, máy chủ đóng gói gói tin JSON nhỏ gọn gồm: `fps`, `total_pass`, `total_defect`, `total_other`, `active_tracks`, `hazard_alert`.

### 8.4. Bảo Mật Công Nghiệp & Quản Lý Phiên (Audit Logging)
* **Bảo vệ tải tệp tin (Secure File Upload):** Endpoint `/api/upload_video` áp dụng kiểm tra nghiêm ngặt: giới hạn kích thước tối đa 200MB, chỉ chấp nhận đuôi mở rộng an toàn (`.mp4`, `.avi`, `.mov`, `.mkv`), và loại bỏ hoàn toàn các ký tự tấn công duyệt đường dẫn (Path Traversal Regex `re.sub(r"[^a-zA-Z0-9_\-]", "_", ...)`).
* **Quản lý phiên [session_manager.py](file:///d:/ConveyorVision/src/conveyorvision/web/session_manager.py):** Mọi ca kiểm định được cấp mã định danh `SES_YYYYMMDD_HHMMSS`. Dữ liệu chi tiết từng mili-giây (Track ID, thời gian xuất hiện, điểm tin cậy cao nhất, kết luận) được tự động ghi vào tệp CSV trong thư mục `reports/` phục vụ công tác kiểm toán chất lượng ISO 9001.

---

<a name="chuong-9"></a>
## CHƯƠNG 9: THIẾT KẾ GIAO DIỆN HMI / FRONTEND CÔNG NGHIỆP

### 9.1. Triết Lý Thiết Kế HMI Công Nghiệp (ISO 9241-210)
Giao diện **ConveyorVision Web Dashboard** là một ứng dụng Single Page Application (SPA) viết bằng HTML5/CSS3 và Vanilla JavaScript thuần túy, không dùng framework cồng kềnh (React/Vue/Angular), đảm bảo thời gian tải trang ban đầu dưới **100 ms**:
* **Tông nền Dark Navy Slate:** Giảm chói và chống mỏi mắt cho người vận hành trong môi trường phòng điều khiển trung tâm.
* **Mã màu phản trực giác chuẩn quốc tế:**
  * <font color="#10b981">**Emerald Green (#10b981):**</font> Sản phẩm Đạt chuẩn (`PASS`) / Trạng thái sẵn sàng.
  * <font color="#ef4444">**Crimson Red (#ef4444):**</font> Phế phẩm khuyết tật (`DEFECT`) / Cảnh báo nguy hiểm.
  * <font color="#8b5cf6">**Royal Violet (#8b5cf6):**</font> Dị vật ngoại lai (`OTHER`).
  * <font color="#f59e0b">**Amber Gold (#f59e0b):**</font> Đang kiểm định (`INSPECTING`) / Tạm dừng.
  * <font color="#0284c7">**Industrial Cyan (#0284c7):**</font> Thông số kỹ thuật, tỷ lệ phần trăm và nút thao tác chính.

### 9.2. Phân Hệ 6 Màn Hình Chức Năng
1. **Màn hình 1 — Tổng Quan (Overview):** 4 thẻ KPI vĩ mô cộng dồn, bảng 5 phiên gần nhất, bảng thông số phần cứng.
2. **Màn hình 2 — Kiểm Định Trực Tiếp (Live Inspection):** Thanh điều khiển Cockpit 2 tầng, màn hình video kèm Reticles định vị 4 góc, banner cảnh báo Hazard nhấp nháy đỏ, 5 thẻ Mini-KPI, công tắc còi buzzer và bảng sự kiện thời gian thực.
3. **Màn hình 3 — Lịch Sử Kiểm Định (History):** Tra cứu toàn bộ ca chạy, mở modal xem chi tiết từng chai, tải bảng tính CSV kiểm toán.
4. **Màn hình 4 — Đánh Giá Mô Hình (Evaluation):** Bảng chỉ số độc lập trên tập test 441 ảnh, cảnh báo rò rỉ dữ liệu cận trùng, benchmark độ trễ suy luận, xem và phóng to toàn màn hình các biểu đồ PR-Curve và Confusion Matrix.
5. **Màn hình 5 — Dữ Liệu & Mô Hình (Dataset & Models):** Biểu đồ phân bổ 2.666 ảnh chuẩn hóa và danh mục các file weights `.pt`.
6. **Màn hình 6 — Cài Đặt (Settings):** Cấu hình thuật toán ByteTrack/BoT-SORT, lost frame buffer, min votes, còi buzzer và tự động lưu CSV.

### 9.3. Cập Nhật Tại Chỗ Không Giật Lag (In-place Reactive DOM)
Khi có sự kiện sản phẩm mới hoặc cập nhật nhãn, hàm JavaScript `updateProductTableRow(track)` tìm kiếm phần tử DOM theo thuộc tính `data-track-id`. Nếu phần tử đã tồn tại, nó chỉ cập nhật nội dung văn bản và kích hoạt hiệu ứng CSS `row-updated` chớp sáng nhẹ, hoàn toàn không xóa hay vẽ lại toàn bộ bảng, triệt tiêu hiện tượng giật trang.

### 9.4. Còi Báo Động Tổng Hợp Trực Tiếp Bằng Web Audio API
Hệ thống không sử dụng các tệp âm thanh `.mp3` bên ngoài (vốn dễ bị lỗi 404 hoặc tải chậm). Thay vào đó, âm thanh cảnh báo phế phẩm được tổng hợp trực tiếp từ phần cứng âm thanh của trình duyệt thông qua **Web Audio API**:
Tạo dao động sóng răng cưa (Sawtooth Oscillator) quét tần số kép từ **880 Hz xuống 440 Hz** trong 250 mili-giây, mô phỏng chính xác âm thanh còi báo động công nghiệp tại các trạm kiểm soát tự động.

---

<a name="chuong-10"></a>
## CHƯƠNG 10: ĐẢM BẢO CHẤT LƯỢNG, KIỂM THỬ TỰ ĐỘNG & CI/CD PIPELINE

### 10.1. Bộ Kiểm Thử Tự Động (Automated Test Suite)
Dự án được bảo vệ bởi bộ 21 kiểm thử tự động toàn diện viết trên nền tảng `pytest`:
* **Kiểm thử Pipeline & Thuật toán (`tests/test_pipeline.py`):**
  1. `test_data_yaml_structure`: Kiểm tra cấu trúc phân tập `data/data.yaml`.
  2. `test_yolo26_native_architecture`: Kiểm tra tính toàn vẹn của mô hình YOLO26n.
  3. `test_dataset_manager_raw_prefix_and_mapping`: Kiểm tra thuật toán chuẩn hóa nhãn 2 lớp.
  4. `test_normalize_split_name`: Kiểm tra chuẩn hóa tên phân tập (train/val/test).
  5. `test_training_arguments_compatibility`: Kiểm tra tương thích tham số huấn luyện Ultralytics.
  6. `test_pipeline_modules_importable`: Kiểm tra tính độc lập và khả năng nạp của các module.
  7. `test_data_yaml_not_overwritten`: Đảm bảo các script runtime không ghi đè làm bẩn tệp cấu hình gốc.
  8. `test_resolve_track_buffer`: Kiểm tra tính nhất quán giữa tham số lost buffer và ByteTrack YAML.
* **Kiểm thử Web Server & Tích hợp (`tests/test_web.py`):**
  9. `test_index_page`: Kiểm tra giao diện HMI trả về mã 200 và đủ các thẻ DOM.
  10. `test_system_status_api`: Kiểm tra API trạng thái hệ thống.
  11. `test_dataset_info_api`: Kiểm tra số liệu thống kê tập dữ liệu.
  12. `test_evaluation_api`: Kiểm tra trả về đầy đủ các chỉ số mAP, Precision, Recall và URL biểu đồ.
  13. `test_models_api`: Kiểm tra tự động phát hiện danh mục file trọng số `.pt`.
  14. `test_history_and_session_manager`: Kiểm tra toàn bộ vòng đời tạo phiên, ghi nhận track và xuất CSV.
  15. `test_worker_lifecycle`: Kiểm tra luồng khởi động, tạm dừng, tiếp tục và dừng an toàn của Worker.
  16. `test_websocket_events`: Kiểm tra kết nối truyền nhận số liệu thời gian thực qua WebSocket.
  17. `test_settings_api`: Kiểm tra lưu trữ và khôi phục cài đặt hệ thống.
  18. `test_video_upload_validation`: Kiểm tra cơ chế chặn các file upload độc hại.
  19. `test_worker_multi_mode_support`: Kiểm tra hỗ trợ 2 chế độ `bottle_and_other` và `bottle_inspection`.
  20. `test_download_pdf_report_api`: Kiểm tra endpoint tải Báo cáo Kỹ thuật PDF.
  21. `test_download_pdf_uiux_api`: Kiểm tra endpoint tải Cẩm nang Hướng dẫn UI/UX PDF.

*Kết quả kiểm thử thực tế:* **21/21 bài kiểm thử đạt kết quả PASSED trong 4.15 giây.**

### 10.2. Tích Hợp Liên Tục (CI/CD Pipeline)
Hệ thống tích hợp tệp cấu hình `.github/workflows/ci.yml` tự động kích hoạt mỗi khi có thao tác `git push` hoặc `pull_request` lên nhánh `main`:
1. Khởi tạo môi trường ảo Python 3.10 và 3.11 trên runner Ubuntu.
2. Cài đặt các gói phụ thuộc từ `requirements.txt` và `pyproject.toml`.
3. Chạy công cụ kiểm tra chất lượng mã nguồn Flake8 và Black.
4. Thực thi toàn bộ bộ bài kiểm thử `pytest` kèm báo cáo độ phủ mã nguồn (Code Coverage).

---

<a name="chuong-11"></a>
## CHƯƠNG 11: DANH MỤC MÃ NGUỒN & HƯỚNG DẪN BẢO TRÌ HỆ THỐNG

### 11.1. Sơ Đồ Cây Thư Mục Dự Án Chuẩn Hóa
```
ConveyorVision/
├── .github/workflows/ci.yml       # Tự động hóa kiểm thử CI/CD GitHub Actions
├── data/
│   ├── data.yaml                  # Cấu hình đường dẫn và nhãn phân tập YOLO
│   └── manifest.csv               # Bảng tra cứu nguồn gốc frame chống rò rỉ dữ liệu
├── doc/
│   ├── BAO_CAO_TONG_KET_CONVEYORVISION.pdf  # Bản PDF 1: Báo cáo nghiệm thu kỹ thuật
│   ├── HUONG_DAN_SU_DUNG_UI_UX.pdf         # Bản PDF 2: Cẩm nang vận hành giao diện UI/UX
│   ├── TAI_LIEU_TOAN_DIEN_DO_AN_CONVEYORVISION.pdf # Bản PDF 3: Tài liệu kỹ thuật toàn diện
│   ├── TAI_LIEU_HUONG_DAN_UI_UX.md         # Bản Markdown hướng dẫn UI/UX
│   ├── HUONG_DAN_SU_DUNG_DASHBOARD.md     # Bản Markdown hướng dẫn nhanh
│   └── evaluation/                # Các biểu đồ đánh giá thực nghiệm (Loss, PR, Matrix)
├── models/                        # Thư mục chứa các checkpoint trọng số (*.pt)
├── notebooks/
│   └── ConveyorVision_YOLO_Training.ipynb # Jupyter Notebook huấn luyện trên Colab GPU
├── reports/
│   ├── sessions.json              # Cơ sở dữ liệu danh mục các ca kiểm định
│   ├── settings.json              # Tệp lưu cấu hình tham số hệ thống
│   └── snapshots/                 # Lưu trữ ảnh chụp hiện trường viền bounding box
├── scripts/
│   ├── generate_pdf_report.py     # Script ReportLab tạo Báo cáo Nghiệm thu Kỹ thuật PDF
│   ├── generate_pdf_uiux.py       # Script ReportLab tạo Cẩm nang Hướng dẫn UI/UX PDF
│   └── generate_master_doc_pdf.py # Script ReportLab tạo Tài liệu Kỹ thuật Toàn diện PDF
├── src/conveyorvision/
│   ├── __init__.py                # Khai báo package ConveyorVision
│   ├── video_io.py                # Xử lý trích xuất khung hình từ video và lưu manifest
│   ├── dataset_manager.py         # Quản lý, chuẩn hóa nhãn 2 lớp và đồng bộ Roboflow
│   ├── train_pilot.py             # Script huấn luyện mô hình qua giao diện dòng lệnh
│   ├── evaluate.py                # Đánh giá độc lập mô hình trên phân tập test/val
│   ├── inference_conveyor.py      # Pipeline phát hiện & theo vết sản phẩm qua CLI
│   └── web/
│       ├── __init__.py
│       ├── server.py              # Máy chủ FastAPI, endpoints REST, WebSocket, Stream
│       ├── worker.py              # Worker nền thực thi suy luận AI đa luồng
│       ├── session_manager.py     # Quản lý vòng đời phiên kiểm định và xuất file CSV
│       ├── templates/index.html   # Giao diện điều khiển trung tâm SPA
│       └── static/
│           ├── css/style.css      # Hệ thống CSS Dark Modern Glassmorphism
│           └── js/app.js          # Xử lý sự kiện giao diện, WebSocket, Web Audio
├── tests/
│   ├── test_pipeline.py           # 8 bài kiểm thử pipeline và thuật toán thị giác
│   └── test_web.py                # 13 bài kiểm thử web server, worker và tải PDF
├── pyproject.toml                 # Cấu hình gói Python package chuẩn hóa (PEP 518)
├── pytest.ini                     # Cấu hình thực thi bộ kiểm thử
├── requirements.txt               # Danh mục các thư viện phụ thuộc
└── run_app.py                     # Điểm khởi động ứng dụng Web Dashboard
```

### 11.2. Hướng Dẫn Vận Hành & Khởi Động Nhanh (Quick Start)
1. **Kích hoạt môi trường và cài đặt:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Trên Windows
   pip install -r requirements.txt
   ```
2. **Khởi chạy Web Dashboard:**
   ```bash
   python run_app.py
   # Truy cập trình duyệt: http://localhost:8000
   ```
3. **Chạy kiểm định qua giao diện dòng lệnh (CLI):**
   ```bash
   python src/conveyorvision/inference_conveyor.py --source raw_videos/demo.mp4 --model models/conveyor_yolo26_30ep_best.pt --tracker bytetrack.yaml
   ```
4. **Tạo lại toàn bộ các bản báo cáo PDF:**
   ```bash
   python scripts/generate_pdf_report.py
   python scripts/generate_pdf_uiux.py
   python scripts/generate_master_doc_pdf.py
   ```

---

<a name="chuong-12"></a>
## CHƯƠNG 12: TÍCH HỢP PHẦN CỨNG NGOẠI VI & ĐỊNH HƯỚNG TRIỂN KHAI THỰC ĐỊA

### 12.1. Kiến Trúc Kết Nối Cơ Cấu Loại Bỏ Vật Lý (Pneumatic Rejection Actuator)
Để chuyển đổi từ một mô hình phần mềm giám sát sang hệ sinh thái tự động hóa nhà máy toàn diện, hệ thống được thiết kế sẵn sàng các cổng giao tiếp ngoại vi:
* **Kết nối PLC Công Nghiệp (Siemens S7-1200 / Mitsubishi FX5U):** Khi phát hiện track có trạng thái `DEFECT`, worker gửi tín hiệu kích hoạt qua giao thức truyền thông mạng **Modbus TCP/IP** hoặc **OPC-UA**. PLC nhận tín hiệu, đo độ trễ di chuyển dựa trên cảm biến encoder đo tốc độ băng tải, và điều khiển van điện từ kích hoạt xi-lanh khí nén (pneumatic cylinder) hoặc cánh gạt servo để gạt phế phẩm vào khay chứa riêng.
* **Kết nối Module Relay USB / GPIO:** Đối với các dây chuyền chi phí thấp, hệ thống kết nối trực tiếp với mạch relay cách ly quang qua cổng COM (RS-232 / USB) để đóng ngắt rơ-le kích hoạt còi đèn chớp công nghiệp (Tower Light 24V).

### 12.2. Triển Khai Nhúng Trên Thiết Bị Biên (Edge AI Deployment)
Để loại bỏ nhu cầu sử dụng máy tính cồng kềnh tại xưởng, hệ sinh thái ConveyorVision có thể được biên dịch và đóng gói nhúng hoàn toàn:
* **Bo mạch mục tiêu:** **NVIDIA Jetson Orin Nano (8GB)** hoặc **Raspberry Pi 5 kết hợp Google Coral / Hailo-8 AI Accelerator**.
* **Tối ưu hóa mô hình qua TensorRT:** Chuyển đổi mô hình `conveyor_yolo26_30ep_best.pt` sang định dạng `ONNX` và tối ưu lượng tử hóa **FP16 / INT8 TensorRT Engine**, đưa tốc độ suy luận lên hơn **80 FPS** với mức tiêu thụ điện năng chỉ dưới 15 Watts.

---

<a name="phu-luc"></a>
## PHỤ LỤC: BẢNG THUẬT NGỮ CHUYÊN NGÀNH (GLOSSARY)

* **mAP (Mean Average Precision):** Chỉ số trung bình của độ chính xác trung bình trên tất cả các phân lớp thực thể, là thước đo chuẩn mực vàng trong các bài toán phát hiện đối tượng.
* **IoU (Intersection over Union):** Tỷ lệ diện tích giao cắt trên diện tích hợp giữa hộp bao dự đoán và hộp bao thực tế.
* **Kalman Filter:** Thuật toán đệ quy tối ưu ước tính trạng thái chuyển động của hệ thống từ chuỗi các phép đo có nhiễu theo thời gian.
* **Hungarian Algorithm:** Thuật toán tối ưu tổ hợp giải quyết bài toán phân công (Assignment Problem) ghép cặp vật thể với chi phí ma trận tối thiểu.
* **HMI (Human-Machine Interface):** Giao diện tương tác người và máy móc trong tự động hóa công nghiệp.
* **FSM (Finite State Machine):** Cỗ máy trạng thái hữu hạn, điều khiển sự chuyển đổi giữa các trạng thái rời rạc của một thực thể.
* **Near-Duplicate Data:** Hiện tượng các mẫu dữ liệu trong tập huấn luyện và tập kiểm thử gần như giống hệt nhau về nội dung thị giác, gây sai lệch tính khách quan khi nghiệm thu mô hình.

