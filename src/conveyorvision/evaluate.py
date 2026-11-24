"""Đánh giá độc lập mô hình YOLO26 trên tập Test hoặc Validation.

Sử dụng:
    python src/conveyorvision/evaluate.py --split test
    python src/conveyorvision/evaluate.py --split val --model models/conveyor_qc_yolo26n.pt
    # Xuất số liệu + biểu đồ cho dashboard (doc/evaluation/metrics.json):
    python src/conveyorvision/evaluate.py --split test --export doc/evaluation --train-run runs/train/<tên lần chạy>
"""

import argparse
import hashlib
import json
import platform
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Thiết lập encoding UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def evaluate_model(
    model_path: str = "models/conveyor_qc_yolo26n.pt",
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
        print(f"[LỖI] Không tìm thấy checkpoint: {model_file}. Chỉ định đúng file --model.")
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
    names = getattr(metrics, "names", {}) or {0: "pass", 1: "defect"}

    print("\n" + "=" * 72)
    print("                      KẾT QUẢ ĐÁNH GIÁ CHI TIẾT                       ")
    print("=" * 72)
    print(f"{'Lớp (Class)':<15} | {'Precision':<10} | {'Recall':<10} | {'mAP@50':<10} | {'mAP@50-95':<10}")
    print("-" * 72)
    print(f"{'Tất cả (All)':<15} | {p * 100:>9.1f}% | {r * 100:>9.1f}% | {map50 * 100:>9.1f}% | {map50_95 * 100:>9.1f}%")

    # In chi tiết từng lớp riêng biệt (pass, defect)
    ap_classes = getattr(metrics.box, "ap_class_index", list(names.keys()))
    for idx, c_idx in enumerate(ap_classes):
        cname = names.get(c_idx, f"Class {c_idx}")
        try:
            cp, cr, cmap50, cmap = metrics.box.class_result(idx)
            print(f"{cname:<15} | {cp * 100:>9.1f}% | {cr * 100:>9.1f}% | {cmap50 * 100:>9.1f}% | {cmap * 100:>9.1f}%")
        except Exception:
            pass
    print("-" * 72)
    print(f"  - Tiền xử lý (Preprocess):            {speed.get('preprocess', 0):.2f} ms/ảnh")
    print(f"  - Suy luận (Inference):               {speed.get('inference', 0):.2f} ms/ảnh")
    print(f"  - Hậu xử lý (Postprocess):            {speed.get('postprocess', 0):.2f} ms/ảnh")
    if speed.get('loss', 0) > 0:
        print(f"  - Tính toán Loss (Validation Loss):   {speed.get('loss', 0):.2f} ms/ảnh")
    if speed.get('inference', 0) > 0:
        fps = 1000.0 / speed['inference']
        print(f"  - Tốc độ xử lý ước tính:             {fps:.1f} FPS")
    print("=" * 72 + "\n")

    return metrics


def _cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def benchmark_cpu(model_file: Path, images: list, imgsz: int, n: int = 30) -> dict:
    """Đo tốc độ suy luận thật trên CPU (trạm kiểm định có thể không có GPU)."""
    from ultralytics import YOLO

    model = YOLO(str(model_file))
    sample = images[:n]
    model.predict(sample[0], imgsz=imgsz, device="cpu", verbose=False)  # warm-up
    totals = {"preprocess": 0.0, "inference": 0.0, "postprocess": 0.0}
    for img in sample:
        result = model.predict(img, imgsz=imgsz, device="cpu", verbose=False)[0]
        for k in totals:
            totals[k] += result.speed[k]
    avg = {k: round(v / len(sample), 1) for k, v in totals.items()}
    avg["fps"] = round(1000.0 / max(1e-6, sum(avg.values())), 1)
    avg["device"] = _cpu_name()
    avg["imgsz"] = imgsz
    return avg


def export_report(metrics, model_file: Path, data_yaml: Path, split: str, imgsz: int,
                  export_dir: Path, train_run: Path = None) -> Path:
    """Ghi metrics.json + biểu đồ để dashboard hiển thị số liệu thật (không hardcode)."""
    import torch
    from ultralytics import YOLO

    export_dir.mkdir(parents=True, exist_ok=True)
    save_dir = Path(metrics.save_dir)
    names = metrics.names
    p, r, map50, map50_95 = metrics.box.mean_results()

    classes = []
    for idx, c in enumerate(metrics.box.ap_class_index):
        c = int(c)
        cp, cr, cmap50, cmap = metrics.box.class_result(idx)
        classes.append({
            "class_id": c,
            "name": names[c],
            "images": int(metrics.nt_per_image[c]),
            "boxes": int(metrics.nt_per_class[c]),
            "precision": round(cp * 100, 1),
            "recall": round(cr * 100, 1),
            "map50": round(cmap50 * 100, 1),
            "map50_95": round(cmap * 100, 1),
        })

    # Ma trận nhầm lẫn của Ultralytics: hàng = dự đoán, cột = nhãn thật, chỉ số cuối = background
    cm = metrics.confusion_matrix.matrix
    confusion = {}
    for c, name in names.items():
        col = cm[:, c]
        total = float(col.sum())
        if total:
            confusion[name] = {
                "correct_pct": round(float(col[c]) / total * 100, 1),
                "as_other_class_pct": round(float(col[:-1].sum() - col[c]) / total * 100, 1),
                "missed_pct": round(float(col[-1]) / total * 100, 1),
            }

    model = YOLO(str(model_file))
    data_dir = data_yaml.parent
    test_images = sorted((data_dir / "images" / split).glob("*.jpg"))
    split_report = data_dir / "split_report.json"

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": {
            "file": model_file.name,
            "sha256": hashlib.sha256(model_file.read_bytes()).hexdigest(),
            "architecture": "YOLO26n",
            "parameters": int(sum(x.numel() for x in model.model.parameters())),
            "size_mb": round(model_file.stat().st_size / (1024 * 1024), 2),
        },
        "split": split,
        "imgsz": imgsz,
        "num_images": int(len(test_images)),
        "num_boxes": int(sum(c["boxes"] for c in classes)),
        "overall": {
            "precision": round(p * 100, 1),
            "recall": round(r * 100, 1),
            "map50": round(map50 * 100, 1),
            "map50_95": round(map50_95 * 100, 1),
        },
        "classes": classes,
        # Ngưỡng thực tế phụ thuộc phiên bản và cách Ultralytics tạo ma trận.
        # Không suy đoán ngưỡng khi validator không cung cấp thông tin.
        "confusion_conf": None,
        "confusion": confusion,
        "speed_gpu": {
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "preprocess_ms": round(metrics.speed["preprocess"], 2),
            "inference_ms": round(metrics.speed["inference"], 2),
            "postprocess_ms": round(metrics.speed["postprocess"], 2),
        } if torch.cuda.is_available() else None,
        "speed_cpu": benchmark_cpu(model_file, test_images, imgsz),
        "dataset_split": json.loads(split_report.read_text(encoding="utf-8")) if split_report.exists() else None,
        "training": None,
    }

    charts = {
        "confusion_matrix_normalized.png": "test_confusion_matrix_normalized.png",
        "BoxPR_curve.png": "test_BoxPR_curve.png",
        "val_batch0_pred.jpg": "test_batch0_pred.jpg",
    }
    for src, dst in charts.items():
        if (save_dir / src).exists():
            shutil.copy2(save_dir / src, export_dir / dst)

    if train_run is not None:
        for name in ("results.png", "results.csv"):
            if (train_run / name).exists():
                shutil.copy2(train_run / name, export_dir / name)
        args_file = train_run / "args.yaml"
        csv_file = train_run / "results.csv"
        if csv_file.exists():
            import csv as _csv
            rows = list(_csv.DictReader(csv_file.open(encoding="utf-8")))
            rows = [{k.strip(): v.strip() for k, v in row.items()} for row in rows]
            best = max(rows, key=lambda row: float(row["metrics/mAP50-95(B)"]))
            report["training"] = {
                "epochs_run": len(rows),
                "best_epoch": int(float(best["epoch"])),
                "time_sec": round(float(rows[-1].get("time", 0) or 0), 1),
                "args": __import__("yaml").safe_load(args_file.read_text()) if args_file.exists() else None,
            }

    out = export_dir / "metrics.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Đã xuất số liệu đánh giá: {out}")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConveyorVision Model Evaluation")
    parser.add_argument("--model", type=str, default="models/conveyor_qc_yolo26n.pt", help="Đường dẫn file .pt")
    parser.add_argument("--data", type=str, default="data/data.yaml", help="Đường dẫn file data.yaml")
    parser.add_argument("--split", type=str, default="test", choices=["test", "val", "train"], help="Phân tập cần đánh giá (test/val)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", type=str, default="", help="Device: 0 (GPU), cpu, etc.")
    parser.add_argument("--export", type=str, default=None, help="Thư mục xuất metrics.json + biểu đồ cho dashboard")
    parser.add_argument("--train-run", type=str, default=None, help="Thư mục lần huấn luyện (lấy results.png/csv, args)")

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
    if args.export:
        export_report(
            res,
            model_file=Path(args.model).resolve(),
            data_yaml=Path(args.data).resolve(),
            split=args.split,
            imgsz=args.imgsz,
            export_dir=Path(args.export),
            train_run=Path(args.train_run) if args.train_run else None,
        )

