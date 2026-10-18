# ConveyorVision — YOLO26 pilot

Hệ thống phân loại sản phẩm đạt/lỗi trên băng chuyền, dùng Ultralytics YOLO26.

## Cấu trúc

```
conveyorvision/
  data/
    data.yaml                  # file cấu hình duy nhất: khai báo đường dẫn tuyệt đối + tên lớp
    images/                    # 2.666 ảnh chia 3 tập: train (1.692), val (533), test (441)
    labels/                    # nhãn YOLO (.txt) tương ứng chuẩn hóa 2 class
    manifest.csv               # sinh ra bởi video_io.py — KHÔNG commit video gốc
  doc/                         # tài liệu thiết kế, mindmap, báo cáo tiến độ
  notebooks/
    ConveyorVision_YOLO_Training.ipynb  # notebook huấn luyện & trực quan hóa biểu đồ
  src/conveyorvision/
    video_io.py                # trích frame từ video bằng OpenCV
    dataset_manager.py         # quản lý, remap 2 class và chuẩn hóa dữ liệu
    train_pilot.py             # script huấn luyện pilot qua CLI
    evaluate.py                # đánh giá độc lập mô hình trên tập test/val
    inference_conveyor.py      # pipeline kiểm định & đếm sản phẩm thời gian thực
  tools/                       # các script tiện ích định dạng báo cáo Word/Markdown
  models/                      # file .pt tối ưu sau khi train
  tests/                       # bộ unit test tự động (pytest)
  reports/                     # log kết quả kiểm định CSV và báo cáo
```

## Bước 0 — cài môi trường

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Bước 1 — trích frame từ video

Bỏ video pilot (2-3 video ngắn) vào một thư mục, ví dụ `raw_videos/`, rồi chạy:

```bash
python src/conveyorvision/video_io.py \
  --video raw_videos/video1.mp4 \
  --out_dir data/images/train \
  --fps 2
```

Script sẽ lưu ảnh vào `data/images/train/` và ghi/append vào `data/manifest.csv`
(video_id, frame_idx, timestamp_s, image_path) — dùng file này để sau tách
train/val/test theo **video_id**, tránh rò rỉ dữ liệu giữa các frame liền kề.

Chạy lại với video khác, đổi `--out_dir data/images/val` hoặc `--out_dir data/images/test`
cho các phần video độc lập (không trộn frame của cùng một video vào các tập khác nhau).

## Bước 2 — Chuẩn hóa tập dữ liệu 3 tập (Train / Val / Test)

Dự án sử dụng bộ dữ liệu chuẩn hóa gồm **2.666 ảnh** chia 3 tập:
- `data/images/train` & `data/labels/train`: **1.692 ảnh** (~63.5%)
- `data/images/val` & `data/labels/val`: **533 ảnh** (~20.0%)
- `data/images/test` & `data/labels/test`: **441 ảnh** (~16.5%)

Định dạng nhãn YOLO (.txt) được chuẩn hóa đồng nhất về 2 class:
- `0: pass` (sản phẩm đạt chuẩn)
- `1: defect` (sản phẩm móp méo, vỡ, nứt, nhãn lỗi, thiếu nắp...)

Quản lý và đồng bộ tự động dữ liệu qua Roboflow API (đọc key từ biến môi trường `ROBOFLOW_API_KEY`):
```bash
python src/conveyorvision/dataset_manager.py --download-all
```

## Bước 3 — Khai báo data/data.yaml

Dự án quản lý cấu hình tập dữ liệu tại `data/data.yaml` với `path: data` tương đối chuẩn Git. Khi chạy qua `evaluate.py`, `train_pilot.py` hoặc Notebook, hệ thống tự động sinh cấu hình runtime cô lập (`runs/runtime_data.yaml`) chứa đường dẫn tuyệt đối cho Ultralytics xử lý mà không làm thay đổi file `data.yaml` trong kho Git.

## Bước 4 — Huấn luyện mô hình (Training)

Có 2 cách huấn luyện:

### Cách 1: Sử dụng Jupyter Notebook trên Colab GPU hoặc Local (Khuyên dùng)
Mở notebook `notebooks/ConveyorVision_YOLO_Training.ipynb` để chạy quy trình đồng bộ dữ liệu, huấn luyện 30 epochs, và trực quan hóa toàn bộ biểu đồ (Loss, Confusion Matrix, PR Curve, Inference Preview).

### Cách 2: Chạy script dòng lệnh (CLI)
```bash
# Huấn luyện thử nghiệm pilot qua CLI với yolo26n.pt
python src/conveyorvision/train_pilot.py --epochs 30 --batch 16 --model yolo26n.pt
```

Hoặc qua dòng lệnh Python trực tiếp:
```bash
python -c "
from ultralytics import YOLO
model = YOLO('yolo26n.pt')
model.train(data='data/data.yaml', epochs=30, imgsz=640, project='runs/train', name='conveyor_yolo26_30', exist_ok=True, cls=1.2)
"
```

## Bước 5 — Đánh giá mô hình trên phân tập kiểm thử (Model Evaluation)

Đánh giá độ chính xác trên phân tập `test` (441 ảnh) hoặc `val`:
```bash
# Đánh giá trên tập test với model tốt nhất
python src/conveyorvision/evaluate.py --split test --model models/conveyor_yolo26_30ep_best.pt

# Đánh giá trên tập val
python src/conveyorvision/evaluate.py --split val --model models/conveyor_yolo26_30ep_best.pt
```

## Bước 6 — Kiểm định & đếm sản phẩm băng chuyền thời gian thực (Real-time Inspection)

Pipeline theo vết (Object Tracking với ByteTrack), cơ chế **Multi-frame Voting** chống phán đoán vội ở mép khung hình, đếm chính xác sản phẩm không bị trùng lặp, cảnh báo phế phẩm và xuất log CSV:
```bash
# Chạy trên file video băng chuyền với tracker ByteTrack
python src/conveyorvision/inference_conveyor.py --source raw_videos/sample.mp4 --model models/conveyor_yolo26_30ep_best.pt --tracker bytetrack.yaml

# Chạy trực tiếp từ camera / webcam
python src/conveyorvision/inference_conveyor.py --source 0 --model models/conveyor_yolo26_30ep_best.pt
```

## 📊 Kết Quả Huấn Luyện & Đánh Giá Thực Nghiệm (Benchmark)

Mô hình **YOLO26 Nano** được huấn luyện 30 epochs trên Google Colab GPU (NVIDIA L4/T4, thời gian chạy: **7.7 phút**):

| Tập dữ liệu | Quy mô | Precision | Recall | mAP@50 | mAP@50-95 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Validation** | 533 ảnh | 78.7% | 79.3% | 82.0% | 58.0% |
| **Test (Phân tập test)** | 441 ảnh | **78.2%** | **75.7%** | **82.5%** | **61.4%** |
| → Riêng lớp `defect` (Test) | 41 box | 76.6% | **85.4%** | **86.2%** | **71.7%** |

* **Đo lường tốc độ thực tế (Empirical):** Đạt **125.9 ms/ảnh (~7.9 FPS)** trên Intel Core i7-8565U CPU (môi trường laptop văn phòng, không GPU). Tốc độ dự kiến **>80 FPS** trên GPU công nghiệp (NVIDIA T4 / RTX).
* **Lưu ý khoa học & Giới hạn thực tế:** Kết quả trên tập Test đóng vai trò là ngưỡng trên thực nghiệm do đối sánh thuật toán (pHash/SSIM) phát hiện khoảng 53–54 cặp ảnh cận trùng giữa train-test từ việc chia ngẫu nhiên chuỗi khung hình Roboflow; để đánh giá độc lập thực sự cần chia lại tập test theo phiên quay vật lý độc lập (session-based split). Pipeline tracking tích hợp cơ chế Multi-frame Voting giúp ổn định nhãn và lọc nhiễu nhận diện qua chuỗi khung hình; tuy nhiên để giải quyết triệt để khoảng cách miền (domain gap / ánh sáng thay đổi), cần thu thập thêm dữ liệu hiện trường để tinh chỉnh (fine-tune) mô hình.
* Chi tiết báo cáo, ma trận nhầm lẫn và biểu đồ xem tại: [`doc/evaluation/README.md`](doc/evaluation/README.md).

## 📥 Hướng Dẫn Về Trọng Số Mô Hình (.pt)

Theo tiêu chuẩn quản lý mã nguồn Git và cấu hình [`.gitignore`](.gitignore), các file trọng số nhị phân nặng (`*.pt`) **không được lưu trực tiếp trên Git**.

Để có file trọng số `models/conveyor_yolo26_30ep_best.pt` khi clone mới repository:
1. **Cách 1 (Khuyên dùng — Tự huấn luyện lại):** Mở notebook `notebooks/ConveyorVision_YOLO_Training.ipynb` trên Google Colab GPU và bấm chạy toàn bộ. Mô hình sẽ hoàn thành huấn luyện 30 epochs sau **~7.7 phút** và xuất file `best.pt`.
2. **Cách 2 (Sử dụng CLI):** Chạy lệnh `python src/conveyorvision/train_pilot.py --epochs 30 --batch 16`.
3. **Cách 3 (Tải trực tiếp qua Release):** Sau khi gắn tag phiên bản release chính thức trên GitHub, file trọng số `conveyor_yolo26_30ep_best.pt` sẽ được lưu trữ kèm tại mục **Releases** của repository.



