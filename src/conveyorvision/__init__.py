# -*- coding: utf-8 -*-
"""ConveyorVision - Hệ thống phân loại sản phẩm trên băng chuyền sử dụng YOLO26.

Thư viện Python cung cấp pipeline hoàn chỉnh cho bài toán kiểm định chất lượng 
sản phẩm trên băng chuyền công nghiệp với khả năng:
- Nhận diện và theo vết vật thể thời gian thực (Object Tracking)
- Phân loại sản phẩm ĐẠT/LỖI (Pass/Defect)
- Huấn luyện và đánh giá mô hình YOLO26
- Quản lý và chuẩn hóa dataset từ nhiều nguồn
- Giao diện Web Dashboard trực quan

Example:
    >>> from conveyorvision import train_pilot, evaluate_model
    >>> train_pilot(epochs=30, batch_size=16)
    >>> evaluate_model(split="test")
"""

__version__ = "2.0.0"
__author__ = "ConveyorVision Team"
__email__ = "contact@conveyorvision.com"

from conveyorvision.dataset_manager import (
    audit_dataset,
    import_dataset_from_dir,
    download_from_roboflow,
    scan_and_import_raw,
    update_data_yaml,
)
from conveyorvision.train_pilot import train_pilot
from conveyorvision.evaluate import evaluate_model
from conveyorvision.inference_conveyor import run_conveyor_inspection
from conveyorvision.video_io import extract_frames

__all__ = [
    # Dataset Management
    "audit_dataset",
    "import_dataset_from_dir",
    "download_from_roboflow",
    "scan_and_import_raw",
    "update_data_yaml",
    # Training & Evaluation
    "train_pilot",
    "evaluate_model",
    # Inference & Inspection
    "run_conveyor_inspection",
    # Video Processing
    "extract_frames",
    # Package Info
    "__version__",
    "__author__",
    "__email__",
]
