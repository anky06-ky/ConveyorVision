"""FastAPI Web Server cho ConveyorVision.

Cung cấp:
- Single Page Application (SPA) dashboard chuyên nghiệp.
- Endpoint Video MJPEG Stream `/api/video_feed`.
- WebSocket `/ws/events` phát tán sự kiện thời gian thực.
- REST API điều khiển kiểm định, quản lý phiên, truy vấn đánh giá mô hình và tập dữ liệu.
"""

import asyncio
import logging
import os
import shutil
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from conveyorvision.web.session_manager import session_manager
from conveyorvision.web.worker import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("conveyorvision.server")

# Đường dẫn thư mục
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
EVAL_DIR = REPO_ROOT / "doc" / "evaluation"
REPORTS_DIR = REPO_ROOT / "reports"
RAW_VIDEOS_DIR = REPO_ROOT / "raw_videos"
MODELS_DIR = REPO_ROOT / "models"

RAW_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ws_manager.set_loop(asyncio.get_running_loop())
    logger.info("ConveyorVision Web Server đã khởi động thành công.")
    yield


app = FastAPI(
    title="ConveyorVision Dashboard",
    description="Hệ thống kiểm định & phân loại sản phẩm thời gian thực trên băng chuyền công nghiệp",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount thư mục tĩnh
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if EVAL_DIR.exists():
    app.mount("/doc/evaluation", StaticFiles(directory=str(EVAL_DIR)), name="eval_assets")

if (REPORTS_DIR / "snapshots").exists():
    app.mount("/reports/snapshots", StaticFiles(directory=str(REPORTS_DIR / "snapshots")), name="snapshots")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Quản lý kết nối WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client WebSocket kết nối. Tổng số: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client WebSocket ngắt kết nối. Còn lại: {len(self.active_connections)}")

    async def broadcast_json(self, data: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

    def dispatch_from_thread(self, event_type: str, payload: Dict[str, Any]):
        """Hàm callback được gọi từ worker thread để phát tán qua WebSocket."""
        if self._loop and self._loop.is_running():
            msg = {"type": event_type, "payload": payload, "timestamp": time.time()}
            asyncio.run_coroutine_threadsafe(self.broadcast_json(msg), self._loop)


ws_manager = ConnectionManager()
worker.subscribe_events(ws_manager.dispatch_from_thread)


# ==============================================================================
# 1. GIAO DIỆN CHÍNH (HTML SPA)
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# ==============================================================================
# 2. VIDEO STREAMING (MJPEG)
# ==============================================================================
def mjpeg_frame_generator():
    """Generator stream khung hình JPEG liên tục cho thẻ <img>."""
    while True:
        frame_bytes = worker.latest_jpeg
        if frame_bytes:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
        time.sleep(0.033)  # ~30 FPS


@app.get("/api/video_feed")
async def video_feed():
    return StreamingResponse(
        mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==============================================================================
# 3. WEBSOCKET REAL-TIME EVENTS
# ==============================================================================
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Gửi ngay trạng thái hiện tại khi client kết nối
        await websocket.send_json({
            "type": "init_status",
            "payload": worker.get_status()
        })
        while True:
            # Lắng nghe tin nhắn từ client (nếu có, e.g. ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Lỗi WebSocket: {e}")
        ws_manager.disconnect(websocket)


# ==============================================================================
# 4. REST API - ĐIỀU KHIỂN KIỂM ĐỊNH
# ==============================================================================
class StartInspectionRequest(BaseModel):
    source: str = "raw_videos/conveyor_demo.mp4"
    model: str = "models/conveyor_yolo26_30ep_best.pt"
    conf: float = 0.45
    tracker: str = "bytetrack.yaml"
    loop: bool = True


@app.get("/api/status")
async def get_system_status():
    return worker.get_status()


@app.post("/api/start_inspection")
async def start_inspection(req: StartInspectionRequest):
    res = worker.start(
        source=req.source,
        model_path=req.model,
        conf_thresh=req.conf,
        tracker_config=req.tracker,
        loop_video=req.loop
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Không thể khởi động kiểm định"))
    return res


@app.post("/api/pause_inspection")
async def pause_inspection():
    res = worker.pause()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.post("/api/resume_inspection")
async def resume_inspection():
    res = worker.resume()
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.post("/api/stop_inspection")
async def stop_inspection():
    res = worker.stop()
    return res


@app.post("/api/snapshot")
async def capture_snapshot():
    path = worker.capture_snapshot()
    if not path:
        raise HTTPException(status_code=400, detail="Không có khung hình để chụp")
    filename = Path(path).name
    return {"success": True, "url": f"/reports/snapshots/{filename}", "path": path}


@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    """Cho phép tải file video (.mp4, .avi, .mov) lên trạm để kiểm tra ngay."""
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file video (.mp4, .avi, .mov, .mkv)")

    dest_path = RAW_VIDEOS_DIR / file.filename
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        rel_path = f"raw_videos/{file.filename}"
        return {"success": True, "source": rel_path, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu file: {e}")


# ==============================================================================
# 5. REST API - LỊCH SỬ KIỂM ĐỊNH & BÁO CÁO CSV
# ==============================================================================
@app.get("/api/history")
async def get_history():
    return session_manager.get_all_sessions()


@app.get("/api/history/{session_id}")
async def get_session_detail(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên kiểm định")
    return session


@app.delete("/api/history/{session_id}")
async def delete_session(session_id: str):
    ok = session_manager.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên cần xóa")
    return {"success": True, "session_id": session_id}


@app.get("/api/download_report/{session_id}")
async def download_report(session_id: str):
    csv_path = session_manager.get_session_csv_path(session_id)
    if not csv_path or not csv_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file log CSV của phiên này")
    return FileResponse(
        path=str(csv_path),
        filename=f"Bao_cao_kiem_dinh_{session_id}.csv",
        media_type="text/csv"
    )


# ==============================================================================
# 6. REST API - ĐÁNH GIÁ MÔ HÌNH (MODEL EVALUATION)
# ==============================================================================
@app.get("/api/evaluation")
async def get_evaluation_data():
    """Trả về toàn bộ số liệu đánh giá chuẩn xác từ doc/evaluation/README.md."""
    return {
        "model_architecture": "YOLO26 Nano (End-to-end NMS-free)",
        "parameters": "2,504,580 (5.9 GFLOPs)",
        "weight_size_mb": 5.45,
        "training_epochs": 30,
        "training_time_sec": 463.2,
        "validation_metrics": {
            "num_images": 533,
            "precision": 78.7,
            "recall": 79.3,
            "map50": 82.0,
            "map50_95": 58.0,
            "box_loss": 1.097,
            "cls_loss": 2.276
        },
        "test_metrics": {
            "num_images": 441,
            "num_boxes": 1032,
            "overall": {
                "precision": 78.2,
                "recall": 75.7,
                "map50": 82.5,
                "map50_95": 61.4
            },
            "classes": [
                {
                    "class_id": 0,
                    "name": "pass (Đạt chuẩn)",
                    "images": 381,
                    "boxes": 991,
                    "precision": 79.7,
                    "recall": 66.1,
                    "map50": 78.9,
                    "map50_95": 51.2
                },
                {
                    "class_id": 1,
                    "name": "defect (Khuyết tật/Lỗi)",
                    "images": 36,
                    "boxes": 41,
                    "precision": 76.6,
                    "recall": 85.4,
                    "map50": 86.2,
                    "map50_95": 71.7
                }
            ]
        },
        "speed_benchmark": {
            "device": "Intel Core i7-8565U CPU @ 1.80GHz",
            "preprocess_ms": 3.1,
            "inference_ms": 125.9,
            "postprocess_ms": 2.4,
            "total_ms": 131.4,
            "fps_cpu": 7.9,
            "fps_gpu_projected": "> 80 FPS (TensorRT / Jetson Orin Nano)"
        },
        "data_leakage_warning": {
            "title": "Lưu ý phương pháp luận — Rủi ro rò rỉ dữ liệu cận trùng (Near-Duplicate Leakage)",
            "message": "Qua kiểm tra đối sánh hàm băm tri giác (pHash/SSIM), ghi nhận khoảng 53–54 cặp ảnh cận trùng giữa tập Train và tập Test (41 ảnh test có bản sao rất gần trong train, trong đó có 23/36 ảnh test chứa defect). Do đó, chỉ số mAP 82.5% trên tập test hiện tại là ngưỡng kỳ vọng tối đa (upper bound). Bắt buộc phải chia lại dữ liệu theo phiên quay (session-based split) trước khi nghiệm thu thực địa.",
            "pairs_detected": "53 - 54 cặp",
            "affected_defect_test_images": "23 / 36 ảnh (63.9%)",
            "recommendation": "Phân chia tập test theo video clip/session sản xuất độc lập"
        },
        "charts": [
            {
                "id": "training_progress",
                "title": "Tiến trình huấn luyện 30 Epochs (Loss & mAP Curves)",
                "image_url": "/doc/evaluation/results.png",
                "description": "Biểu đồ biến thiên Train/Val Box Loss, Class Loss và độ dốc hội tụ mAP@50 qua từng epoch."
            },
            {
                "id": "confusion_matrix",
                "title": "Ma trận nhầm lẫn Test (Normalized Confusion Matrix)",
                "image_url": "/doc/evaluation/test_confusion_matrix_normalized.png",
                "description": "Tỷ lệ dự đoán chính xác giữa nhãn thực tế và nhãn dự đoán trên 441 ảnh phân tập test."
            },
            {
                "id": "pr_curve",
                "title": "Đường cong Precision - Recall (PR Curve)",
                "image_url": "/doc/evaluation/test_BoxPR_curve.png",
                "description": "Quan hệ đánh đổi giữa Độ chính xác (Precision) và Độ nhạy (Recall) cho từng lớp sản phẩm."
            },
            {
                "id": "test_predictions",
                "title": "Hình ảnh nhận diện thực tế trên tập Test",
                "image_url": "/doc/evaluation/test_batch0_pred.jpg",
                "description": "Mẫu bounding boxes và nhãn phân loại mô hình dự đoán trên batch thử nghiệm."
            }
        ]
    }


# ==============================================================================
# 7. REST API - DỮ LIỆU & MÔ HÌNH (DATASET & MODELS)
# ==============================================================================
@app.get("/api/dataset_info")
async def get_dataset_info():
    train_dir = REPO_ROOT / "data" / "images" / "train"
    val_dir = REPO_ROOT / "data" / "images" / "val"
    test_dir = REPO_ROOT / "data" / "images" / "test"

    train_c = len(list(train_dir.glob("*.jpg"))) if train_dir.exists() else 1692
    val_c = len(list(val_dir.glob("*.jpg"))) if val_dir.exists() else 533
    test_c = len(list(test_dir.glob("*.jpg"))) if test_dir.exists() else 441
    total_c = train_c + val_c + test_c

    return {
        "dataset_name": "ConveyorVision Industrial Bottles",
        "total_images": total_c,
        "splits": {
            "train": {"count": train_c, "pct": round(train_c / total_c * 100, 1)},
            "val": {"count": val_c, "pct": round(val_c / total_c * 100, 1)},
            "test": {"count": test_c, "pct": round(test_c / total_c * 100, 1)}
        },
        "classes": [
            {"id": 0, "name": "pass (Đạt chuẩn)", "ratio_pct": 85.2, "description": "Chai đủ thể tích, nhãn thẳng, nắp đậy khít"},
            {"id": 1, "name": "defect (Khuyết tật/Lỗi)", "ratio_pct": 14.8, "description": "Thiếu nắp, nắp vênh, xước nhãn, nứt vỡ hoặc thiếu thể tích"}
        ],
        "image_resolution": "640x640 (RGB)",
        "source_format": "YOLOv8/YOLO26 PyTorch Format"
    }


@app.get("/api/models")
async def get_available_models():
    """Quét và liệt kê các checkpoint trọng số sẵn có trong repository."""
    models_list = []
    seen_paths = set()

    candidate_dirs = [MODELS_DIR, REPO_ROOT / "runs"]
    for cdir in candidate_dirs:
        if cdir.exists():
            for pt in cdir.rglob("*.pt"):
                abs_str = str(pt.resolve())
                if abs_str not in seen_paths:
                    seen_paths.add(abs_str)
                    rel_path = pt.relative_to(REPO_ROOT).as_posix()
                    size_mb = round(pt.stat().st_size / (1024 * 1024), 2)
                    mtime = datetime.fromtimestamp(pt.stat().st_mtime).strftime("%H:%M %d/%m/%Y")
                    is_active = (pt.name == "conveyor_yolo26_30ep_best.pt")

                    models_list.append({
                        "name": pt.name,
                        "path": rel_path,
                        "size_mb": size_mb,
                        "modified": mtime,
                        "is_active": is_active,
                        "description": "Mô hình sản xuất chính (30 Epochs, Colab L4/T4)" if is_active else "Checkpoint thử nghiệm / pilot"
                    })

    # Đưa model active lên đầu danh sách
    models_list.sort(key=lambda m: (not m["is_active"], m["name"]))
    return models_list
