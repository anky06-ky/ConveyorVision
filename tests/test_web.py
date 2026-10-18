"""Unit & Integration Tests cho ConveyorVision Web Dashboard."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conveyorvision.web.server import app
from conveyorvision.web.session_manager import SessionManager
from conveyorvision.web.worker import InspectionWorker


@pytest.fixture
def client():
    return TestClient(app)


def test_index_page(client):
    """Kiểm tra trang chính HTML SPA tải thành công."""
    response = client.get("/")
    assert response.status_code == 200
    assert "ConveyorVision" in response.text
    assert "Trạm 01" in response.text
    assert "video-stream-feed" in response.text


def test_system_status_api(client):
    """Kiểm tra API /api/status trả về đúng cấu trúc trạng thái."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "fps" in data
    assert "total_pass" in data
    assert "total_defect" in data
    assert "inspecting_count" in data
    assert "defect_rate" in data


def test_dataset_info_api(client):
    """Kiểm tra API /api/dataset_info trả về đúng số liệu tập dữ liệu."""
    response = client.get("/api/dataset_info")
    assert response.status_code == 200
    data = response.json()
    assert data["total_images"] == 2666
    assert data["splits"]["train"]["count"] == 1692
    assert data["splits"]["val"]["count"] == 533
    assert data["splits"]["test"]["count"] == 441
    assert len(data["classes"]) == 2


def test_evaluation_api(client):
    """Kiểm tra API /api/evaluation trả về đầy đủ các chỉ số test và cảnh báo near-duplicate."""
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert data["test_metrics"]["overall"]["map50"] == 82.5
    assert data["test_metrics"]["overall"]["precision"] == 78.2
    assert data["test_metrics"]["overall"]["recall"] == 75.7

    # Kiểm tra nội dung cảnh báo rủi ro dữ liệu cận trùng
    warning = data["data_leakage_warning"]
    assert "53–54" in warning["message"] or "53 - 54" in warning["pairs_detected"]
    assert "session-based" in warning["message"] or "session-based" in warning["recommendation"]

    # Kiểm tra danh sách biểu đồ
    assert len(data["charts"]) >= 4


def test_models_api(client):
    """Kiểm tra API /api/models quét được checkpoint .pt trong repository."""
    response = client.get("/api/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    model_names = [m["name"] for m in models]
    assert "conveyor_yolo26_30ep_best.pt" in model_names


def test_history_and_session_manager(tmp_path):
    """Kiểm tra vòng đời quản lý phiên (SessionManager) và xuất log CSV."""
    sm = SessionManager(base_dir=tmp_path)
    session = sm.create_session(
        source="test_video.mp4",
        model_name="yolo26n.pt",
        tracker="bytetrack.yaml",
        conf_thresh=0.45
    )
    assert session["session_id"].startswith("SES_")
    assert (tmp_path / session["csv_file"]).exists()

    # Finalize phiên
    tracks = [
        {"track_id": 1, "state": "PASS", "class_name": "pass", "max_conf": 0.88, "first_ts": 0.5, "last_ts": 2.1, "obs_votes": 8, "was_corrected": False},
        {"track_id": 2, "state": "DEFECT", "class_name": "defect", "max_conf": 0.92, "first_ts": 1.2, "last_ts": 2.5, "obs_votes": 5, "was_corrected": True}
    ]
    fin = sm.finalize_session(
        session_id=session["session_id"],
        total_pass=1,
        total_defect=1,
        avg_fps=15.0,
        duration_sec=3.5,
        tracks=tracks
    )
    assert fin is not None
    assert fin["status"] == "COMPLETED"
    assert fin["total_items"] == 2
    assert fin["defect_rate"] == 50.0

    # Lấy lại session
    fetched = sm.get_session(session["session_id"])
    assert fetched["session_id"] == session["session_id"]
    assert len(fetched["tracks"]) == 2

    # Xóa session
    deleted = sm.delete_session(session["session_id"])
    assert deleted is True
    assert sm.get_session(session["session_id"]) is None


def test_worker_lifecycle():
    """Kiểm tra các trạng thái cơ bản của InspectionWorker."""
    worker = InspectionWorker()
    assert worker.state == "STOPPED"
    status = worker.get_status()
    assert status["state"] == "STOPPED"
    assert status["total_pass"] == 0
    assert status["total_defect"] == 0
    assert worker.latest_jpeg is not None  # Frame idle được tạo sẵn

    # Thử chụp snapshot khi có frame idle
    snap_path = worker.capture_snapshot()
    assert snap_path is not None
    assert Path(snap_path).exists()


def test_websocket_events(client):
    """Kiểm tra kết nối WebSocket và nhận dữ liệu khởi tạo."""
    with client.websocket_connect("/ws/events") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "init_status"
        assert "payload" in data
        assert "state" in data["payload"]
        websocket.send_text("ping")
        resp = websocket.receive_text()
        assert resp == "pong"

