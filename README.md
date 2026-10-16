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
  tools/                       # các script tiện ích định dạng báo cáo Word/Markdown
  models/                      # file .pt tối ưu sau khi train
  tests/
  reports/
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

Dự án chỉ lưu một file cấu hình duy nhất tại `data/data.yaml` (bản trùng ở root đã được loại bỏ).
Lưu ý: thuộc tính `path` trong `data/data.yaml` cần là đường dẫn tuyệt đối tới thư mục `data/` trên máy của bạn (tránh lỗi Ultralytics resolve sai sang thư mục mặc định của hệ thống). Khi chạy qua `train_pilot.py` hoặc Notebook, script sẽ tự động sinh và cập nhật đường dẫn tuyệt đối này.

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
model.train(data='data/data.yaml', epochs=30, imgsz=640, project='runs/train', name='conveyor_yolo26_30', exist_ok=True)
"
```


