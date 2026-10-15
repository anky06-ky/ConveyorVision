"""
ConveyorVision Pilot Training Script
------------------------------------
Huấn luyện thử nghiệm pilot cho mô hình YOLO trên tập dữ liệu đã chuẩn hóa (2 class: pass, defect).
Chiến lược:
- Train 1.692 ảnh, batch size 16 (~106 steps/epoch)
- Mặc định 30 epochs (~3.180 steps)
- Có thể chạy 2-3 epoch đầu để đo thời gian mỗi epoch trước khi train dài.
"""

import sys
import time
from pathlib import Path
import argparse

# Thiết lập encoding UTF-8 cho Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def train_pilot(
    data_yaml: str = "data/data.yaml",
    model_name: str = "yolov8n.pt",
    epochs: int = 30,
    batch_size: int = 16,
    imgsz: int = 640,
    project: str = "runs/pilot",
    name: str = "pilot_run",
    device: str = ""
):
    try:
        from ultralytics import YOLO
    except ImportError as e:
        print(f"[LỖI] Không thể nạp Ultralytics / PyTorch: {e}")
        print("Vui lòng đảm bảo đã cài đặt Microsoft Visual C++ Redistributable:")
        print("  -> Chạy file: vc_redist.x64.exe (đã tải sẵn ở thư mục gốc)")
        return None

    yaml_path = Path(data_yaml).resolve()
    if not yaml_path.exists():
        print(f"[LỖI] Không tìm thấy file cấu hình: {yaml_path}")
        return None

    print("\n=======================================================")
    print("       KHỞI CHẠY HUẤN LUYỆN PILOT CONVEYORVISION        ")
    print("=======================================================")
    print(f"  * Model xuất phát:    {model_name}")
    print(f"  * Cấu hình data:      {yaml_path}")
    print(f"  * Số Epochs:          {epochs}")
    print(f"  * Batch size:         {batch_size} (~106 steps/epoch)")
    print(f"  * Kích thước ảnh:     {imgsz}x{imgsz}")
    print(f"  * Thư mục lưu kết quả:{project}/{name}")
    print("=======================================================\n")

    start_time = time.time()
    model = YOLO(model_name)

    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        project=project,
        name=name,
        device=device if device else None,
        plots=True,
        save=True,
        verbose=True
    )

    elapsed = time.time() - start_time
    avg_per_epoch = elapsed / max(1, epochs)
    est_30_epochs = avg_per_epoch * 30

    print("\n=======================================================")
    print("                  KẾT QUẢ ĐO LƯỜNG                     ")
    print("=======================================================")
    print(f"  - Thời gian đã chạy ({epochs} epochs): {elapsed / 60:.2f} phút")
    print(f"  - Trung bình mỗi epoch:              {avg_per_epoch:.2f} giây")
    if epochs < 30:
        print(f"  - Ước tính thời gian cho 30 epochs:  {est_30_epochs / 60:.2f} phút ({est_30_epochs / 3600:.2f} giờ)")
    print("=======================================================\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConveyorVision Pilot Training")
    parser.add_argument("--epochs", type=int, default=30, help="Số epoch huấn luyện (khuyên dùng 3 để đo trước, 30 cho toàn bộ pilot)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Pretrained weights")
    parser.add_argument("--data", type=str, default="data/data.yaml", help="Path to data.yaml")
    parser.add_argument("--project", type=str, default="runs/pilot", help="Thư mục project lưu kết quả")
    parser.add_argument("--name", type=str, default="pilot_test", help="Tên lần chạy")
    parser.add_argument("--device", type=str, default="", help="Device: 0 (GPU), cpu, etc.")

    args = parser.parse_args()
    train_pilot(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        project=args.project,
        name=args.name,
        device=args.device
    )
