# TÀI LIỆU TOÀN DIỆN VỀ KIẾN TRÚC, THUẬT TOÁN VÀ VẬN HÀNH ĐỒ ÁN CONVEYORVISION
## HỆ THỐNG THỊ GIÁC MÁY TÍNH KIỂM ĐỊNH & THEO VẾT PHẾ PHẨM BĂNG CHUYỀN THỜI GIAN THỰC (VERSION 2.0)

---

## 1. Tổng Quan Dự Án & Bối Cảnh Bài Toán Công Nghiệp

### 1.1. Bối cảnh thực tế trong sản xuất tự động
Trong các dây chuyền sản xuất công nghiệp hiện đại (nước giải khát, dược phẩm, hóa mỹ phẩm, thực phẩm đóng chai), công đoạn kiểm soát chất lượng (Quality Control - QC) đóng vai trò quyết định đến uy tín thương hiệu và an toàn người tiêu dùng.
* **Phương pháp truyền thống:** Dựa vào công nhân kiểm tra bằng mắt thường. Nhược điểm chí mạng là mệt mỏi thị giác sau 20–30 phút, tốc độ giới hạn (< 1 chai/giây), tỷ lệ bỏ sót lỗi cao (15–25%), và không có dữ liệu số hóa để truy xuất kiểm toán.
* **Phương pháp cảm biến quang/laser đơn điểm:** Chỉ phát hiện được sự có mặt của vật thể hoặc chiều cao tổng thể, hoàn toàn bất lực trước các khuyết tật hình thái phức tạp như nứt cổ chai, rách tem nhãn, móp thân nhựa, hoặc vặn lệch ren nắp.
* **Giải pháp ConveyorVision:** Ứng dụng mô hình Deep Learning tiên tiến (YOLO) kết hợp thuật toán theo vết đa đối tượng (ByteTrack), máy trạng thái công nghiệp (Finite State Machine) và giao diện điều khiển HMI thời gian thực để tự động hóa 100% khâu phân loại chai đạt chuẩn (`pass`) và phế phẩm (`defect`), đồng thời lọc bỏ dị vật lạ trên băng chuyền.

### 1.2. Những thách thức kỹ thuật cốt lõi
1. **Chuyển động liên tục & Mờ chuyển động (Motion Blur):** Sản phẩm di chuyển trên băng tải với vận tốc 0.2 – 0.8 m/s, đòi hỏi thời gian suy luận và xử lý đồ họa phải đạt trên 20 FPS để không gây trôi khung hình.
2. **Hiện tượng giật nhãn (Label Flickering) ở rìa camera:** Khi chai mới bước vào hoặc sắp rời khỏi khung nhìn của camera, góc chụp bị nghiêng hoặc bị che khuất một phần, khiến mô hình AI dễ dự đoán sai nếu chỉ dựa vào một khung hình duy nhất (Single-frame inference).
3. **Phản quang và khúc xạ ánh sáng:** Chai thủy tinh và chai nhựa trong suốt có tính phản xạ ánh sáng mạnh, phụ thuộc vào hệ thống đèn trần nhà xưởng.
4. **Vấn đề trễ hiển thị (Video Latency) trên Web Dashboard:** Luồng truyền hình ảnh qua mạng cục bộ nếu thiết kế vòng lặp stream không đúng cách sẽ gây hiện tượng trễ lũy kế (buffer lag), khiến kỹ sư nhìn thấy hình ảnh trễ 2–5 giây so với vị trí thực tế của chai trên băng tải.

---

## 2. Kiến Trúc Tổng Thể & Ngăn Xếp Công Nghệ (Technology Stack)

Hệ thống được thiết kế theo cấu trúc phân tầng công nghiệp (Layered Architecture):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            TẦNG 1: THU THẬP HÌNH ẢNH (DATA INPUT)                           │
│     • Camera Công nghiệp USB / IP Camera (RTSP)                                             │
│     • Video File mô phỏng thực tế (.mp4, .avi) trong raw_videos/                            │
│     • Kích thước hàng đợi phần cứng: cv2.CAP_PROP_BUFFERSIZE = 1 (Triệt tiêu độ trễ đệm)     │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ (Khung hình BGR gốc)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                     TẦNG 2: THỊ GIÁC MÁY TÍNH & BÁM VẾT (AI VISION ENGINE)                  │
│     • Tiền xử lý & Chuẩn hóa: Resize 480px / 640px, BGR -> RGB, Tensor Float32             │
│     • Mô hình AI: YOLO26 Nano / YOLOv8 Nano (2.5M params, 5.9 GFLOPs, weights: 5.45 MB)     │
│     • Thuật toán theo vết: ByteTrack (Kalman Filter 8D + Liên kết phát hiện 2 vòng)         │
│     • Trích xuất: Bounding Box [x1, y1, x2, y2], Track ID, Class ID, Confidence Score       │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ (Dữ liệu Track + Bounding Box)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                TẦNG 3: MÁY TRẠNG THÁI CÔNG NGHIỆP (INDUSTRIAL STATE MACHINE)                │
│     • Bộ lọc đa khung hình (Multi-frame Voting): Loại bỏ nhiễu ở viền (Min 3 votes)         │
│     • Nguyên tắc ưu tiên an toàn (Defect Bias): Bắt được 2 frame lỗi -> Lập tức chốt DEFECT  │
│     • Cơ chế chốt trễ (Delayed Commit): Chờ chai rời khỏi camera (Lost Buffer 30 frame)     │
│     • Cập nhật tại chỗ (In-place Record Update): Tránh đếm trùng lặp mã sản phẩm            │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                      ┌────────────────────────┴────────────────────────┐
                      ▼                                                 ▼
┌───────────────────────────────────────────────┐ ┌───────────────────────────────────────────┐
│     TẦNG 4: BACKEND & DỊCH VỤ DỮ LIỆU         │ │   TẦNG 5: TRẠM ĐIỀU KHIỂN HMI WEB SPA     │
│  • FastAPI + Uvicorn Asynchronous Server      │ │• Giao diện Dark Glassmorphism chống chói  │
│  • WebSocket Server: Đồng bộ sự kiện thời     │ │• 6 Phân hệ: Tổng quan, Trực tiếp, Lịch    │
│    gian thực từng mili-giây                   │ │  sử, Đánh giá, Dữ liệu, Cài đặt           │
│  • Luồng MJPEG: threading.Condition nén đẩy   │ │• Video Canvas HUD: Khung ngắm định vị     │
│    chỉ khi có frame mới (<50ms latency)       │ │• Còi báo động Web Audio API (880 -> 440Hz)│
│  • Session Manager: Ghi log kiểm toán CSV     │ │• Bảng sự kiện Reactive DOM In-place       │
│  • ReportLab Engine: Xuất 2 bản PDF chuẩn hóa │ │• 2 Chế độ: Chai & Dị vật vs QC chuyên sâu │
└───────────────────────────────────────────────┘ └───────────────────────────────────────────┘
```

### Bảng thành phần công nghệ chi tiết:
| Phân hệ | Công nghệ sử dụng | Vai trò kỹ thuật trong hệ thống |
| :--- | :--- | :--- |
| **Deep Learning Framework** | `ultralytics` (YOLOv8 / YOLO26 API) | Phát hiện đối tượng đa tỉ lệ với kiến trúc NMS-free và backbone tối ưu hóa |
| **Computer Vision Engine** | `OpenCV` (cv2) | Xử lý ảnh số, chuyển đổi không gian màu, vẽ HUD overlay và streaming frame |
| **Object Tracking** | `ByteTrack` (`bytetrack.yaml`) | Gán nhãn ID liên tục xuyên suốt các frame qua chuyển động Kalman Filter |
| **Backend Web Framework** | `FastAPI`, `Starlette`, `Uvicorn` | API bất đồng bộ hiệu năng cao, quản lý kết nối WebSocket và luồng stream video |
| **Concurrency Control** | `threading.Condition`, `threading.Event` | Đồng bộ hóa nhà sản xuất - người tiêu dùng (Producer-Consumer) không gây nghẽn CPU |
| **HMI Frontend** | HTML5, CSS3 Variables, Vanilla JS ES6+ | SPA đáp ứng nhanh, cập nhật DOM tại chỗ, không dùng framework nặng gây lag |
| **Audio Synthesizer** | Web Audio API (`AudioContext`, `OscillatorNode`) | Phát âm thanh cảnh báo lỗi trực tiếp từ mã lệnh trình duyệt mà không cần file MP3 |
| **Báo cáo PDF & Font** | `reportlab` 5.1.0, `pypdf`, Windows TrueType Font | Biên dịch 2 bản PDF báo cáo kỹ thuật & cẩm nang UI/UX tiếng Việt Unicode chuẩn A4 |
| **Kiểm thử tự động** | `pytest`, `pytest-cov`, `TestClient` | 21 kịch bản unit test và integration test bao phủ toàn bộ luồng logic |

---

## 3. Quản Trị Dữ Liệu & Quy Trình Huấn Luyện Mô Hình

### 3.1. Nguồn gốc dữ liệu & Chuẩn hóa 2 lớp (Class Mapping)
Dự án hợp nhất 3 bộ dữ liệu thành phần từ Roboflow với tổng quy mô **2.666 ảnh**:
1. **Conveyor Belt gốc (`conveyor_`):** 1.740 ảnh quay trực tiếp từ băng tải công nghiệp, gán nhãn gốc là `bottle`. Module `dataset_manager.py` tự động remap thành `class 0: pass`.
2. **Bayo Bottle Detection (`bayo_`):** 706 ảnh chai lọ trong các điều kiện ánh sáng đa dạng, bao gồm 134 ảnh nền rỗng không chứa chai.
3. **Bottle Defects (`bottle_defect_`):** 220 ảnh chụp chi tiết các khuyết tật đặc thù: móp thân vỏ, nứt vỡ miệng chai, rách nhãn mác, mất nắp chai. Toàn bộ khuyết tật này được gom chuẩn hóa thành `class 1: defect`.

#### Phân bổ dữ liệu 3 tập chuẩn khoa học:
* **Tập Huấn luyện (Train):** 1.692 ảnh (chiếm 63.5%) — gồm 3.053 box `pass`, 384 box `defect`, 138 ảnh nền rỗng.
* **Tập Kiểm định (Validation):** 533 ảnh (chiếm 20.0%) — gồm 1.052 box `pass`, 99 box `defect`, 41 ảnh nền rỗng.
* **Tập Kiểm thử Độc lập (Test):** 441 ảnh (chiếm 16.5%) — gồm 991 box `pass`, 41 box `defect`, 24 ảnh nền rỗng.

> **Tầm quan trọng của 203 ảnh nền rỗng (Negative Images):** Giúp mô hình học được đặc trưng của mặt băng chuyền kim loại và con lăn cao su khi không có vật thể, triệt tiêu hiện tượng báo động giả (False Positives) khi băng tải chạy không tải.

### 3.2. Cơ chế cách ly cấu hình runtime (`runs/runtime_data.yaml`)
Để đảm bảo kho Git luôn sạch và có thể clone chạy ngay trên bất kỳ máy tính nào mà không bị xung đột đường dẫn tuyệt đối:
* Tệp `data/data.yaml` chỉ lưu đường dẫn tương đối: `path: data`.
* Khi khởi chạy huấn luyện (`train_pilot.py`), đánh giá (`evaluate.py`) hoặc Notebook, hệ thống tự động sinh tệp `runs/runtime_data.yaml` chứa đường dẫn tuyệt đối cục bộ của máy hiện tại. Sau khi hoàn thành, tệp gốc trong Git không bị biến đổi.

### 3.3. Thông số kỹ thuật quá trình huấn luyện
* **Mô hình gốc:** `yolo26n.pt` native (End-to-end NMS-free, 260 layers, 2.504.580 tham số, 5.9 GFLOPs).
* **Môi trường:** Google Colab GPU Runtime (NVIDIA L4/T4).
* **Thời lượng:** 30 epochs hoàn thành trong **463.2 giây (~7.7 phút)** (tương đương ~15.4 giây/epoch).
* **Optimizer:** AdamW với learning rate ban đầu `lr0 = 0.001667`, `momentum = 0.9`.
* **Trọng số phân loại `cls = 1.2`:** Giả thuyết kỹ thuật tăng hệ số phạt đối với lớp thiểu số phế phẩm.

### 3.4. Đánh giá định lượng trên 441 ảnh Test độc lập
Đo lường bằng script `python src/conveyorvision/evaluate.py --split test`:

$$\text{mAP@50} = \int_{0}^{1} P(R) \, dR \quad \text{tại ngưỡng IoU } = 0.5$$

| Lớp (Class) | Số lượng ảnh | Số Bounding Box | Precision | Recall | mAP@50 | mAP@50-95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Toàn bộ (Overall)** | **441** | **1.032** | **78.2%** | **75.7%** | **82.5%** | **61.4%** |
| `pass` (Chai đạt) | 381 | 991 | 79.7% | 66.1% | 78.9% | 51.2% |
| `defect` (Chai lỗi) | 36 | 41 | **76.6%** | **85.4%** | **86.2%** | **71.7%** |

### 3.5. Báo cáo minh bạch về rủi ro dữ liệu cận trùng (Near-Duplicate Leakage)
Dự án đặt tính trung thực và chuẩn mực khoa học lên hàng đầu:
1. **Phân tích hàm băm tri giác (pHash / SSIM):** Thuật toán đối sánh ảnh phát hiện **53–54 cặp ảnh cận trùng** giữa tập Train và tập Test (41 ảnh test có bản sao rất gần trong train, trong đó có **23/36 ảnh test chứa nhãn defect**). Nguyên nhân do các frame được cắt từ cùng một video clip ngắn.
2. **Ý nghĩa khoa học:** Các chỉ số kiểm thử hiện tại phản ánh **ngưỡng trên thực nghiệm (Empirical Upper Bound)**. Khi triển khai nghiệm thu cấp nhà máy, bắt buộc phải chia lại dữ liệu theo phiên quay độc lập (**Session-based Split**) để kiểm tra tính tổng quát hóa tuyệt đối.
3. **Lý giải ma trận nhầm lẫn tại ngưỡng cứng `conf=0.25`:** Do tập test chỉ có 41 box phế phẩm, một số box ở rìa bị nhầm sang `pass` tại ngưỡng 0.25, nhưng trên toàn dải ngưỡng của đường cong PR, mô hình đạt độ nhạy bắt lỗi (Recall) lên tới **85.4%**.

---

## 4. Thuật Toán Bám Vết & Máy Trạng Thái Công Nghiệp (State Machine)

### 4.1. Tại sao Single-frame Detection thất bại trên băng chuyền?
Nếu chỉ chạy Object Detection trên từng frame:
* Mỗi frame phát hiện một chai sẽ tạo ra một kết quả độc lập. Nếu chai đi qua camera trong 30 frame, hệ thống sẽ đếm thành **30 chai khác nhau**.
* Khi chai vừa bước vào nửa thân qua mép camera, ánh sáng chưa đủ, AI dễ dự đoán nhầm thành khuyết tật (`defect`). Nếu kích hoạt cơ cấu gạt ngay lúc này, hệ thống sẽ gạt nhầm chai đạt.

### 4.2. Giải pháp: Tích hợp ByteTrack + Kalman Filter
ByteTrack giải quyết triệt để vấn đề này thông qua cơ chế liên kết 2 vòng:
* **Bộ lọc Kalman 8 chiều:** Dự đoán không gian trạng thái của từng chai: $[x, y, a, h, v_x, v_y, v_a, v_h]$ (với $(x, y)$ là tọa độ tâm, $a$ là tỷ lệ khung hình, $h$ là chiều cao, và các $v$ là vận tốc tương ứng).
* **Vòng liên kết 1 (High-score association):** Ghép các bounding box có confidence $\ge 0.5$ với các track dự đoán của Kalman Filter dựa trên ma trận khoảng cách IoU.
* **Vòng liên kết 2 (Low-score association):** Tận dụng các bounding box có confidence thấp ($0.1 \le \text{conf} < 0.5$) để tiếp tục duy trì track khi chai bị che khuất một phần hoặc bị mờ do chuyển động nhanh, ngăn chặn việc gãy track sinh ID mới.

### 4.3. Máy trạng thái hữu hạn & Cơ chế phán quyết Multi-frame Voting
Mỗi chai mang một Track ID duy nhất sẽ vận hành theo sơ đồ máy trạng thái sau:

```
        ┌────────────────────────────────────────────────────────┐
        │                 CHAI BẮT ĐẦU VÀO TẦM QUÉT               │
        │                     (ID Khởi tạo mới)                  │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │            TRẠNG THÁI 1: INSPECTING (Đang quét)        │
        │   • Tích lũy số lượt quan sát: obs_votes += 1          │
        │   • Đếm số phiếu lỗi: defect_votes                     │
        │   • Chưa đưa ra kết luận cuối cùng                     │
        └──────────────┬──────────────────────────┬──────────────┘
                       │                          │
        (defect_votes >= 2                        │ (obs_votes >= min_votes VÀ
         hoặc majority DEFECT)                    │  không có bằng chứng DEFECT)
                       │                          │
                       ▼                          ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│     TRẠNG THÁI 2: DEFECT (LỖI)       │  │       TRẠNG THÁI 3: PASS (ĐẠT)       │
│ • Gán nhãn phế phẩm vĩnh viễn        │  │ • Tạm giữ nhãn PASS                  │
│ • Bật Cờ cảnh báo đỏ neon            │  │ • CHƯA chốt số đếm ngay              │
│ • Kích hoạt còi Web Audio API        │  │ • Chờ chai an toàn đi qua trạm       │
│ • Cập nhật tại chỗ hàng trong bảng   │  │ • Sau lost_buffer (30 frame) mất dấu │
│ • Sẵn sàng kích hoạt cơ cấu gạt PLC  │  │   mới chính thức ghi nhận vào tổng   │
└──────────────────────────────────────┘  └──────────────────────────────────────┘
```

#### Các nguyên lý thiết kế then chốt:
1. **Thiên vị An Toàn Tuyệt Đối (Defect Bias):** Trong công nghiệp đóng chai, việc bỏ sót 1 chai lỗi ra thị trường gây thiệt hại gấp 1.000 lần việc gạt nhầm 1 chai tốt. Do đó, chỉ cần có từ **2 frame phát hiện lỗi** trở lên, trạng thái lập tức chuyển sang `DEFECT` và không bao giờ bị đảo ngược thành `PASS`.
2. **Cơ chế Chốt Trễ (Delayed Commit cho PASS):** Trạng thái `PASS` chỉ được cộng vào tổng số lượng khi chai đã hoàn toàn biến mất khỏi tầm nhìn trong `lost_track_buffer = 30` khung hình liên tiếp. Điều này bảo đảm nếu chai ở cuối hành trình mới bị lộ vết nứt, hệ thống vẫn kịp thời chuyển thành DEFECT.
3. **Cập nhật dòng tại chỗ (In-place Reactive Record):** Khi trạng thái thay đổi, hệ thống phát tín hiệu WebSocket cập nhật trực tiếp dòng tương ứng trong bảng nhật ký, không tạo dòng mới, loại bỏ 100% rủi ro đếm trùng sản phẩm.

---

## 5. Động Cơ Xử Lý Video & Tối Ưu Hóa Độ Trễ Siêu Thấp (< 50ms)

### 5.1. Triệt tiêu tắc nghẽn bằng `threading.Condition`
* **Vấn đề của luồng MJPEG thông thường:** Vòng lặp `while True` nén JPEG liên tục ngay cả khi camera chưa có frame mới, tiêu tốn 100% CPU và làm phình to hàng đợi TCP buffer, gây trễ tích lũy hàng giây.
* **Giải pháp trong ConveyorVision:** Áp dụng mô hình **Producer-Consumer** với `threading.Condition`:
  - **Worker (Producer):** Sau khi xử lý xong một khung hình mới, gọi `condition.acquire()`, cập nhật `latest_frame` và phát tín hiệu `condition.notify_all()`.
  - **Stream Generator (Consumer):** Luồng stream gọi `condition.wait()`, chuyển vào trạng thái ngủ không tốn CPU. Ngay khi có tín hiệu, luồng thức dậy nén ảnh JPEG và đẩy ra HTTP response. Khung hình được truyền ngay lập tức, độ trễ truyền dẫn đo được **< 50 ms**.

### 5.2. Đồng bộ nhịp Wall-clock Pacing & Buffer phần cứng
* Với Webcam: Cấu hình `cv2.CAP_PROP_BUFFERSIZE = 1`, buộc driver camera bỏ qua các khung hình cũ, chỉ lấy khung hình mới nhất tại thời điểm thực tế.
* Với Video File mô phỏng: Tính toán thời gian trôi qua thực tế bằng `time.time() - start_time` để điều tiết FPS bằng đúng tốc độ quay gốc (1.0x), không phát quá nhanh làm tràn bộ nhớ và không phát gián đoạn.

### 5.3. Chế độ Kiểm Định Kép (Dual Inspection Modes)
Đáp ứng cả bài toán thử nghiệm thực tế bằng điện thoại và dây chuyền công nghiệp chuẩn:
1. **Chế độ 1: Chai & Dị Vật Khác (`bottle_and_other`):**
   - Phù hợp cho video quay đời thực có nhiều đồ vật linh tinh trên băng tải.
   - Chai lọ được phân loại thành Đạt chuẩn (khung Xanh lá) hoặc Phế phẩm (khung Đỏ).
   - Các vật thể lạ khác (cốc, hộp, lon, bút, sách, điện thoại...) được khoanh khung màu **Tím sapphire**, dịch tên sang tiếng Việt và đếm riêng vào thẻ **Dị vật**, tuyệt đối không bị phạt nhầm thành phế phẩm chai.
2. **Chế độ 2: QC Chai Chuyên Sâu (`bottle_inspection`):**
   - Phù hợp cho dây chuyền chuẩn hóa. Tập trung 100% tài nguyên thuật toán phân tích các khuyết tật vỏ chai, nắp chai và mức nước.

---

## 6. Trạm Điều Khiển Web HMI Dashboard Chuyên Nghiệp

Được xây dựng theo triết lý **Dark Glassmorphism** công nghiệp hiện đại, bao gồm 6 màn hình SPA:

1. **Màn hình 1 — Tổng Quan (Overview):**
   - 4 Thẻ KPI vĩ mô cộng dồn: Tổng sản phẩm đã quét, Đạt chuẩn (`PASS`), Phế phẩm (`DEFECT`), Tỷ lệ phế phẩm bình quân (%).
   - Nhật ký 5 phiên làm việc gần nhất kèm thời gian và nút nhảy nhanh.
   - Nút tắt tải trực tiếp 2 bản báo cáo PDF.
2. **Màn hình 2 — Kiểm Định Trực Tiếp (Live Inspection - Trọng Tâm):**
   - Thanh điều khiển Cockpit 2 tầng: Nguồn video, tải video mới an toàn, chọn chế độ kiểm định, Model checkpoint, Độ phân giải (`480px` siêu mượt 22–25 FPS trên CPU vs `640px` chuẩn), Thanh trượt Confidence (0.10 – 0.90), Thuật toán Tracker (`ByteTrack` / `BoT-SORT`).
   - 4 Nút thao tác vận hành: Bắt đầu, Tạm dừng/Tiếp tục, Chụp ảnh hiện trường (`reports/snapshots/`), Dừng phiên và chốt số liệu.
   - Khung video Machine Vision HUD: Khung ngắm định vị 4 góc, nhãn ID trực quan, Cờ cảnh báo đỏ neon chớp sáng khi phát hiện lỗi, Còi báo động Web Audio API (880Hz &rarr; 440Hz).
   - Bảng nhật ký sản phẩm thời gian thực cập nhật tại chỗ (*In-place Reactive DOM*).
3. **Màn hình 3 — Lịch Sử Kiểm Định (Inspection History):**
   - Bảng tổng hợp toàn bộ các ca sản xuất trong quá khứ.
   - Hộp thoại Modal xem chi tiết từng mã Track ID (thời điểm xuất hiện, mức độ tin cậy, số frame quan sát, trạng thái chốt).
   - Tải file kiểm toán CSV phục vụ lưu trữ ISO 9001 / HACCP.
4. **Màn hình 4 — Đánh Giá Mô Hình (Model Evaluation):**
   - Bảng chỉ số độc lập trên 441 ảnh Test (Precision, Recall, mAP50, mAP50-95).
   - Minh bạch khoa học về rủi ro ảnh cận trùng và sự khác biệt giữa Recall toàn dải với ma trận nhầm lẫn tĩnh.
   - Đo lường thực tế độ trễ từng giai đoạn (Preprocess: 3.1ms, Inference CPU: 125.9ms, Postprocess: 2.4ms).
   - Bộ xem biểu đồ trực quan hóa (PR Curve, Confusion Matrix, Loss Curves) có tính năng phóng to toàn màn hình.
5. **Màn hình 5 — Dữ Liệu & Mô Hình (Dataset & Models):**
   - Thống kê tỷ lệ phân bổ của 2.666 ảnh và danh mục các tệp trọng số `.pt` sẵn có.
6. **Màn hình 6 — Cài Đặt Tham Số (Settings):**
   - Tùy chỉnh tham số ByteTrack, lost buffer, số frame tối thiểu, tự động lưu CSV và còi âm thanh; đồng bộ thẳng tới tệp `reports/settings.json`.

---

## 7. Cấu Trúc Mã Nguồn & Chi Tiết Từng Module Trong Dự Án

```
ConveyorVision/
├── .github/workflows/ci.yml         # CI/CD tự động chạy kiểm thử trên GitHub Actions
├── data/
│   ├── data.yaml                    # Cấu hình dataset tương đối cho Git (2 class: 0 pass, 1 defect)
│   ├── images/ & labels/            # 2.666 ảnh và nhãn phân chia train/val/test
│   └── README.roboflow.txt          # Ghi chú nguồn gốc dữ liệu từ Roboflow
├── doc/
│   ├── BAO_CAO_TONG_KET_CONVEYORVISION.pdf  # BẢN PDF 1: Báo cáo nghiệm thu kỹ thuật (6 trang)
│   ├── HUONG_DAN_SU_DUNG_UI_UX.pdf          # BẢN PDF 2: Cẩm nang hướng dẫn UI/UX (9 trang)
│   ├── TAI_LIEU_HUONG_DAN_UI_UX.md          # Bản Markdown chi tiết của cẩm nang UI/UX
│   ├── HUONG_DAN_SU_DUNG_DASHBOARD.md       # Hướng dẫn thao tác nhanh bảng điều khiển
│   ├── ConveyorVision_Project_Proposal_YOLO26.pdf # Bản đề xuất dự án ban đầu
│   └── evaluation/                          # Biểu đồ đánh giá: results.png, confusion matrix, PR curve
├── models/
│   ├── conveyor_yolo26_30ep_best.pt # Trọng số YOLO26n huấn luyện 30 epochs (5.45 MB)
│   └── yolov8n_pilot_best.pt        # Trọng số baseline YOLOv8n pilot 3 epochs (6.5 MB)
├── notebooks/
│   └── ConveyorVision_YOLO_Training.ipynb   # Jupyter Notebook huấn luyện & trực quan hóa biểu đồ
├── raw_videos/                      # Thư mục chứa video băng chuyền mẫu thử nghiệm
├── reports/
│   ├── sessions.json                # Cơ sở dữ liệu lưu trữ lịch sử các phiên kiểm định
│   ├── settings.json                # Cấu hình tham số hệ thống đã lưu
│   └── snapshots/                   # Thư mục lưu ảnh chụp hiện trường vi phạm
├── scripts/
│   ├── generate_pdf_report.py       # Script biên dịch Báo cáo Kỹ thuật PDF (ReportLab)
│   └── generate_pdf_uiux.py         # Script biên dịch Cẩm nang UI/UX PDF (ReportLab)
├── src/conveyorvision/
│   ├── __init__.py                  # Khai báo package & phiên bản v2.0.0
│   ├── dataset_manager.py           # Quản lý, tải từ Roboflow, remap nhãn & chuẩn hóa 3 tập
│   ├── train_pilot.py               # Script CLI huấn luyện mô hình YOLO với runtime YAML động
│   ├── evaluate.py                  # Đánh giá độc lập mô hình trên tập test/val qua Ultralytics API
│   ├── inference_conveyor.py        # Pipeline CLI kiểm định thời gian thực (Detect + ByteTrack)
│   ├── video_io.py                  # Trích xuất khung hình từ video và ghi log manifest.csv
│   └── web/                         # Trạm điều khiển Web Dashboard HMI (FastAPI)
│       ├── __init__.py
│       ├── server.py                # Máy chủ FastAPI, định tuyến REST API, WebSocket & endpoints PDF
│       ├── worker.py                # Tiến trình nền thực thi AI inference, ByteTrack & State Machine
│       ├── session_manager.py       # Quản lý vòng đời ca sản xuất & xuất file log kiểm toán CSV
│       ├── templates/index.html     # Giao diện đơn trang HMI SPA hoàn chỉnh
│       └── static/
│           ├── css/style.css        # Thiết kế Dark Glassmorphism, animations và layout HMI
│           └── js/app.js            # Điều khiển WebSocket, reactive DOM, Web Audio API & phím tắt
├── tests/
│   ├── test_pipeline.py             # Unit tests cho dataset, mô hình, tracker và CLI pipeline
│   └── test_web.py                  # Integration tests cho REST API, worker, WebSocket & PDF downloads
├── pyproject.toml                   # Khai báo cấu hình dự án chuẩn pip package
├── pytest.ini                       # Cấu hình đường dẫn thực thi kiểm thử tự động
├── requirements.txt                 # Danh mục thư viện phụ thuộc
├── run_app.py                       # Điểm khởi chạy nhanh ứng dụng Web Dashboard
├── CONTRIBUTING.md                  # Hướng dẫn đóng góp mã nguồn & quy chuẩn code
├── LICENSE                          # Giấy phép phần mềm mã nguồn mở MIT
└── README.md                        # Tài liệu tổng quan dự án trên GitHub
```

### Chi tiết nhiệm vụ của các tệp mã nguồn nòng cốt:
1. **`src/conveyorvision/web/worker.py`:** Trái tim của hệ thống. Chạy trên một luồng tách biệt (`threading.Thread`), nạp mô hình YOLO và cấu hình ByteTrack. Vòng lặp chính đọc từng khung hình từ video/webcam, thực hiện detect, feed qua ByteTrack, cập nhật số phiếu vote của từng Track ID, quyết định trạng thái `INSPECTING`/`PASS`/`DEFECT`/`OTHER`, điều khiển biến điều kiện `condition.notify_all()` và phát gói tin trạng thái qua WebSocket.
2. **`src/conveyorvision/web/server.py`:** Máy chủ Web API xây dựng trên FastAPI. Quản lý vòng đời worker (Start/Pause/Resume/Stop), định tuyến luồng `/api/video_feed` (MJPEG), xử lý tải video an toàn chống lỗ hổng Path Traversal (`/api/upload_video`), quản lý lịch sử (`/api/history`), cấu hình (`/api/settings`) và cung cấp 2 endpoint tải trực tiếp PDF (`/api/download_pdf_report` và `/api/download_pdf_uiux`).
3. **`src/conveyorvision/web/session_manager.py`:** Quản lý phiên làm việc. Tạo mã phiên định danh duy nhất (`SES_YYYYMMDD_HHMMSS`), ghi nhận thời gian bắt đầu, thời lượng, số lượng PASS, DEFECT, OTHER và xuất tệp nhật ký CSV kiểm toán chi tiết đến từng mili-giây.
4. **`src/conveyorvision/inference_conveyor.py`:** Phiên bản chạy dòng lệnh (CLI). Cho phép kỹ sư kiểm tra nhanh trên một video hoặc camera mà không cần mở giao diện Web, hỗ trợ các đối số `--source`, `--model`, `--tracker`, `--conf`, `--show`, `--out_csv`.
5. **`scripts/generate_pdf_report.py` & `generate_pdf_uiux.py`:** Công cụ tự động hóa xuất bản tài liệu PDF chất lượng cao. Sử dụng ReportLab với canvas 2 lượt (`NumberedCanvas`) để tính chính xác tổng số trang, nhúng các biểu đồ thực nghiệm, bảng dữ liệu chuẩn và bảng chữ ký nghiệm thu.

---

## 8. Hướng Dẫn Vận Hành & Khắc Phục Sự Cố (Troubleshooting)

### 8.1. Khởi chạy hệ thống
1. **Khởi chạy Giao diện Web HMI (Khuyên dùng):**
   ```bash
   python run_app.py
   # Tùy chỉnh cổng nếu cần: python run_app.py --port 8080 --host 0.0.0.0
   ```
   Mở trình duyệt truy cập: `http://localhost:8000`.

2. **Chạy kiểm định qua dòng lệnh CLI:**
   ```bash
   python src/conveyorvision/inference_conveyor.py --source raw_videos/demo.mp4 --model models/conveyor_yolo26_30ep_best.pt --tracker bytetrack.yaml
   ```

3. **Chạy bộ kiểm thử tự động (Test Suite):**
   ```bash
   pytest -v
   ```
   *(Toàn bộ 21/21 test cases đạt 100% PASSED trong ~4.15 giây).*

### 8.2. Bảng phím tắt thao tác nhanh trên hiện trường
| Phím tắt | Phạm vi | Chức năng |
| :--- | :--- | :--- |
| **Bấm Logo ConveyorVision** | Header | Chuyển nhanh về màn hình Tổng quan |
| **Nút 📥 Báo Cáo PDF** | Header | Tải toàn văn Báo cáo Nghiệm thu Kỹ thuật (PDF) |
| **Nút 📘 Cẩm Nang UI/UX** | Header | Tải Cẩm nang Hướng dẫn Vận hành HMI (PDF) |
| **Nút 📖 Hướng Dẫn Online** | Header | Mở bảng cẩm nang tương tác 5 tab trong ứng dụng |
| **Phím ESC** | Toàn hệ thống | Đóng nhanh mọi cửa sổ Modal hoặc biểu đồ phóng to |
| **Phím 1, 2, 3, 4, 5, 6** | Bàn phím | Chuyển đổi nhanh giữa 6 màn hình chức năng |
| **Phím F / Nút ⛶** | Khung video | Bật / tắt chế độ toàn màn hình camera (Fullscreen) |

### 8.3. Bảng chẩn đoán & xử lý sự cố thường gặp
| Sự cố phát sinh | Nguyên nhân gốc rễ | Biện pháp xử lý ngay |
| :--- | :--- | :--- |
| **Không nghe thấy tiếng còi khi chai lỗi** | Trình duyệt chặn quyền tự động phát âm thanh (Autoplay Policy) | Nhấp chuột vào một vị trí bất kỳ trên trang web để cấp quyền Web Audio; kiểm tra công tắc âm thanh bên cạnh bảng số liệu. |
| **Video bị giật hoặc FPS dưới 15** | Đang để độ phân giải 640px trên máy tính văn phòng chỉ dùng CPU | Tại thanh điều khiển, đổi mục 'Độ phân giải suy luận' sang **`⚡ 480px (Siêu mượt)`**. Tốc độ sẽ tăng vọt lên 22–25 FPS. |
| **Webcam hiển thị màn hình đen** | Ứng dụng khác (Zoom, Teams, Camera) đang chiếm quyền webcam | Tắt các ứng dụng đang dùng webcam, chọn lại nguồn `Webcam 0` và bấm Bắt đầu. |
| **Vật thể lạ bị báo lỗi viền đỏ** | Đang để chế độ 'QC Chai Chuyên Sâu' trên video tự quay có nhiều đồ vật | Đổi chế độ sang **`🍶 Chai & Dị Vật Khác`**. Các vật thể khác sẽ được viền tím và đếm vào mục Dị vật. |
| **Lỗi khi tải video mới lên** | File dung lượng quá 200MB hoặc sai định dạng | Đảm bảo file có đuôi `.mp4`, `.avi`, `.mov`, `.mkv` và dung lượng dưới 200MB. |

---

## 9. Lộ Trình Công Nghiệp Hóa (Industrial Deployment Roadmap)

Để nâng cấp từ sản phẩm đồ án phòng Lab thành giải pháp thương mại hóa cắm-và-chạy (Plug-and-Play) trong nhà máy:

1. **Giao tiếp phần cứng điều khiển cơ khí (PLC & Cơ cấu gạt phế phẩm):**
   - Tích hợp module giao tiếp qua giao thức công nghiệp **Modbus TCP/IP** hoặc **OPC-UA** để gửi tín hiệu tới PLC Siemens S7-1200 / Mitsubishi FX5U.
   - Khi phát hiện `DEFECT`, worker tính toán khoảng cách từ vị trí camera đến vị trí tay gạt xi-lanh khí nén dựa trên tốc độ encoder băng tải, gửi tín hiệu kích hoạt van điện từ (Solenoid Valve) gạt chính xác chai lỗi vào thùng phế phẩm.
2. **Triển khai nhúng biên (Edge AI Deployment):**
   - Xuất mô hình sang định dạng **ONNX** và biên dịch sang **NVIDIA TensorRT (FP16 / INT8)**.
   - Triển khai trực tiếp trên máy tính nhúng công nghiệp **NVIDIA Jetson Orin Nano / Orin NX**, đạt tốc độ suy luận dự kiến **> 80 FPS**, điện năng tiêu thụ dưới 15W, hoạt động bền bỉ 24/7 trong môi trường bụi và ẩm.
3. **Thu thập dữ liệu thực địa & Session-based Fine-tuning:**
   - Thu thập 200–300 clip ngắn trực tiếp tại nhà máy đối tác với các chủng loại chai và nhãn mác khác nhau.
   - Chia tập theo phiên quay độc lập để loại bỏ hoàn toàn ảnh cận trùng, huấn luyện bổ sung (Active Learning) để đạt độ chính xác nghiệm thu thực tế trên 99.0%.

---

*Tài liệu này được biên soạn bởi Đội ngũ Kỹ sư Công nghệ Thông tin & Thị Giác Máy Tính Dự án ConveyorVision — Cập nhật đồng bộ cùng phiên bản hệ thống 2.0.0 (Tháng 10/2026).*
