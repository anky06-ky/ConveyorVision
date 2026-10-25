# TÀI LIỆU HƯỚNG DẪN SỬ DỤNG GIAO DIỆN & TRẢI NGHIỆM NGƯỜI DÙNG (UI/UX USER GUIDE)
## HỆ THỐNG THỊ GIÁC MÁY TÍNH KIỂM ĐỊNH BĂNG CHUYỀN CONVEYORVISION (VERSION 2.0)

---

## 1. Triết Lý Thiết Kế UI/UX (Industrial HMI Design System)

Giao diện **ConveyorVision** được thiết kế theo chuẩn **HMI (Human-Machine Interface)** công nghiệp với các nguyên tắc cốt lõi:

* **Chủ đề Dark Navy Slate tối ưu thị giác:** Giảm tối đa hiện tượng mỏi mắt cho kỹ sư và công nhân vận hành khi phải theo dõi màn hình camera kiểm tra liên tục trong ca làm việc 8–12 tiếng.
* **Độ tương phản cao & Mã màu tiêu chuẩn quốc tế:**
  * <span style="color:#10b981; font-weight:bold;">Xanh ngọc lục bảo (Emerald Green #10b981):</span> Sản phẩm Đạt chuẩn (`PASS`) / Trạng thái sẵn sàng (`RUNNING/READY`).
  * <span style="color:#ef4444; font-weight:bold;">Đỏ thẫm cảnh báo (Crimson Red #ef4444):</span> Phế phẩm khuyết tật (`DEFECT`) / Lỗi hệ thống (`ERROR`).
  * <span style="color:#c084fc; font-weight:bold;">Tím hồng công nghệ (Violet Magenta #c084fc):</span> Dị vật / Vật thể lạ ngoài danh mục chai lọ (`OTHER`).
  * <span style="color:#f59e0b; font-weight:bold;">Vàng hổ phách (Amber Gold #f59e0b):</span> Đang kiểm tra (`INSPECTING`) / Tạm dừng (`PAUSED`).
  * <span style="color:#0284c7; font-weight:bold;">Xanh công nghiệp (Industrial Cyan #0284c7):</span> Thông số kỹ thuật, tỷ lệ phần trăm và nút thao tác chính.
* **Cập nhật tại chỗ không giật lag (In-place Reactive DOM):** Bảng sự kiện và các thẻ chỉ số được cập nhật trực tiếp tại từng phần tử DOM thông qua WebSocket, không tải lại toàn trang hay re-render gây giật hình.
* **Độ trễ thấp & Đồng bộ nhịp thực tế:** Luồng truyền hình ảnh MJPEG áp dụng biến điều kiện `threading.Condition` kết hợp độ phân giải 480px, đưa độ trễ từ camera đến màn hình mắt người quan sát xuống dưới **50 ms** (~22–25 FPS trên CPU).

---

## 2. Sơ Đồ Cấu Trúc & Luồng Trải Nghiệm (Navigation Architecture)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 CONVEYORVISION DASHBOARD SPA                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ├── 🏠 MÀN HÌNH 1: TỔNG QUAN (Overview)
         │      ├── 4 Thẻ KPI vĩ mô (Tổng quét, PASS, DEFECT, Tỷ lệ lỗi %)
         │      ├── Nhật ký các phiên kiểm định gần nhất (Recent Sessions Table)
         │      ├── Nút chuyển nhanh đến trạm kiểm định
         │      └── Bảng thông số phần cứng & mô hình
         │
         ├── 🎥 MÀN HÌNH 2: KIỂM ĐỊNH TRỰC TIẾP (Live Inspection - Trọng Tâm)
         │      ├── Thanh điều khiển Cockpit 2 tầng (Nguồn, Upload, Chế độ, Model, Resolution, Conf, Tracker)
         │      ├── 4 Nút thao tác vận hành (Bắt đầu, Tạm dừng, Dừng phiên, Chụp hiện trường)
         │      ├── Khung hiển thị Video trực tiếp + HUD thời gian thực + Cờ cảnh báo loại bỏ
         │      ├── 5 Thẻ Mini-KPI (PASS, DEFECT, ĐANG QUÉT, TỶ LỆ LỖI %, DỊ VẬT)
         │      ├── Công tắc Còi báo động Web Audio API
         │      └── Bảng nhật ký sản phẩm thời gian thực (In-place Row Update)
         │
         ├── 🗄️ MÀN HÌNH 3: LỊCH SỬ KIỂM ĐỊNH (History)
         │      ├── Bảng tổng hợp tất cả các phiên làm việc
         │      ├── Modal xem chi tiết từng track ID (thời gian, confidence, số frame quan sát)
         │      ├── Tải file kiểm toán CSV về máy
         │      └── Xóa phiên không cần thiết
         │
         ├── 📊 MÀN HÌNH 4: ĐÁNH GIÁ MÔ HÌNH (Evaluation)
         │      ├── Cảnh báo minh bạch khoa học về rủi ro rò rỉ ảnh cận trùng (Near-Duplicate)
         │      ├── Bảng chỉ số độc lập trên 441 ảnh Test (Precision, Recall, mAP50, mAP50-95)
         │      ├── Benchmark tốc độ suy luận thực tế CPU vs Dự kiến GPU
         │      └── Bộ xem biểu đồ trực quan hóa (PR Curve, Confusion Matrix, Loss Progression)
         │
         ├── 📦 MÀN HÌNH 5: DỮ LIỆU & MÔ HÌNH (Dataset & Models)
         │      ├── Tỷ lệ phân bổ tập dữ liệu chuẩn hóa (Train: 1.692, Val: 533, Test: 441)
         │      └── Danh mục và dung lượng các file trọng số (*.pt) có sẵn trong trạm
         │
         └── ⚙️ MÀN HÌNH 6: CÀI ĐẶT (Settings)
                ├── Cấu hình thuật toán theo vết mặc định (ByteTrack / BoT-SORT)
                ├── Ngưỡng mất dấu trước khi chốt PASS (Lost Frame Buffer)
                ├── Số frame quan sát tối thiểu để loại bỏ nhiễu biên (Min Observation Votes)
                ├── Bật/tắt tự động lưu file CSV kiểm toán
                ├── Bật/tắt còi cảnh báo âm thanh
                └── Nút "Lưu cấu hình" đồng bộ thẳng tới backend máy chủ
```

---

## 3. Hướng Dẫn Thao Tác Chi Tiết Từng Màn Hình

### 3.1. Màn Hình 1: Tổng Quan (Overview)

* **Mục đích:** Cung cấp cái nhìn toàn cảnh về hiệu suất vận hành của dây chuyền và lịch sử các ca sản xuất.
* **Các thành phần chính:**
  1. **Thẻ KPI tổng thể:** Hiển thị tổng số sản phẩm đã qua trạm, số lượng chai đạt, số lượng chai lỗi và tỷ lệ lỗi bình quân cộng dồn.
  2. **Bảng phiên gần nhất:** Liệt kê 5 ca kiểm định gần nhất kèm thông tin thời gian và nguồn video. Bấm nút **"Xem tất cả"** để nhảy nhanh sang trang Lịch sử.
  3. **Thao tác nhanh:** Bấm nút **"▶ Chuyển đến Trực tiếp"** để vào ngay trạm quan sát camera.

---

### 3.2. Màn Hình 2: Kiểm Định Trực Tiếp (Live Inspection)

Đây là **màn hình vận hành chính** của người thao tác máy hoặc kỹ sư kiểm tra chất lượng.

#### Bước 1: Thiết lập tham số tại Thanh điều khiển 2 tầng
* **Nguồn kiểm định:**
  * Chọn `🎥 Video Demo (Mô phỏng)` để chạy video băng tải mẫu có sẵn trong thư mục `raw_videos/`.
  * Chọn `📷 Webcam 0 (USB Camera)` để quét hình ảnh từ camera kết nối trực tiếp với máy tính.
* **Tải file video lên:** Bấm nút **"Choose File"** để tải video thực tế do bạn quay (`.mp4`, `.avi`, `.mov`, `.mkv`). Hệ thống tự động kiểm tra bảo mật, đổi tên an toàn và tự chọn file mới vào danh sách nguồn.
* **Chế độ kiểm định (Cực kỳ quan trọng):**
  * `🍶 Chai & Dị vật khác (Tự quay)`: **Khuyên dùng cho video thực tế tự quay bằng điện thoại**. Hệ thống sẽ tự động tách biệt Chai lọ (viền Xanh lá) khỏi các đồ vật khác trên băng tải (cốc, hộp, lon, điện thoại, sách... viền Tím hồng).
  * `🔍 QC Chai Đạt / Lỗi (Chuyên sâu)`: Phù hợp cho dây chuyền chuẩn. Hệ thống tập trung bắt các khuyết tật của chai: nắp lệch, rách nhãn, vơi mức nước (`PASS` viền Xanh, `DEFECT` viền Đỏ).
* **Checkpoint mô hình:** Chọn file trọng số phù hợp (mặc định: `conveyor_yolo26_30ep_best.pt` hoặc mô hình COCO).
* **Độ phân giải suy luận:**
  * `⚡ 480px (Siêu mượt)`: **Khuyên dùng cho CPU**, tốc độ đạt 22–25 FPS, giảm 50% băng thông, độ trễ &lt; 50ms.
  * `🎯 640px (Chuẩn)`: Cho camera công nghiệp độ nét cao hoặc máy tính có GPU rời.
* **Ngưỡng tin cậy (Conf Slider):** Kéo thanh trượt từ `0.10` đến `0.90` (mức chuẩn: `0.45`). Kéo sang phải để giảm phát hiện nhầm; kéo sang trái để nhạy hơn với vết lỗi mờ.
* **Tracker:** Chọn `ByteTrack` (tốc độ cao, tối ưu vật thể chuyển động thẳng) hoặc `BoT-SORT` (kèm trích xuất đặc trưng ngoại hình khi camera bị rung).

#### Bước 2: Vận hành kiểm tra
* Bấm **`▶ Bắt đầu kiểm định`**: Nút chuyển sang trạng thái đang chạy ngay tức thì; luồng camera và HUD bắt đầu quét.
* Bấm **`⏸ Tạm dừng` / `▶ Tiếp tục`**: Dừng tạm thời khung hình để người kiểm tra quan sát kỹ chi tiết một sản phẩm nghi vấn.
* Bấm **`📸 Chụp hiện trường`**: Chụp lại ngay khung hình hiện tại kèm nhãn bounding box, lưu vào thư mục `reports/snapshots/`.
* Bấm **`⏹ Dừng phiên`**: Kết thúc ca kiểm định, chốt số liệu thống kê cuối cùng và tự động xuất file báo cáo CSV.
* Bấm **`⛶ Phóng to`**: Mở chế độ camera toàn màn hình trên máy chiếu hoặc màn hình điều khiển lớn tại xưởng.

#### Bước 3: Đọc hiểu HUD và Bảng nhật ký thời gian thực
* **Khung viền trên video:**
  * Khung Xanh lá: Chai đạt chuẩn (`PASS`).
  * Khung Đỏ: Chai phế phẩm khuyết tật (`DEFECT`).
  * Khung Tím hồng: Dị vật / Vật thể lạ trên băng tải (`Vật thể khác: <Tên Tiếng Việt>`).
* **Cờ cảnh báo nhấp nháy đỏ phía trên video:** Xuất hiện khi phát hiện chai lỗi hoặc dị vật nguy hiểm, kèm âm thanh còi báo động kép (880Hz &rarr; 440Hz).
* **Bảng nhật ký sản phẩm (Event Log):** Mỗi sản phẩm có một mã `#ID` riêng biệt. Khi sản phẩm có thêm bằng chứng xác nhận lỗi, dòng sự kiện tương ứng sẽ **chớp sáng xanh và tự cập nhật tại chỗ** (In-place Update), không tạo thêm dòng rác gây rối mắt.

---

### 3.3. Màn Hình 3: Lịch Sử Kiểm Định (Inspection History)

* **Xem lại danh sách:** Bảng thống kê toàn bộ các phiên đã kiểm tra trong quá khứ kèm ngày giờ, thời lượng, số lượng PASS, DEFECT và tỷ lệ lỗi.
* **Nút "Chi tiết":** Bấm để mở hộp thoại hiển thị danh sách từng chai trong phiên đó: mã Track ID, mức độ tin cậy cao nhất, thời gian xuất hiện trên băng tải, trạng thái chốt và ghi chú hiệu chỉnh.
* **Nút "Tải CSV":** Bấm để tải file bảng tính Excel/CSV chứa dữ liệu chi tiết từng mili-giây phục vụ lưu trữ kiểm toán ISO/HACCP.
* **Nút "✕":** Xóa bỏ các phiên chạy thử nghiệm không cần lưu lại.

---

### 3.4. Màn Hình 4: Đánh Giá Mô Hình (Model Evaluation)

* **Bảng chỉ số kiểm thử độc lập (Test Set):** Trình bày chi tiết chỉ số Precision, Recall, mAP@50, mAP@50-95 của lớp `pass` và lớp `defect`.
* **Khung cảnh báo dữ liệu cận trùng (Near-Duplicate Leakage):** Nêu rõ lưu ý khoa học về 53–54 cặp ảnh cận trùng và sự khác biệt giữa Recall 85.4% toàn dải so với ma trận nhầm lẫn tại ngưỡng cắt tĩnh `conf=0.25`.
* **Đo lường tốc độ suy luận (Benchmark):** Thể hiện chi tiết thời gian tiền xử lý (3.1ms), suy luận (125.9ms trên CPU) và hậu xử lý (2.4ms).
* **Tab chuyển đổi biểu đồ trực quan:**
  * Bấm chọn giữa các tab: `Tiến trình Loss & mAP`, `Ma trận nhầm lẫn Test`, `Đường cong PR Test`, `Dự đoán mẫu Test batch`.
  * Nhấp chuột trực tiếp vào ảnh biểu đồ để **phóng to toàn màn hình** kiểm tra từng trục tọa độ.

---

### 3.5. Màn Hình 5: Dữ Liệu & Mô Hình (Dataset & Models)

* Xem tổng quan phân bổ của 2.666 ảnh được chuẩn hóa theo tỷ lệ chuẩn:
  * Tập Huấn luyện (Train): 1.692 ảnh (63.5%)
  * Tập Kiểm định (Val): 533 ảnh (20.0%)
  * Tập Kiểm thử (Test): 441 ảnh (16.5%)
* Xem danh sách các file weights `.pt` tìm thấy trong thư mục dự án cùng dung lượng và ngày sửa đổi.

---

### 3.6. Màn Hình 6: Cài Đặt (Settings)

* **Thuật toán theo vết:** Lựa chọn giữa `ByteTrack` và `BoT-SORT`.
* **Ngưỡng mất dấu chốt PASS (Lost Frame Buffer):** Mặc định 30 khung hình. Nếu camera không nhìn thấy chai trong 30 frame liên tiếp, chai được xác định đã an toàn đi qua trạm kiểm định.
* **Số frame quan sát tối thiểu (Min Observation Votes):** Mặc định 3 khung hình. Tránh nhận diện rác ở viền góc camera.
* **Tự động xuất CSV:** Tự động tạo file log vào `reports/` sau mỗi phiên.
* **Bật/tắt còi báo động:** Bật hoặc tắt âm thanh còi buzzer trên trình duyệt.
* **Bấm "Lưu cấu hình":** Hệ thống lưu vào file `reports/settings.json` trên máy chủ và hiển thị thông báo `✓ Đã lưu cài đặt` màu xanh.

---

## 4. Bảng Phím Tắt & Thao Tác Nhanh (Keyboard Shortcuts)

| Phím bấm / Thao tác | Vị trí màn hình | Chức năng thực hiện |
| :--- | :--- | :--- |
| **Bấm vào Logo ConveyorVision** | Góc trên bên trái | Chuyển nhanh về màn hình Tổng quan (Overview) |
| **Bấm nút 📥 Tải Báo Cáo PDF** | Thanh Header góc trên | Tải ngay bản báo cáo nghiệm thu kỹ thuật hoàn chỉnh (PDF) |
| **Bấm nút 📖 Hướng Dẫn UI/UX** | Thanh Header góc trên | Mở cửa sổ cẩm nang hướng dẫn sử dụng tương tác |
| **Bấm vào ảnh biểu đồ** | Màn hình Đánh giá | Phóng to toàn màn hình xem chi tiết đường cong PR và Loss |
| **Phím ESC** | Toàn hệ thống | Đóng nhanh tất cả các cửa sổ Modal đang mở |
| **Bấm nút ⛶ Phóng to** | Góc dưới khung video | Chuyển khung camera trực tiếp sang chế độ Fullscreen |

---

## 5. Xử Lý Các Tình Huống Vận Hành Thường Gặp (Troubleshooting)

| Tình huống phát sinh | Nguyên nhân khả dĩ | Hướng dẫn khắc phục nhanh |
| :--- | :--- | :--- |
| **Trình duyệt không phát tiếng còi khi có lỗi** | Trình duyệt chặn âm thanh tự động (Autoplay Policy) | Nhấp chuột vào bất kỳ vị trí nào trên trang web để kích hoạt quyền âm thanh Web Audio API; kiểm tra nút bật âm thanh bên phải màn hình. |
| **Video phát có cảm giác giật hoặc chậm** | Đang để độ phân giải 640px trên máy tính không có GPU rời | Tại thanh điều khiển, đổi mục **"Độ phân giải suy luận"** từ `640px` sang **`⚡ 480px (Siêu mượt)`** để tăng tốc độ lên 22–25 FPS. |
| **Webcam hiển thị màn hình đen** | Một ứng dụng khác (Zoom, Teams, Camera app) đang chiếm webcam | Tắt các ứng dụng đang dùng webcam, chọn lại `Webcam 0` và bấm Bắt đầu. |
| **Có nhiều vật thể khác ngoài chai bị báo lỗi đỏ** | Đang chạy chế độ kiểm định QC chai trên video tự quay nhiều đồ vật | Đổi mục **"Chế độ kiểm định"** sang **`🍶 Chai & Dị vật khác (Tự quay)`**. Khi đó các đồ vật khác sẽ được khoanh viền tím hồng và đếm riêng vào mục Dị vật, không bị phán quyết nhầm thành phế phẩm. |
| **Tải video lên báo lỗi** | Định dạng file không hợp lệ hoặc dung lượng vượt quá 200MB | Chỉ tải các file video có đuôi `.mp4`, `.avi`, `.mov`, `.mkv` và dung lượng dưới 200MB. |

---

*Tài liệu này được biên soạn bởi Đội ngũ Phát triển ConveyorVision — Cập nhật cùng phiên bản Web Dashboard 2.0.0.*
