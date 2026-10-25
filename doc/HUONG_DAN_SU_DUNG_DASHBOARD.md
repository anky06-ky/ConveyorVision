# Hướng Dẫn Sử Dụng Dashboard ConveyorVision (Version 2.0)

Tài liệu hướng dẫn cài đặt, khởi chạy và vận hành hệ thống kiểm định thị giác máy tính công nghiệp **ConveyorVision** trên môi trường máy trạm hoặc máy tính điều khiển.

---

## 1. Khởi Chạy Nhanh Hệ Thống

Mở terminal PowerShell tại thư mục dự án và kích hoạt ứng dụng:

```powershell
cd D:\ConveyorVision
.\.venv\Scripts\python.exe run_app.py
```

Khi server hiển thị thông báo:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
Mở trình duyệt web (Google Chrome, Microsoft Edge, Cốc Cốc, Brave...) và truy cập địa chỉ:
👉 **`http://127.0.0.1:8000`**

*(Giữ cửa sổ terminal mở trong suốt quá trình sử dụng; nhấn `Ctrl+C` trong terminal để tắt server khi kết thúc ca làm việc).*

---

## 2. Các Màn Hình Chức Năng Chính

Dashboard gồm **6 màn hình nghiệp vụ** được bố trí trực quan trên thanh điều hướng bên trái:

1. **Tổng quan (Overview):** Xem 4 chỉ số KPI vĩ mô (Tổng sản phẩm, PASS, DEFECT, Tỷ lệ lỗi %) và danh sách 5 phiên làm việc gần nhất.
2. **Kiểm định trực tiếp (Live Inspection):**
   * Chọn nguồn kiểm tra: Video demo có sẵn, Webcam USB, hoặc tải file video tự quay lên.
   * Lựa chọn **Chế độ kiểm định**:
     * `🍶 Chai & Dị vật khác (Tự quay)`: Tự động phân tách Chai lọ khỏi các vật thể lạ (hộp, cốc, lon, điện thoại...).
     * `🔍 QC Chai Đạt / Lỗi (Chuyên sâu)`: Kiểm định chất lượng nắp, nhãn, thể tích chai chuyên sâu trên băng tải.
   * Chọn độ phân giải: `⚡ 480px (Siêu mượt, >20 FPS trên CPU)` hoặc `🎯 640px (Chuẩn)`.
   * Các nút vận hành: **`▶ Bắt đầu kiểm định`**, **`⏸ Tạm dừng`**, **`⏹ Dừng phiên`**, **`📸 Chụp hiện trường`**.
   * Bảng nhật ký thời gian thực tự động cập nhật tại chỗ (in-place update) theo từng Track ID.
   * Còi báo động buzzer (Web Audio API) tự động kêu khi phát hiện chai lỗi hoặc dị vật.
3. **Lịch sử kiểm định (History):** Tra cứu toàn bộ các phiên làm việc, xem chi tiết từng chai hoặc tải file kiểm toán định dạng `.csv`.
4. **Đánh giá mô hình (Model Evaluation):** Tra cứu chỉ số kiểm thử trên 441 ảnh test độc lập (mAP@50 = 82.5%, Recall phế phẩm = 85.4%), benchmark tốc độ thực tế và xem phóng to các biểu đồ PR Curve, Confusion Matrix.
5. **Dữ liệu & Mô hình (Dataset & Models):** Xem cấu trúc 2.666 ảnh chuẩn hóa và danh sách các file checkpoint `.pt` sẵn sàng.
6. **Cài đặt (Settings):** Cấu hình thuật toán theo vết (ByteTrack/BoT-SORT), số frame mất dấu (Lost Frame Buffer), số vote quan sát tối thiểu, tự động xuất CSV và bật/tắt còi buzzer. Cấu hình được lưu trực tiếp vào backend qua file `reports/settings.json`.

---

## 3. Tải Báo Cáo Nghiệm Thu & Cẩm Nang UI/UX

* Trên thanh tiêu đề (Top Header) ở mọi màn hình:
  * Bấm nút **`📥 Tải Báo Cáo PDF`** để tải về bản **Báo cáo nghiệm thu kỹ thuật hoàn chỉnh** (định dạng PDF chính thức).
  * Bấm nút **`📖 Hướng Dẫn UI/UX`** hoặc biểu tượng trợ giúp **`ℹ️`** để xem cẩm nang thao tác và giải nghĩa chi tiết ngay trên giao diện.

---

## 4. Xử Lý Sự Cố Nhanh

* **Không nghe thấy tiếng còi báo lỗi:** Nhấp chuột một lần vào trang web để cấp quyền âm thanh trình duyệt (Browser Autoplay Policy); đảm bảo công tắc còi âm thanh đang bật.
* **Stream video bị chậm/lag:** Tại thanh điều khiển, đổi phân giải suy luận sang **`⚡ 480px (Siêu mượt)`**. Hệ thống đã được tối ưu hóa luồng frame condition variable, đạt tốc độ 20–25 FPS mượt mà trên CPU.
* **Phát hiện nhầm các đồ vật khác thành phế phẩm:** Chuyển sang chế độ **`🍶 Chai & Dị vật khác (Tự quay)`**.
