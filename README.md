# ConveyorVision — YOLO26 pilot

Hệ thống phân loại sản phẩm đạt/lỗi trên băng chuyền, dùng Ultralytics YOLO26.

## Cấu trúc

```
conveyorvision/
  data/
    images/train  images/val   # ảnh đã trích từ video
    labels/train  labels/val   # nhãn YOLO (.txt) tương ứng
    data.yaml                  # khai báo đường dẫn + tên lớp
    manifest.csv               # sinh ra bởi video_io.py — KHÔNG commit video gốc
  notebooks/                   # EDA, thử nghiệm
  src/conveyorvision/
    video_io.py                # trích frame từ video bằng OpenCV
  app/                         # FastAPI (thêm ở Tuần 5)
  models/                      # file .pt đã fine-tune
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
train/val theo **video_id**, tránh rò rỉ dữ liệu giữa các frame liền kề.

Chạy lại với video khác, đổi `--out_dir data/images/val` cho một phần video
dành riêng cho validation (không trộn frame của cùng một video vào cả hai tập).

## Bước 2 — gán nhãn bounding box

Dùng CVAT hoặc Roboflow trên các ảnh trong `data/images/train` và
`data/images/val`, xuất nhãn định dạng YOLO (.txt), đặt vào
`data/labels/train` và `data/labels/val` (tên file trùng tên ảnh).

## Bước 3 — khai báo data.yaml

File mẫu đã có ở `data/data.yaml` — chỉnh `path` thành đường dẫn tuyệt đối
tới thư mục `data/` trên máy bạn.

## Bước 4 — train thử lần đầu (pilot)

```bash
python -c "
from ultralytics import YOLO
model = YOLO('yolo26n.pt')
model.train(data='data/data.yaml', epochs=20, imgsz=640)
"
```

Mục tiêu bước này chỉ là xác nhận pipeline chạy được (loss giảm, không lỗi
định dạng) — chưa cần tối ưu số liệu.
