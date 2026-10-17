import sys
from pathlib import Path
import pytest
import yaml

# Add src to path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from conveyorvision.dataset_manager import resolve_raw_prefix_and_mapping, normalize_split_name
from ultralytics import YOLO


def test_data_yaml_structure():
    """Verify data/data.yaml exists, is valid YAML, and has standard pass/defect classes."""
    data_yaml = Path(__file__).resolve().parent.parent / "data" / "data.yaml"
    assert data_yaml.exists(), "data/data.yaml must exist."

    with open(data_yaml, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "names" in config, "data.yaml must contain 'names' mapping."
    names = config["names"]
    assert names[0] == "pass", "Class 0 must be 'pass'."
    assert names[1] == "defect", "Class 1 must be 'defect'."


def test_yolo26_native_architecture():
    """Verify yolo26n.pt is a native YOLO26 model with end-to-end NMS-free head."""
    model_path = Path(__file__).resolve().parent.parent / "yolo26n.pt"
    assert model_path.exists(), "yolo26n.pt must exist in repository root."

    model = YOLO(str(model_path))
    yaml_config = getattr(model.model, "yaml", {})
    yaml_file = yaml_config.get("yaml_file", "").lower()
    is_end2end = yaml_config.get("end2end", False)

    assert "yolo26" in yaml_file or is_end2end is True, "Model must be YOLO26 native architecture."


def test_dataset_manager_raw_prefix_and_mapping():
    """Test prefix and class mapping resolution for raw datasets."""
    prefix, mapping = resolve_raw_prefix_and_mapping("bayo_bottle")
    assert prefix == "bayo"
    assert mapping.get("defect") == 1
    assert mapping.get("ok") == 0

    prefix_def, mapping_def = resolve_raw_prefix_and_mapping("bottle_defects")
    assert prefix_def == "bottle_defect"
    assert mapping_def.get("defective") == 1
    assert mapping_def.get("good") == 0


def test_normalize_split_name():
    """Test split name normalization."""
    assert normalize_split_name("valid") == "val"
    assert normalize_split_name("validation") == "val"
    assert normalize_split_name("test") == "test"
    assert normalize_split_name("train") == "train"
    assert normalize_split_name("training") == "train"
    assert normalize_split_name("unknown") == "unknown"
