"""Đánh giá độc lập mô hình YOLO26 trên tập Test hoặc Validation.

Sử dụng:
    python src/conveyorvision/evaluate.py --split test
    python src/conveyorvision/evaluate.py --split val --model models/conveyor_yolo26_30ep_best.pt
"""

import argparse
import sys
from pathlib import Path

# Thiết lập encoding UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def evaluate_model(
    model_path: str = "models/conveyor_yolo26_30ep_best.pt",
    data_yaml: str = "data/data.yaml",
    split: str = "test",
    imgsz: int = 640,
    batch: int = 16,
    device: str = ""
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[LỖI] Chưa cài đặt Ultralytics. Vui lòng chạy: pip install -r requirements.txt")
        return None

    model_file = Path(model_path).resolve()
    if not model_file.exists():
        candidate_fallbacks = [
            Path("models/conveyor_yolo26_30ep_best.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
            Path("runs/detect/runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/last.pt").resolve(),
            Path("runs/detect/runs/train/conveyor_yolo26_30/weights/last.pt").resolve(),
            Path("weights/best.pt").resolve()
        ]
        found_fallback = next((p for p in candidate_fallbacks if p.exists()), None)
        if found_fallback:
            print(f"[INFO] Không tìm thấy {model_file}, sử dụng checkpoint: {found_fallback}")
            model_file = found_fallback
        else:
            print(f"[LỖI] Không tìm thấy file trọng số: {model_file}")
            print("💡 Gợi ý: File trọng số (*.pt) không được lưu trên Git theo .gitignore.")
            print("   Bạn có thể tạo trọng số bằng cách:")
            print("     1. Chạy notebook notebooks/ConveyorVision_YOLO_Training.ipynb trên Google Colab GPU (~7.7 phút)")
            print("     2. Hoặc chạy CLI: python src/conveyorvision/train_pilot.py --epochs 30")
            print("     3. Hoặc tải file weights về và đặt vào models/conveyor_yolo26_30ep_best.pt")
            return None

    yaml_file = Path(data_yaml).resolve()
    if not yaml_file.exists():
        print(f"[LỖI] Không tìm thấy file dataset: {yaml_file}")
        return None

    # Tạo cấu hình runtime với path tuyệt đối để tránh sửa đổi data/data.yaml gốc trong Git
    eval_yaml_path = yaml_file
    try:
        import yaml
        with open(yaml_file, "r", encoding="utf-8") as f:
            y_data = yaml.safe_load(f) or {}
        data_parent = yaml_file.parent.resolve()
        current_path = y_data.get("path")
        if not current_path or not Path(current_path).is_absolute() or not Path(current_path).exists():
            y_data["path"] = data_parent.as_posix()
            runtime_dir = Path("runs")
            runtime_dir.mkdir(parents=True, exist_ok=True)
            runtime_yaml = runtime_dir / f"runtime_{yaml_file.name}"
            with open(runtime_yaml, "w", encoding="utf-8") as f:
                yaml.safe_dump(y_data, f, sort_keys=False)
            eval_yaml_path = runtime_yaml.resolve()
    except Exception as e:
        print(f"[CẢNH BÁO] Không thể tạo file cấu hình runtime ({e}). Dùng file gốc: {yaml_file}")

    print("\n" + "=" * 65)
    print("      ĐÁNH GIÁ ĐỘC LẬP MÔ HÌNH CONVEYORVISION (YOLO26)")
    print("=" * 65)
    print(f"  * Model trọng số:    {model_file}")
    print(f"  * Cấu hình dataset:  {eval_yaml_path} (nguồn: {yaml_file})")
    print(f"  * Phân tập đánh giá: {split.upper()}")
    print(f"  * Kích thước ảnh:    {imgsz}x{imgsz}")
    print("=" * 65 + "\n")

    model = YOLO(str(model_file))
    metrics = model.val(
        data=str(eval_yaml_path),
        split=split,
        imgsz=imgsz,
        batch=batch,
        device=device if device else None,
        plots=True,
        save_json=False,
        verbose=True
    )

    p, r, map50, map50_95 = metrics.box.mean_results()
    speed = metrics.speed

    print("\n" + "=" * 65)
    print("                   KẾT QUẢ ĐÁNH GIÁ CHI TIẾT                  ")
    print("=" * 65)
    print(f"  - Precision (Độ chính xác):          {p * 100:.2f}%")
    print(f"  - Recall (Độ nhạy / Bắt trúng):      {r * 100:.2f}%")
    print(f"  - mAP@50:                            {map50 * 100:.2f}%")
    print(f"  - mAP@50-95:                         {map50_95 * 100:.2f}%")
    print(f"  - Thời gian inference trung bình:    {speed.get('inference', 0):.2f} ms/ảnh")
    if speed.get('inference', 0) > 0:
        fps = 1000.0 / speed['inference']
        print(f"  - Tốc độ xử lý ước tính:             {fps:.1f} FPS")
    print("=" * 65 + "\n")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConveyorVision Model Evaluation")
    parser.add_argument("--model", type=str, default="models/conveyor_yolo26_30ep_best.pt", help="Đường dẫn file .pt")
    parser.add_argument("--data", type=str, default="data/data.yaml", help="Đường dẫn file data.yaml")
    parser.add_argument("--split", type=str, default="test", choices=["test", "val", "train"], help="Phân tập cần đánh giá (test/val)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", type=str, default="", help="Device: 0 (GPU), cpu, etc.")

    args = parser.parse_args()
    res = evaluate_model(
        model_path=args.model,
        data_yaml=args.data,
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device
    )
    if res is None:
        sys.exit(1)

