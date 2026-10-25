"""Unit & Integration Tests cho ConveyorVision Web Dashboard."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

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
    """Kiểm tra API /api/dataset_info trả về đúng cấu trúc tập dữ liệu."""
    response = client.get("/api/dataset_info")
    assert response.status_code == 200
    data = response.json()
    
    # Kiểm tra cấu trúc response
    assert "total_images" in data
    assert "splits" in data
    assert "train" in data["splits"]
    assert "val" in data["splits"]
    assert "test" in data["splits"]
    assert "classes" in data
    assert len(data["classes"]) == 2
    
    # Skip test value checking nếu dataset chưa có
    if data["total_images"] == 0:
        pytest.skip("Dataset chưa được download, skip test giá trị")
    
    # Kiểm tra tính hợp lệ của số liệu nếu có data
    assert data["total_images"] > 0
    assert data["splits"]["train"]["count"] >= 0
    assert data["splits"]["val"]["count"] >= 0
    assert data["splits"]["test"]["count"] >= 0


def test_evaluation_api(client):
    """Kiểm tra API /api/evaluation trả về đầy đủ các chỉ số test và cảnh báo near-duplicate."""
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    data = response.json()
    
    # Kiểm tra cấu trúc response
    assert "test_metrics" in data
    assert "overall" in data["test_metrics"]
    assert "map50" in data["test_metrics"]["overall"]
    assert "precision" in data["test_metrics"]["overall"]
    assert "recall" in data["test_metrics"]["overall"]

    # Kiểm tra nội dung cảnh báo rủi ro dữ liệu cận trùng
    warning = data["data_leakage_warning"]
    assert "message" in warning
    assert "recommendation" in warning

    # Kiểm tra danh sách biểu đồ
    assert "charts" in data
    assert len(data["charts"]) >= 4


def test_models_api(client):
    """Kiểm tra API /api/models quét được checkpoint .pt trong repository."""
    response = client.get("/api/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    
    # Kiểm tra cấu trúc từng model entry
    if len(models) > 0:
        model = models[0]
        assert "name" in model
        assert "path" in model
        assert "size_mb" in model
        assert "modified" in model


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


def test_settings_api(client):
    """Kiểm tra API cấu hình tham số hệ thống."""
    # Lấy cài đặt
    res = client.get("/api/settings")
    assert res.status_code == 200
    settings = res.json()
    assert "tracker" in settings
    assert "lost_track_buffer" in settings

    # Cập nhật cài đặt
    update_payload = {
        "tracker": "botsort.yaml",
        "lost_track_buffer": 40,
        "min_observation_votes": 4,
        "auto_save_csv": False,
        "sound_alarm": False
    }
    update_res = client.post("/api/settings", json=update_payload)
    assert update_res.status_code == 200
    saved = update_res.json()["settings"]
    assert saved["tracker"] == "botsort.yaml"
    assert saved["lost_track_buffer"] == 40
    assert saved["min_observation_votes"] == 4
    assert saved["auto_save_csv"] is False

    # Khôi phục cài đặt mặc định
    client.post("/api/settings", json={"tracker": "bytetrack.yaml", "lost_track_buffer": 30, "min_observation_votes": 3, "auto_save_csv": True, "sound_alarm": True})


def test_video_upload_validation(client):
    """Kiểm tra từ chối các định dạng file không an toàn khi upload."""
    files = {"file": ("malicious.exe", b"invalid binary content", "application/octet-stream")}
    res = client.post("/api/upload_video", files=files)
    assert res.status_code == 400
    assert "Chỉ hỗ trợ file video" in res.json()["detail"]


def test_worker_multi_mode_support():
    """Kiểm tra worker hỗ trợ chế độ 'bottle_and_other' và 'bottle_inspection'."""
    worker = InspectionWorker()
    assert hasattr(worker, "total_other")
    assert worker.total_other == 0
    worker.inspection_mode = "bottle_and_other"
    status = worker.get_status()
    assert "total_other" in status
    assert status["total_other"] == 0


def test_download_pdf_report_api(client):
    """Kiểm tra API tải báo cáo tổng kết dạng PDF."""
    res = client.get("/api/download_pdf_report")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "BaoCao_TongKet_ConveyorVision.pdf" in res.headers.get("content-disposition", "")
    assert len(res.content) > 100000


def test_download_pdf_uiux_api(client):
    """Kiểm tra API tải cẩm nang hướng dẫn sử dụng UI/UX dạng PDF."""
    res = client.get("/api/download_pdf_uiux")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "HuongDan_SuDung_UIUX_ConveyorVision.pdf" in res.headers.get("content-disposition", "")
    assert len(res.content) > 50000


