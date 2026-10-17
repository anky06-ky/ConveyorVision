"""
ConveyorVision Dataset Manager
------------------------------
Quản lý, tải về, remap nhãn và chuẩn hóa dữ liệu cho bài toán:
- Class 0: pass (sản phẩm đạt chuẩn trên băng chuyền)
- Class 1: defect (sản phẩm lỗi: móp méo, vỡ, nhãn lỗi, thiếu nắp...)

Hỗ trợ:
1. Đồng bộ / di chuyển bộ dữ liệu cũ từ root (train/valid/test) vào thư mục chuẩn data/
2. Nhập dataset từ Roboflow (qua API hoặc từ thư mục giải nén ZIP)
3. Remap nhãn về 2 class chuẩn: 0 (pass) và 1 (defect)
4. Kiểm toán (audit) chất lượng dữ liệu, thống kê số lượng ảnh và bounding boxes
"""

import os
import sys
import shutil
import glob
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# Đảm bảo in tiếng Việt không bị lỗi encoding trên Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    yaml = None

# Cấu hình class chuẩn của ConveyorVision
STANDARD_CLASSES = {
    0: "pass",
    1: "defect"
}

# Quy tắc remap nhãn mặc định (không phân biệt hoa thường)
DEFAULT_NAME_MAP = {
    # Nhóm Đạt (pass = 0)
    "good": 0,
    "pass": 0,
    "bottle": 0,
    "normal": 0,
    "standard": 0,
    "ok": 0,

    # Nhóm Lỗi (defect = 1)
    "defect": 1,
    "defective": 1,
    "bad": 1,
    "damage": 1,
    "damaged": 1,
    "dent": 1,
    "dented": 1,
    "broken": 1,
    "crack": 1,
    "scratch": 1,
    "no-cap": 1,
    "no_cap": 1,
    "missing_cap": 1,
    "label_defect": 1,
    "dirty": 1
}


def normalize_split_name(name: str) -> str:
    """Chuẩn hóa tên split về train, val, test."""
    name = name.lower().strip()
    if name in ["valid", "validation", "val"]:
        return "val"
    if name in ["train", "training"]:
        return "train"
    if name in ["test", "testing"]:
        return "test"
    return name


def ensure_data_dirs(base_data_dir: Path):
    """Tạo đầy đủ cấu trúc thư mục chuẩn trong data/"""
    for split in ["train", "val", "test"]:
        (base_data_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (base_data_dir / "labels" / split).mkdir(parents=True, exist_ok=True)


def update_data_yaml(project_root: Path) -> Path:
    """Tạo hoặc cập nhật file data/data.yaml chuẩn."""
    data_dir = project_root / "data"
    yaml_path = data_dir / "data.yaml"

    # Dùng đường dẫn chuẩn forward slash cho YOLO
    posix_path = data_dir.resolve().as_posix()

    if yaml is not None:
        yaml_data = {
            "path": posix_path,
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "names": STANDARD_CLASSES
        }
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    else:
        content = f"""# ConveyorVision YOLO Dataset Configuration
path: {posix_path}
train: images/train
val: images/val
test: images/test

names:
  0: pass
  1: defect
"""
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"[OK] Cập nhật file cấu hình: {yaml_path}")
    return yaml_path


def validate_bbox_line(line: str) -> Optional[Tuple[int, float, float, float, float]]:
    """Kiểm tra và chuẩn hóa 1 dòng nhãn YOLO (class x y w h)."""
    parts = line.strip().split()
    if not parts or len(parts) < 5:
        return None
    try:
        cls_idx = int(parts[0])
        x = float(parts[1])
        y = float(parts[2])
        w = float(parts[3])
        h = float(parts[4])
        # Kiểm tra tọa độ nằm trong khoảng [0, 1]
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))
        return (cls_idx, x, y, w, h)
    except ValueError:
        return None


def remap_and_copy_file(
    src_img: Path,
    src_lbl: Optional[Path],
    dst_img: Path,
    dst_lbl: Path,
    class_id_mapping: Dict[int, int]
) -> int:
    """
    Sao chép ảnh và chuyển đổi nhãn sang class chuẩn.
    Trả về số lượng box hợp lệ được ghi nhận.
    """
    # 1. Sao chép ảnh
    shutil.copy2(src_img, dst_img)

    # 2. Xử lý nhãn
    valid_boxes = 0
    new_lines = []

    if src_lbl and src_lbl.exists():
        with open(src_lbl, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            parsed = validate_bbox_line(line)
            if not parsed:
                continue
            src_cls, x, y, w, h = parsed
            if src_cls in class_id_mapping:
                target_cls = class_id_mapping[src_cls]
                if target_cls is not None:
                    new_lines.append(f"{target_cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
                    valid_boxes += 1

    # Luôn tạo file nhãn (kể cả file rỗng cho background image)
    with open(dst_lbl, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return valid_boxes


def migrate_root_dataset(project_root: Path, copy_only: bool = True) -> Dict:
    """
    Chuyển đổi bộ dữ liệu hiện tại (1.740 ảnh chai ở thư mục root train/valid/test)
    vào đúng thư mục chuẩn data/images/ và data/labels/ với class 0 = pass.
    """
    data_dir = project_root / "data"
    ensure_data_dirs(data_dir)

    print("\n--- [Bước 1] Chuẩn hóa bộ dữ liệu hiện có từ root (conveyor-belt-eafpe-bgzzm) ---")
    stats = {"images": 0, "boxes": 0, "splits": {}}

    source_splits = {
        "train": project_root / "train",
        "valid": project_root / "valid",
        "test": project_root / "test"
    }

    # Class 0 ban đầu là 'bottle' -> remap thành 0 ('pass')
    class_map = {0: 0}

    for orig_split, orig_dir in source_splits.items():
        target_split = normalize_split_name(orig_split)
        img_dir = orig_dir / "images"
        lbl_dir = orig_dir / "labels"

        if not img_dir.exists():
            continue

        images = [p for p in img_dir.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]]
        split_images = 0
        split_boxes = 0

        for img_path in images:
            lbl_name = img_path.stem + ".txt"
            lbl_path = lbl_dir / lbl_name if lbl_dir.exists() else None

            # Đổi tên với tiền tố để tránh trùng lặp
            dest_name = f"conveyor_{img_path.name}"
            dest_lbl_name = f"conveyor_{lbl_name}"

            dest_img = data_dir / "images" / target_split / dest_name
            dest_lbl = data_dir / "labels" / target_split / dest_lbl_name

            boxes = remap_and_copy_file(img_path, lbl_path, dest_img, dest_lbl, class_map)
            split_images += 1
            split_boxes += boxes

        stats["splits"][target_split] = {"images": split_images, "boxes": split_boxes}
        stats["images"] += split_images
        stats["boxes"] += split_boxes
        print(f"  + Split '{target_split}': đã nhập {split_images} ảnh, {split_boxes} bounding boxes")

    print(f"[OK] Hoàn thành chuẩn hóa dữ liệu cũ: Tổng {stats['images']} ảnh, {stats['boxes']} boxes (Class: pass).")
    return stats


def import_dataset_from_dir(
    source_dir: Path,
    project_root: Path,
    dataset_prefix: str,
    explicit_class_map: Optional[Dict[str, int]] = None
) -> Dict:
    """
    Nhập một dataset YOLO đã tải về (hoặc giải nén) từ một thư mục bất kỳ.
    Tự động đọc data.yaml nguồn để ánh xạ nhãn về 0 (pass) và 1 (defect).
    """
    data_dir = project_root / "data"
    ensure_data_dirs(data_dir)

    print(f"\n--- Nhập dataset từ thư mục: {source_dir.name} (prefix: {dataset_prefix}) ---")

    # Đọc data.yaml nguồn nếu có
    src_yaml_path = None
    for yml in source_dir.glob("*.yaml"):
        src_yaml_path = yml
        break
    if not src_yaml_path:
        for yml in source_dir.glob("*.yml"):
            src_yaml_path = yml
            break

    id_to_target_cls: Dict[int, int] = {}

    if src_yaml_path and src_yaml_path.exists():
        with open(src_yaml_path, "r", encoding="utf-8") as f:
            src_cfg = yaml.safe_load(f)
        names = src_cfg.get("names", [])
        print(f"  * Tìm thấy nhãn nguồn: {names}")

        if isinstance(names, list):
            for idx, name in enumerate(names):
                name_clean = str(name).strip().lower()
                if explicit_class_map and name_clean in explicit_class_map:
                    id_to_target_cls[idx] = explicit_class_map[name_clean]
                elif name_clean in DEFAULT_NAME_MAP:
                    id_to_target_cls[idx] = DEFAULT_NAME_MAP[name_clean]
                else:
                    print(f"  [CẢNH BÁO] Không có quy tắc map cho nhãn '{name}' (idx {idx}), bỏ qua box này.")
        elif isinstance(names, dict):
            for idx, name in names.items():
                name_clean = str(name).strip().lower()
                idx_int = int(idx)
                if explicit_class_map and name_clean in explicit_class_map:
                    id_to_target_cls[idx_int] = explicit_class_map[name_clean]
                elif name_clean in DEFAULT_NAME_MAP:
                    id_to_target_cls[idx_int] = DEFAULT_NAME_MAP[name_clean]
                else:
                    print(f"  [CẢNH BÁO] Không có quy tắc map cho nhãn '{name}' (idx {idx}), bỏ qua box này.")
    else:
        # Nếu không có data.yaml, dùng mapping mặc định cho 2 class
        print("  * Không thấy data.yaml nguồn, dùng mapping mặc định:")
        print("    Class 0 -> 0 (pass), Class 1 -> 1 (defect)")
        id_to_target_cls = {0: 0, 1: 1}

    print(f"  * Bảng chuyển đổi ID lớp: {id_to_target_cls}")

    # Tìm các thư mục split
    stats = {"images": 0, "boxes": 0, "splits": {}}

    # Quét các split có thể có: train, valid, val, test
    found_splits = []
    for candidate in ["train", "valid", "val", "test"]:
        cand_path = source_dir / candidate
        if cand_path.is_dir():
            found_splits.append((candidate, cand_path))

    # Nếu không có cấu trúc split lồng, kiểm tra trực tiếp thư mục images
    if not found_splits:
        if (source_dir / "images").exists():
            for candidate in ["train", "valid", "val", "test"]:
                c_img = source_dir / "images" / candidate
                if c_img.is_dir():
                    found_splits.append((candidate, source_dir))

    # Xây dựng danh sách ảnh hiện có trong data/ để tránh nhân đôi dữ liệu khi import lại
    existing_file_names = set()
    for s in ["train", "val", "test"]:
        s_img_dir = data_dir / "images" / s
        if s_img_dir.exists():
            for p in s_img_dir.iterdir():
                existing_file_names.add(p.name)
                for pfx in ["conveyor_", "bayo_", "bottle_defect_", "bayo_bottle_", "bottle_defects_"]:
                    if p.name.startswith(pfx):
                        existing_file_names.add(p.name[len(pfx):])

    auto_partition = (len(found_splits) == 1 and found_splits[0][0].lower() in ["train", "training"])
    if auto_partition:
        print("  * Dataset nguồn chỉ có 1 split duy nhất ('train'). Tự động phân bổ: 70% train, 20% val, 10% test.")

    for orig_split, split_root in found_splits:
        # Tìm thư mục images và labels
        img_dir = split_root / "images" if (split_root / "images").exists() else split_root
        lbl_dir = split_root / "labels" if (split_root / "labels").exists() else None

        # Trường hợp cấu trúc images/train, labels/train
        if (source_dir / "images" / orig_split).exists():
            img_dir = source_dir / "images" / orig_split
        if (source_dir / "labels" / orig_split).exists():
            lbl_dir = source_dir / "labels" / orig_split

        images = [p for p in img_dir.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]]
        if auto_partition:
            import random
            random.Random(42).shuffle(images)
        else:
            images = sorted(images)
        num_images = len(images)

        for idx, img_path in enumerate(images):
            # Tránh nhân đôi dữ liệu nếu ảnh đã tồn tại trong data/
            if img_path.name in existing_file_names or f"{dataset_prefix}_{img_path.name}" in existing_file_names:
                continue

            if auto_partition:
                if idx < int(0.70 * num_images):
                    target_split = "train"
                elif idx < int(0.90 * num_images):
                    target_split = "val"
                else:
                    target_split = "test"
            else:
                target_split = normalize_split_name(orig_split)

            lbl_name = img_path.stem + ".txt"
            lbl_path = None
            if lbl_dir and (lbl_dir / lbl_name).exists():
                lbl_path = lbl_dir / lbl_name
            elif (img_dir.parent / "labels" / lbl_name).exists():
                lbl_path = img_dir.parent / "labels" / lbl_name

            dest_name = f"{dataset_prefix}_{img_path.name}"
            dest_lbl_name = f"{dataset_prefix}_{lbl_name}"

            dest_img = data_dir / "images" / target_split / dest_name
            dest_lbl = data_dir / "labels" / target_split / dest_lbl_name

            boxes = remap_and_copy_file(img_path, lbl_path, dest_img, dest_lbl, id_to_target_cls)
            existing_file_names.add(dest_name)
            existing_file_names.add(img_path.name)
            
            if target_split not in stats["splits"]:
                stats["splits"][target_split] = {"images": 0, "boxes": 0}
            stats["splits"][target_split]["images"] += 1
            stats["splits"][target_split]["boxes"] += boxes
            stats["images"] += 1
            stats["boxes"] += boxes

    for s_name, s_data in stats["splits"].items():
        print(f"  + Split '{s_name}': đã nhập {s_data['images']} ảnh, {s_data['boxes']} bounding boxes")

    print(f"[OK] Nhập thành công: Tổng {stats['images']} ảnh, {stats['boxes']} boxes.")
    return stats


def download_from_roboflow(
    api_key: str,
    workspace: str,
    project: str,
    version: int = 1,
    download_dir: Optional[Path] = None
) -> Optional[Path]:
    """Tải dataset trực tiếp qua Roboflow SDK."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[LỖI] Chưa cài đặt thư viện 'roboflow'. Hãy chạy: pip install roboflow")
        return None

    if download_dir is None:
        download_dir = Path("raw_datasets")
    download_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n>>> Đang tải từ Roboflow: {workspace}/{project} (version {version})...")
    try:
        rf = Roboflow(api_key=api_key)
        prj = rf.workspace(workspace).project(project)
        ver = prj.version(version)
        dataset_location = ver.download("yolov8", location=str(download_dir / project))
        print(f"[OK] Đã tải về thư mục: {dataset_location.location}")
        return Path(dataset_location.location)
    except Exception as e:
        print(f"[LỖI] Không thể tải dataset {workspace}/{project}: {e}")
        return None


def audit_dataset(project_root: Path) -> Dict:
    """
    Kiểm tra toàn diện dữ liệu trong thư mục data/
    Thống kê số ảnh, số file nhãn, số bounding box cho từng class và từng split.
    """
    data_dir = project_root / "data"
    splits = ["train", "val", "test"]

    report = {
        "splits": {},
        "total_images": 0,
        "total_labels": 0,
        "total_boxes": 0,
        "class_counts": {0: 0, 1: 0},
        "empty_labels": 0,
        "missing_labels": 0
    }

    print("\n=======================================================")
    print("         BÁO CÁO KIỂM TOÁN DỮ LIỆU CONVEYORVISION       ")
    print("=======================================================")

    for split in splits:
        img_dir = data_dir / "images" / split
        lbl_dir = data_dir / "labels" / split

        img_files = list(img_dir.glob("*.*")) if img_dir.exists() else []
        img_files = [p for p in img_files if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]]

        split_info = {
            "images": len(img_files),
            "labels": 0,
            "boxes_pass": 0,
            "boxes_defect": 0,
            "empty_labels": 0,
            "missing_labels": 0
        }

        for img_p in img_files:
            lbl_p = lbl_dir / (img_p.stem + ".txt")
            if not lbl_p.exists():
                split_info["missing_labels"] += 1
                report["missing_labels"] += 1
                continue

            split_info["labels"] += 1
            with open(lbl_p, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if not lines:
                split_info["empty_labels"] += 1
                report["empty_labels"] += 1
            else:
                for line in lines:
                    parsed = validate_bbox_line(line)
                    if parsed:
                        cls_id, x, y, w, h = parsed
                        if cls_id == 0:
                            split_info["boxes_pass"] += 1
                            report["class_counts"][0] += 1
                        elif cls_id == 1:
                            split_info["boxes_defect"] += 1
                            report["class_counts"][1] += 1

        total_split_boxes = split_info["boxes_pass"] + split_info["boxes_defect"]
        report["splits"][split] = split_info
        report["total_images"] += split_info["images"]
        report["total_labels"] += split_info["labels"]
        report["total_boxes"] += total_split_boxes

        print(f"\n[Split: {split.upper()}]")
        print(f"  - Số lượng ảnh:         {split_info['images']}")
        print(f"  - Số file nhãn:         {split_info['labels']}")
        print(f"  - Box Pass (0):         {split_info['boxes_pass']}")
        print(f"  - Box Defect (1):       {split_info['boxes_defect']}")
        print(f"  - Nhãn rỗng (nền):      {split_info['empty_labels']}")
        print(f"  - Thiếu file nhãn:      {split_info['missing_labels']}")

    print("\n-------------------------------------------------------")
    print(f"TỔNG CỘNG: {report['total_images']} ảnh | {report['total_boxes']} bounding boxes")
    print(f"  * Class 0 (pass):   {report['class_counts'][0]} boxes")
    print(f"  * Class 1 (defect): {report['class_counts'][1]} boxes")
    print("=======================================================\n")

    return report




def extract_and_import_zip(
    zip_path: Path,
    project_root: Path,
    dataset_prefix: str,
    explicit_class_map: Optional[Dict[str, int]] = None
) -> Dict:
    """Giải nén file ZIP vào thư mục tạm và nhập vào data/"""
    extract_to = project_root / "raw_datasets" / zip_path.stem
    extract_to.mkdir(parents=True, exist_ok=True)
    print(f"\n[ZIP] Đang giải nén: {zip_path.name} -> {extract_to}...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
    return import_dataset_from_dir(extract_to, project_root, dataset_prefix, explicit_class_map)


def resolve_raw_prefix_and_mapping(folder_name: str) -> Tuple[str, Optional[Dict[str, int]]]:
    """Ánh xạ tên thư mục raw về tiền tố và class mapping chuẩn để tránh lệch tiền tố và nhân đôi ảnh."""
    name = folder_name.lower()
    if "bayo" in name or "bottle-detection" in name:
        return "bayo", {"defect": 1, "ok": 0}
    if "defect" in name or "defective" in name:
        return "bottle_defect", {"good": 0, "defective": 1}
    if "conveyor" in name:
        return "conveyor", {"bottle": 0}
    return folder_name.replace(" ", "_").lower(), None


def scan_and_import_raw(project_root: Path) -> int:
    """Tự động quét thư mục raw_datasets/ tìm các file zip hoặc thư mục con để nhập."""
    raw_dir = project_root / "raw_datasets"
    if not raw_dir.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Đã tạo thư mục '{raw_dir.name}/'. Hãy bỏ file ZIP hoặc thư mục dataset vào đây.")
        return 0

    count = 0
    # 1. Quét các file ZIP
    for zip_f in raw_dir.glob("*.zip"):
        prefix, class_map = resolve_raw_prefix_and_mapping(zip_f.stem)
        extract_and_import_zip(zip_f, project_root, prefix, class_map)
        count += 1

    # 2. Quét các thư mục con
    for sub in raw_dir.iterdir():
        if sub.is_dir() and not sub.name.startswith("."):
            prefix, class_map = resolve_raw_prefix_and_mapping(sub.name)
            import_dataset_from_dir(sub, project_root, prefix, class_map)
            count += 1

    return count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ConveyorVision Dataset Pipeline Manager")
    parser.add_argument("--root", type=str, default=".", help="Đường dẫn thư mục dự án ConveyorVision")
    parser.add_argument("--migrate", action="store_true", help="Di chuyển và chuẩn hóa dữ liệu cũ từ root vào data/")
    parser.add_argument("--import-dir", type=str, default=None, help="Nhập dataset từ thư mục đã tải")
    parser.add_argument("--import-zip", type=str, default=None, help="Nhập dataset trực tiếp từ file ZIP")
    parser.add_argument("--scan-raw", action="store_true", help="Tự động quét và nhập mọi file ZIP/thư mục trong raw_datasets/")
    parser.add_argument("--prefix", type=str, default="imported", help="Tiền tố tên ảnh khi nhập")
    parser.add_argument("--api-key", type=str, default=None, help="Roboflow API Key để tải tự động")
    parser.add_argument("--download-all", action="store_true", help="Tự động tải tất cả dataset mục tiêu bằng API Key")
    parser.add_argument("--audit", action="store_true", help="Kiểm toán và in thống kê dataset hiện tại")

    args = parser.parse_args()
    proj_root = Path(args.root).resolve()

    # Cập nhật YAML
    update_data_yaml(proj_root)

    if args.migrate:
        migrate_root_dataset(proj_root)

    if args.import_dir:
        import_path = Path(args.import_dir).resolve()
        import_dataset_from_dir(import_path, proj_root, args.prefix)

    if args.import_zip:
        zip_path = Path(args.import_zip).resolve()
        extract_and_import_zip(zip_path, proj_root, args.prefix)

    if args.scan_raw:
        scan_and_import_raw(proj_root)

    if args.download_all:
        api_key = args.api_key or os.getenv("ROBOFLOW_API_KEY")
        if not api_key:
            print("[LỖI] Vui lòng cung cấp --api-key hoặc thiết lập biến môi trường ROBOFLOW_API_KEY!")
            sys.exit(1)

        # Danh sách dataset mục tiêu cho bài toán ConveyorVision (đầy đủ 2.666 ảnh)
        target_datasets = [
            {
                "workspace": "anky06",
                "project": "conveyor-belt-eafpe-bgzzm",
                "version": 1,
                "prefix": "conveyor",
                "mapping": {"bottle": 0}
            },
            {
                "workspace": "bayo-et081",
                "project": "bottle-detection-qti1t",
                "version": 1,
                "prefix": "bayo",
                "mapping": {"defect": 1, "ok": 0}
            },
            {
                "workspace": "anky06",
                "project": "bottle_defects-tpmcq-kijtp",
                "version": 1,
                "prefix": "bottle_defect",
                "mapping": {"good": 0, "defective": 1}
            }
        ]

        raw_dir = proj_root / "raw_datasets"
        download_errors = 0
        for ds in target_datasets:
            loc = download_from_roboflow(api_key, ds["workspace"], ds["project"], ds["version"], raw_dir)
            if loc and loc.exists():
                import_dataset_from_dir(loc, proj_root, ds["prefix"], ds["mapping"])
            else:
                download_errors += 1
                print(f"[LỖI] Tải dataset '{ds['workspace']}/{ds['project']}' thất bại!")

        if download_errors > 0:
            print(f"\n[LỖI NGHIÊM TRỌNG] Có {download_errors}/{len(target_datasets)} dataset tải không thành công.")
            sys.exit(1)

    # Luôn kiểm toán dữ liệu
    report = audit_dataset(proj_root)
    if report["total_images"] == 0:
        print("[LỖI] Thư mục data/images không có dữ liệu ảnh hợp lệ.")
        sys.exit(1)
