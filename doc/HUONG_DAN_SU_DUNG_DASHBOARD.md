# Hướng dẫn sử dụng Dashboard ConveyorVision

> Tài liệu này hướng dẫn dùng giao diện hiện có trong repo. Một số mục trong giao diện đang là bản trình diễn và chưa điều khiển cấu hình thật; xem phần **Cách đọc kết quả và giới hạn mô hình** trước khi demo.

## 1. Khởi chạy

Mở PowerShell tại thư mục dự án:

```powershell
cd D:\ConveyorVision
.\.venv\Scripts\python.exe run_app.py
```

Nếu môi trường ảo chưa được tạo, tạo môi trường và cài thư viện theo README. Khi server báo đã chạy, mở `http://127.0.0.1:8000` trong trình duyệt. Giữ cửa sổ terminal mở trong lúc dùng Dashboard; nhấn `Ctrl+C` trong terminal để tắt server.

Trước khi chạy kiểm định, kiểm tra:

- Có checkpoint mô hình ở `models/conveyor_yolo26_30ep_best.pt` (file `.pt` không được lưu trong Git; cần chép file đã tải từ Colab vào đây).
- Có video demo trong `raw_videos/`, hoặc chọn webcam, hoặc tải video lên ở màn hình Kiểm định trực tiếp.
- Đóng ứng dụng khác đang chiếm webcam nếu dùng camera.

## 2. Các màn hình

### Tổng quan

Hiển thị trạng thái trạm và tổng hợp các phiên đã lưu: số sản phẩm, PASS, DEFECT, tỷ lệ lỗi và vài phiên gần nhất. Đây là số cộng dồn từ lịch sử phiên, không phải số đếm riêng của phiên đang chạy.

### Kiểm định trực tiếp

1. Chọn nguồn video demo, webcam `0`, hoặc tải file video `.mp4`, `.avi`, `.mov` lên. Sau khi tải xong, chọn tên video mới trong danh sách nguồn.
2. Chọn checkpoint, ngưỡng tin cậy và tracker. Mặc định là ByteTrack.
3. Bấm **Bắt đầu**, xem video có bounding box và các số PASS/DEFECT/FPS.
4. Bật/tắt còi trên trình duyệt bằng checkbox âm thanh. Trình duyệt có thể yêu cầu thao tác người dùng trước khi phát âm thanh.
5. **Chụp** lưu ảnh khung hình hiện tại vào `reports/snapshots/`. **Phóng to** mở toàn màn hình.
6. Dừng phiên khi đã kiểm tra xong. File video hiện được gửi với chế độ lặp, vì vậy video có thể chạy lại liên tục cho tới khi dừng.

Ý nghĩa ngưỡng tin cậy: tăng ngưỡng thường giảm phát hiện nhầm nhưng cũng có thể bỏ sót chai lỗi; giảm ngưỡng thường bắt được nhiều vật thể hơn nhưng có thể tăng phát hiện nhầm. Hãy đánh giá trên video đại diện trước khi chốt ngưỡng. ByteTrack/BoT-SORT là tracker, không làm tăng độ chính xác phân loại của YOLO một cách tự động.

> **Lưu ý thao tác ở phiên bản hiện tại:** sau khi bấm Bắt đầu, backend chưa gửi sự kiện cập nhật trạng thái ngay cho giao diện. Do đó nút Tạm dừng/Dừng có thể vẫn bị vô hiệu hóa dù worker đã chạy. Có thể dừng tạm thời bằng PowerShell: `Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/stop_inspection`. Đây là lỗi giao diện cần sửa trước buổi demo chính thức.

### Lịch sử

Mỗi lần chạy tạo một phiên. Mở **Chi tiết** để xem các track đã chốt; bấm **Tải CSV** để tải log từng track. Xóa phiên sẽ xóa cả bản ghi CSV của phiên đó. Lịch sử nằm trong `reports/sessions.json`, CSV nằm trong `reports/`.

Để lưu được kết quả cuối phiên, hãy dừng phiên một cách bình thường và chờ Dashboard báo hoàn tất. Nếu worker bị lỗi trước khi mở được model/video, phiên có thể còn trạng thái RUNNING trong lịch sử; xem mục 4.

### Đánh giá mô hình

Màn hình này trình bày benchmark đã ghi trong mã nguồn/tài liệu, không tự chạy đánh giá lại checkpoint hiện chọn. Precision là tỷ lệ dự đoán dương tính đúng; Recall là tỷ lệ đối tượng thật được tìm thấy; mAP là điểm tổng hợp theo ngưỡng confidence/IoU. Xem từng lớp riêng, nhất là `defect`, thay vì chỉ nhìn Overall.

Biểu đồ confusion matrix trong báo cáo có hàng là lớp dự đoán và cột là lớp thật. Trên ma trận test hiện tại, khoảng **41% cột defect** đi vào hàng pass ở ngưỡng tạo confusion matrix. Con số này khác Recall 85.4% trong bảng có thể do cách chọn confidence/ngưỡng đánh giá khác nhau; báo cáo hiện chưa ghi rõ ngưỡng confusion matrix, nên cần bổ sung metadata và đo lại theo ngưỡng triển khai trước khi diễn giải.

### Dữ liệu & Mô hình

Màn hình hiện chỉ xem số ảnh mỗi split và danh sách checkpoint tìm thấy trong repo; chưa có thao tác tải dữ liệu, thay model, xóa checkpoint hay sửa nhãn trực tiếp tại đây.

### Cài đặt

Các trường tracker mặc định, lost-frame buffer, min votes và tự động xuất CSV hiện chưa được nối với nút Lưu hoặc worker. Nút Lưu chỉ hiện thông báo; thay đổi ở các trường đó **không được áp dụng**. Checkbox âm thanh tại màn hình Live mới là điều khiển đang hoạt động và được lưu trong localStorage của trình duyệt đó.

## 3. Cách đọc kết quả và giới hạn mô hình

- Báo cáo hiện có 441 ảnh test, nhưng chỉ 36 ảnh/41 bounding box có lớp defect. Mẫu defect nhỏ nên 1 box làm Recall thay đổi khoảng 2.4 điểm phần trăm.
- Đã ghi nhận khoảng 53–54 cặp ảnh train-test gần trùng. Các chỉ số test vì vậy chỉ là tham khảo/upper bound, chưa phản ánh chắc chắn khả năng tổng quát hóa sang video hoặc dây chuyền mới.
- Bảng báo cáo ghi Recall defect 85.4%, trong khi confusion matrix ở ngưỡng của biểu đồ chỉ phân loại đúng khoảng 59% cột defect. Cần cố định ngưỡng confidence, ghi rõ cách tính và đánh giá lại trên test sạch theo từng phiên quay.
- Giao diện hiện chỉ phát tiếng beep và hiển thị banner cảnh báo. Nó **không kết nối PLC, GPIO, relay hoặc cơ cấu gạt chai**; chưa được dùng để tự động loại sản phẩm ngoài thực tế.

## 4. Khắc phục nhanh

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Server không mở | Xem lỗi trong terminal; xác nhận đã cài `requirements.txt` và cổng 8000 chưa bị ứng dụng khác dùng. |
| Không tìm thấy model | Chép đúng file `.pt` vào `models/`; kiểm tra tên model trong danh sách và terminal. Không dựa vào fallback tự động vì worker có thể chọn checkpoint khác với tên đang hiển thị. |
| Video đen hoặc báo không mở được | Kiểm tra đường dẫn/tệp video, codec, quyền đọc; với webcam kiểm tra chỉ số camera và đóng ứng dụng đang dùng camera. |
| Không có bounding box | Kiểm tra model, lớp/nhãn và nguồn ảnh; thử giảm nhẹ confidence, nhưng phải kiểm chứng false positive và false negative sau khi đổi. |
| Nút Pause/Stop bị mờ sau khi Start | Dùng lệnh dừng ở phần Kiểm định trực tiếp; đây là lỗi đồng bộ trạng thái của giao diện. |
| Tải video thất bại | Dùng `.mp4`, `.avi` hoặc `.mov` theo bộ chọn file trên trang; xem phản hồi lỗi của server. |
| Còi không phát | Bật checkbox âm thanh, nhấp lại vào trang và kiểm tra quyền âm thanh/autoplay của trình duyệt. |

## 5. Hướng hoàn thiện UX/UI

Ưu tiên cải thiện theo thứ tự:

1. Đồng bộ trạng thái RUNNING/PAUSED/STOPPED/ERROR qua WebSocket ngay khi bắt đầu và khi lỗi; khóa/mở đúng nút theo trạng thái thật.
2. Kiểm tra model/video trước khi tạo session; nếu khởi chạy thất bại, hiển thị nguyên nhân và đánh dấu phiên FAILED thay vì để RUNNING.
3. Nối các trường Cài đặt vào localStorage hoặc backend, nạp lại giá trị khi mở trang, validate phạm vi và cho biết “Đã lưu” chỉ sau khi lưu thật.
4. Lấy danh sách model thật từ API vào bộ chọn model; hiển thị model đang nạp thực tế và đường dẫn checkpoint, không âm thầm fallback sang model khác.
5. Bổ sung thông báo upload thành công/thất bại, giới hạn dung lượng video và chuẩn hóa tên file; hiển thị trạng thái đang tải.
6. Đổi nhãn “kích hoạt cơ cấu gạt” thành “cảnh báo phát hiện lỗi (mô phỏng)” cho tới khi tích hợp phần cứng thật.
7. Đặt ngưỡng confusion matrix lên báo cáo; trình bày rõ tỷ lệ defect bị bỏ sót và cảnh báo near-duplicate ngay cạnh KPI test.
8. Dùng trạng thái rỗng/loading/error nhất quán, thao tác bằng bàn phím, nhãn accessible cho nút icon, và xác nhận trước khi xóa phiên.

