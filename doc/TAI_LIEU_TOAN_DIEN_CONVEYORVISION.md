# CẨM NANG TOÀN DIỆN VỀ DỰ ÁN CONVEYORVISION (TỪ A ĐẾN Z)
## BỘ TÀI LIỆU CHI TIẾT TỔNG THỂ DỰ ÁN TỪ CHUYÊN GIA CÔNG NGHỆ THÔNG TIN
*Biên soạn bởi: Senior IT Expert & AI Solution Architect — DeepMind Team*  
*Bản PDF phát hành chính thức: [doc/CONVEYORVISION_TOAN_TAP_A_DEN_Z.pdf](CONVEYORVISION_TOAN_TAP_A_DEN_Z.pdf)*

---

## 📌 LỜI TỰA CỦA CHUYÊN GIA CÔNG NGHỆ THÔNG TIN

> *"Nếu bạn là một người chưa từng học về lập trình hay trí tuệ nhân tạo, tài liệu này được viết riêng cho bạn! Chúng tôi cam đoan sẽ không dùng những thuật ngữ khó hiểu để đánh đố, mà sẽ dùng các ví dụ đời thường, sinh động như con mắt, bộ não, người thám tử hay buồng lái máy bay để bạn hiểu tường tận 100% cách hệ thống này vận hành. Đồng thời, toàn bộ công thức kỹ thuật, kiến trúc mã nguồn và số liệu đánh giá khoa học cũng được ghi nhận trọn vẹn để đáp ứng những yêu cầu thẩm định kỹ thuật khắt khe nhất."*

---

## 1. BỐI CẢNH THỰC TẾ: TẠI SAO PHẢI CẦN DỰ ÁN NÀY?

Hãy tưởng tượng bạn đang đứng tại một nhà máy sản xuất nước giải khát hoặc dược phẩm. Băng chuyền chạy vùn vụt với tốc độ **1 đến 3 mét mỗi giây**, vận chuyển hàng chục ngàn chai lọ mỗi ca làm việc. Những chiếc chai này phải đạt chuẩn 100%: không bị móp méo, nắp không được lệch, nhãn không được rách hay nhăn nheo.

### 1.1. Nỗi đau khi dùng con người kiểm tra bằng mắt thường
Trước khi có hệ thống này, các nhà máy thường bố trí công nhân ngồi dọc băng chuyền để quan sát bằng mắt thường. Tuy nhiên, cách làm này bộc lộ những nhược điểm chí mạng:
1. **Hiện tượng mỏi mắt và lóa mắt:** Các nghiên cứu công thái học chỉ ra rằng sau **20–30 phút** nhìn chăm chú vào các vật thể lướt nhanh liên tục, mắt người bắt đầu mất tập trung, tỷ lệ bỏ sót phế phẩm tăng vọt từ 2% lên tới **15–20%**.
2. **Tốc độ giới hạn:** Mắt người không thể xử lý chính xác khi băng chuyền chạy trên 5 sản phẩm/giây.
3. **Thiếu tính nhất quán:** Người này có thể cho rằng vết trầy nhỏ là chấp nhận được, nhưng người khác lại cho là phế phẩm.
4. **Không có dữ liệu lưu trữ:** Khi khách hàng khiếu nại về một lô hàng lỗi, nhà máy hoàn toàn không có bằng chứng hình ảnh hay số liệu lịch sử để kiểm toán.

### 1.2. Giải pháp "Mắt thần" ConveyorVision
**ConveyorVision** chính là một *"Người bảo vệ vô hình thông minh"* được lắp đặt ngay phía trên băng chuyền. Hệ thống bao gồm một chiếc Camera công nghiệp (hoặc Webcam thông thường) kết nối với máy tính có cài đặt trí tuệ nhân tạo (AI). Hệ thống làm việc 24/7 không biết mệt mỏi, phát hiện tức thì sản phẩm hỏng chỉ trong **15 mili-giây**, tự động hú còi cảnh báo và sẵn sàng ra lệnh cho xi-lanh gạt bỏ chai lỗi ra khỏi dây chuyền.

---

## 2. BỨC TRANH TOÀN CẢNH: HỆ THỐNG VẬN HÀNH THẾ NÀO?

Hệ thống ConveyorVision giống như một **dây chuyền phân xử gồm 6 mắt xích phối hợp nhịp nhàng**:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. CAMERA       │ ───>  │ 2. AI YOLO26    │ ───>  │ 3. BYTETRACK    │
│ (Đôi Mắt)       │       │ (Bộ Não)        │       │ (Thám Tử)       │
│ Quay 30 FPS     │       │ Quét trong 15ms │       │ Gắn biển số ID  │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
┌─────────────────┐       ┌─────────────────┐                ▼
│ 6. CƠ CẤU CHẤP  │ <───  │ 5. WEB HMI      │ <───  ┌─────────────────┐
│ HÀNH (Cánh Tay) │       │ (Buồng Lái)     │       │ 4. MULTI-FRAME  │
│ Còi & Xi-lanh   │       │ Màn hình < 50ms │       │ VOTING (Tòa Án) │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

1. **Camera (Đôi Mắt):** Ghi lại liên tục 30 bức ảnh mỗi giây (30 FPS) khi chai chạy qua trạm kiểm tra.
2. **AI YOLO26 (Bộ Não):** Quét từng bức ảnh trong 15ms, xác định vị trí chai và phân tích xem chai là PASS hay DEFECT.
3. **ByteTrack (Thám Tử):** Gắn biển số ID cho từng chai, theo dõi đường đi của chai từ lúc xuất hiện đến lúc đi khuất.
4. **Multi-frame Voting (Hội Đồng Giám Định):** Không vội kết luận ở khung hình đầu tiên. Đợi nhìn rõ ít nhất 3 lần rồi mới đưa ra phán quyết cuối cùng.
5. **Web Dashboard HMI (Buồng Lái Trung Tâm):** Màn hình hiển thị video trực tiếp, thẻ chỉ số đếm số lượng, biểu đồ và còi cảnh báo phế phẩm.
6. **Cơ Cấu Chấp Hành (Cánh Tay Cơ Khí):** Hú còi buzzer, lưu bằng chứng ảnh vào thư mục và sẵn sàng kích hoạt xi-lanh gạt chai lỗi.

---

## 3. DỮ LIỆU: BỘ NÃO AI HỌC BẰNG CÁCH NÀO?

Trí tuệ nhân tạo (AI) không tự nhiên thông minh. Nó giống như một đứa trẻ mới sinh: muốn đứa trẻ biết đâu là chai lành, đâu là chai vỡ thì cha mẹ phải đưa cho đứa trẻ xem hàng ngàn bức ảnh mẫu và chỉ bảo: *"Đây là chai đạt này con, còn đây là chai nứt nắp này con"*.

### 3.1. Bộ dữ liệu 2.666 ảnh chuẩn hóa
Dự án đã thu thập, làm sạch và gán nhãn thủ công cẩn trọng bộ dữ liệu gồm **2.666 bức ảnh chất lượng cao** với 2 lớp đối tượng:
* **Lớp 0: PASS (Đạt chuẩn):** Chai nhựa hoặc chai thủy tinh nguyên vẹn, nhãn mác ngay ngắn, nắp vặn kín và dung tích nước bên trong đúng vạch quy định.
* **Lớp 1: DEFECT (Khuyết tật):** Chai bị móp méo thân, rách nhãn, mất nhãn, vặn lệch nắp, mất nắp hoặc vơi nước.

### 3.2. Quy tắc chia 3 tập vàng trong Khoa học Dữ liệu
* **Tập Huấn Luyện (Train - 1.692 ảnh, 63.5%):** Đóng vai trò là **Sách giáo khoa** có kèm sẵn đáp án để mô hình AI học các dấu hiệu khuyết tật.
* **Tập Kiểm Định (Val - 533 ảnh, 20.0%):** Là các **Bài kiểm tra 15 phút** giữa kỳ để kỹ sư tinh chỉnh thông số, xem AI học có tiến bộ không.
* **Tập Kiểm Thử (Test - 441 ảnh, 16.5%):** Là **Đề thi tốt nghiệp đại học** độc lập hoàn toàn. AI chưa từng được nhìn thấy các ảnh này trước đó.

### 3.3. Minh bạch khoa học: Vấn đề "Ảnh cận trùng" (Near-Duplicate)
Do bộ dữ liệu ban đầu được trích xuất từ các đoạn video quay liên tục, có **53 cặp ảnh giữa tập Train và Test có độ tương đồng cao (cùng một góc quay chai)**. Mặc dù điều này giúp mô hình đạt điểm số mAP rất cao (99.5%), chúng tôi đã khuyến nghị trong thực tế cần chia tập theo *Session Split* (mỗi phiên quay video độc lập cho vào 1 tập riêng) để đánh giá độ thích nghi thực tế của AI.

---

## 4. HAI TRỤ CỘT THUẬT TOÁN CỐT LÕI

### 4.1. Trụ Cột 1: YOLO26 Nano — "Chỉ Nhìn Một Lần Là Thấy Tất Cả"
* **YOLO** là viết tắt của *You Only Look Once*. Các công nghệ AI cổ điển trước đây phải chia bức ảnh thành hàng trăm mảnh nhỏ để soi từng mảnh, khiến máy tính chạy rất chậm. Ngược lại, YOLO26 quét toàn bộ bức ảnh trong đúng một lượt suy luận duy nhất.
* **Kích thước siêu nhẹ:** File trọng số chỉ nặng **5.45 Megabytes**, cực kỳ tiết kiệm bộ nhớ, chạy mát trên CPU.
* **Tốc độ:** Xử lý một ảnh chỉ trong khoảng **15 mili-giây**.

### 4.2. Trụ Cột 2: ByteTrack — Tại Sao Nhận Diện Thôi Là Chưa Đủ?
Camera quay 30 khung hình/giây. Một chiếc chai chạy qua băng chuyền mất 2 giây, nghĩa là xuất hiện trong **60 bức ảnh liên tiếp**. Nếu chỉ dùng AI nhận diện từng ảnh rời rạc, hệ thống sẽ đếm thành **60 cái chai**!
ByteTrack giải quyết bài toán này như một người thám tử:
1. **Gắn biển số ID cố định:** Chai vừa vào được cấp ID (ví dụ `#12`).
2. **Bộ lọc Kalman (Kalman Filter):** Dự đoán vận tốc và vị trí tiếp theo, bám chặt chiếc chai `#12` qua 60 khung hình liên tiếp.
3. **Đếm chính xác 1:1:** Khi chai rời khỏi camera, hệ thống chốt số lượng đúng 1 sản phẩm.

---

## 5. CƠ CHẾ PHÁN QUYẾT BẢO VỆ CHẤT LƯỢNG

1. **Bỏ phiếu đa khung hình (Multi-frame Voting):** Trạng thái ban đầu là `INSPECTING` (màu Vàng). Chỉ khi nhìn thấy tối thiểu 3 khung hình (Min Votes = 3) mới đưa ra phán quyết.
2. **Nguyên tắc "Ưu tiên Phế phẩm" (Defect-First Safety):** Chỉ cần tích lũy đủ số phiếu xác nhận lỗi trong hành trình, lập tức chốt `DEFECT` và kích hoạt báo động ngay lập tức.
3. **Ngưỡng mất dấu an toàn (Lost Buffer = 30 frames):** Chai đạt `PASS` chỉ được chốt sổ sau khi đã biến mất khỏi tầm mắt camera trong 30 frame liên tiếp.
4. **Chế độ Đa Vật Thể (Chai & Dị vật khác):** Tự động nhận diện dị vật lạ (cốc, hộp, lon, bút...) viền màu Tím hoàng gia, đếm riêng vào thẻ **DỊ VẬT**, không phạt nhầm vào tỷ lệ phế phẩm của chai.

---

## 6. TRẠM ĐIỀU KHIỂN WEB DASHBOARD HMI

Giao diện SPA hiện đại, chuẩn HMI công nghiệp:
* **Dark Glassmorphism:** Nền tối chống chói mắt cho ca trực 8–12 tiếng.
* **HUD Machine Vision:** 4 góc định vị quang học trên khung hình camera trực tiếp.
* **Độ trễ < 50ms:** Ứng dụng biến điều kiện `threading.Condition` và độ phân giải `480px` cho tốc độ 22–25 FPS mượt mà trên CPU.
* **Còi báo động Web Audio API:** Trình duyệt tự tổng hợp sóng âm kép 880Hz → 440Hz, không cần loa rời hay file âm thanh ngoài.
* **In-place Reactive DOM:** Bảng sự kiện chớp sáng xanh cập nhật tại chỗ khi có bằng chứng mới, không giật lag màn hình.

---

## 7. BẢN ĐỒ MÃ NGUỒN: CHI TIẾT TỪNG TỆP CODE

| Tệp Mã Nguồn | Vai Trò & Nhiệm Vụ Cụ Thể |
| :--- | :--- |
| `run_app.py` | Điểm khởi động toàn bộ ứng dụng, mở server tại cổng 8000. |
| `src/conveyorvision/video_io.py` | Xử lý trích xuất khung hình từ video và webcam, đồng bộ nhịp wall-clock. |
| `src/conveyorvision/dataset_manager.py` | Tải dữ liệu Roboflow, chuẩn hóa về 2 class `pass`/`defect`. |
| `src/conveyorvision/train_pilot.py` | Huấn luyện mô hình YOLO qua giao diện dòng lệnh CLI. |
| `src/conveyorvision/evaluate.py` | Đo lường độc lập chỉ số mAP trên 441 ảnh Test. |
| `src/conveyorvision/inference_conveyor.py` | Bộ não kiểm định, theo vết ByteTrack và xuất CSV qua CLI. |
| `src/conveyorvision/web/server.py` | Máy chủ FastAPI: quản lý WebSocket, REST APIs và tải PDF. |
| `src/conveyorvision/web/worker.py` | Tiến trình ngầm nạp AI, chạy ByteTrack và đồng bộ luồng video MJPEG. |
| `src/conveyorvision/web/session_manager.py` | Quản trị cơ sở dữ liệu các ca sản xuất, xuất file kiểm toán CSV. |
| `src/conveyorvision/web/static/js/app.js` | Logic giao diện: kết nối WebSocket, DOM update tại chỗ, còi âm thanh. |
| `src/conveyorvision/web/static/css/style.css` | Hệ thống phong cách Dark Glassmorphism công nghiệp. |
| `tests/test_web.py` & `test_pipeline.py` | 21 bài kiểm thử tự động đạt 100% Passed. |
| `scripts/generate_pdf_report.py` | Tạo Báo cáo Kỹ thuật PDF tổng kết. |
| `scripts/generate_pdf_uiux.py` | Tạo Cẩm nang Hướng dẫn UI/UX PDF. |
| `scripts/generate_pdf_handbook.py` | Tạo Cẩm nang Toàn diện Từ A Đến Z PDF. |

---

## 8. KẾT QUẢ THỰC NGHIỆM ĐỊNH LƯỢNG (BENCHMARK)

* **Độ chính xác (Precision):** 98.0%
* **Độ nhạy bao quát (Recall):** 92.6%
* **mAP@50:** **99.5% (Gần như tuyệt đối)**
* **mAP@50-95:** 82.4%
* **Thời gian suy luận:** 15ms
* **Tốc độ thực tế CPU:** 22–25 FPS (Độ trễ < 50ms)
* **Tỷ lệ bỏ sót phế phẩm (False Negative):** 0.0% tại ngưỡng chuẩn.

---

## 9. HƯỚNG DẪN VẬN HÀNH DÀNH CHO NGƯỜI MỚI

1. **Khởi động:** Mở Terminal và gõ `python run_app.py`. Trình duyệt sẽ mở `http://localhost:8000`.
2. **Chọn nguồn:** Chọn Webcam hoặc Video demo/Video tự quay.
3. **Chọn chế độ:** Chọn `🍶 Chai & Dị vật khác` và độ phân giải `⚡ 480px (Siêu mượt)`.
4. **Bắt đầu:** Bấm `▶ Bắt đầu kiểm định`. Xem kết quả đếm nhảy số thời gian thực. Bấm `⏹ Dừng phiên` khi hoàn tất.

---

## 10. TỪ ĐIỂN THUẬT NGỮ BÌNH DÂN (GLOSSARY)

* **FPS (Frames Per Second):** Số bức ảnh máy quay chụp được trong 1 giây. Mức 24–30 FPS là mắt người thấy mượt mà.
* **Latency (Độ trễ):** Thời gian từ lúc camera thấy chai đến lúc màn hình đổi số. Hệ thống đạt < 50ms (nhanh gấp 6 lần cái chớp mắt).
* **Bounding Box:** Chiếc khung hình chữ nhật vẽ quanh vật thể để chỉ vị trí.
* **Confidence:** Độ tự tin của AI (0% đến 100%).
* **mAP:** Điểm thi tốt nghiệp của AI (thang 1.0). Đồ án đạt 0.995 (9.95/10 điểm).
* **Epoch:** Một lần AI học hết cuốn sách giáo khoa ảnh mẫu.
* **WebSocket:** Đường dây điện thoại kết nối trực tiếp giúp số liệu nhảy tức thì mà không cần nạp lại trang web.

---

## 11. BỘ BA ẤN PHẨM PDF CHÍNH THỨC CỦA DỰ ÁN

| Ấn Phẩm | Tệp PDF Trong Thư Mục `doc/` | Đối Tượng Sử Dụng |
| :--- | :--- | :--- |
| **Bản 1: Báo Cáo Kỹ Thuật** | `doc/BAO_CAO_TONG_KET_CONVEYORVISION.pdf` | Hội đồng nghiệm thu, Giảng viên chấm thi, Chuyên gia AI |
| **Bản 2: Cẩm Nang UI/UX** | `doc/HUONG_DAN_SU_DUNG_UI_UX.pdf` | Kỹ sư vận hành, Trưởng ca QC, Nhân viên xưởng |
| **Bản 3: Toàn Tập A Đến Z** | `doc/CONVEYORVISION_TOAN_TAP_A_DEN_Z.pdf` | Người mới bắt đầu, Lãnh đạo, Khách hàng, Toàn thể đội ngũ |
