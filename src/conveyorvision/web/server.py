"""FastAPI Web Server cho ConveyorVision.

Cung cấp:
- Single Page Application (SPA) dashboard chuyên nghiệp.
- Endpoint Video MJPEG Stream `/api/video_feed`.
- WebSocket `/ws/events` phát tán sự kiện thời gian thực.
- REST API điều khiển kiểm định, cấu hình hệ thống, quản lý phiên, truy vấn đánh giá mô hình và tập dữ liệu.
- Cơ chế bảo mật: Chống Path Traversal, giới hạn dung lượng tải video, cấu hình CORS an toàn.
"""

import asyncio
import csv
import logging
import os
import re
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

# Đường dẫn thư mục chuẩn
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
EVAL_DIR = REPO_ROOT / "doc" / "evaluation"
REPORTS_DIR = REPO_ROOT / "reports"
SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
RAW_VIDEOS_DIR = REPO_ROOT / "raw_videos"
MODELS_DIR = REPO_ROOT / "models"

# Đảm bảo các thư mục luôn sẵn sàng trước khi mount tĩnh
RAW_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB


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

# Cấu hình CORS an toàn cho trạm cục bộ
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount thư mục tĩnh (chắc chắn snapshots tồn tại để bản clone mới không bị 404)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if EVAL_DIR.exists():
    app.mount("/doc/evaluation", StaticFiles(directory=str(EVAL_DIR)), name="eval_assets")

app.mount("/reports/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")

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
        try:
            loop = self._loop
            if loop and loop.is_running():
                msg = {"type": event_type, "payload": payload, "timestamp": time.time()}
                asyncio.run_coroutine_threadsafe(self.broadcast_json(msg), loop)
        except Exception as e:
            logger.warning(f"Lỗi gửi tin WebSocket: {e}")


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
    """Generator stream khung hình JPEG với độ trễ thấp, đồng bộ theo Condition Variable chống lag."""
    last_seq = -1
    while True:
        with worker._frame_cond:
            worker._frame_cond.wait_for(
                lambda: worker._frame_seq != last_seq or worker.state == "STOPPED",
                timeout=0.25
            )
            last_seq = worker._frame_seq
            frame_bytes = worker.latest_jpeg

        if frame_bytes:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )


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
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"Lỗi WebSocket: {e}")
        ws_manager.disconnect(websocket)


# ==============================================================================
# 4. REST API - ĐIỀU KHIỂN KIỂM ĐỊNH & CÀI ĐẶT
# ==============================================================================
class StartInspectionRequest(BaseModel):
    source: str = "raw_videos/conveyor_demo.mp4"
    model: str = "models/conveyor_yolo26_30ep_best.pt"
    mode: str = "bottle_and_other"  # "bottle_and_other" hoặc "bottle_inspection"
    conf: float = 0.45
    tracker: str = "bytetrack.yaml"
    imgsz: int = 480
    loop: bool = True
    lost_track_buffer: Optional[int] = None
    min_observation_votes: Optional[int] = None
    auto_save_csv: Optional[bool] = None


class SettingsUpdateRequest(BaseModel):
    tracker: Optional[str] = None
    lost_track_buffer: Optional[int] = None
    min_observation_votes: Optional[int] = None
    auto_save_csv: Optional[bool] = None
    sound_alarm: Optional[bool] = None
    default_conf: Optional[float] = None


@app.get("/api/status")
async def get_system_status():
    return worker.get_status()


@app.get("/api/settings")
async def get_settings():
    return session_manager.get_settings()


@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    dump_fn = getattr(req, "model_dump", None) or getattr(req, "dict")
    payload = {k: v for k, v in dump_fn().items() if v is not None}
    saved = session_manager.save_settings(payload)
    return {"success": True, "settings": saved}


@app.post("/api/start_inspection")
async def start_inspection(req: StartInspectionRequest):
    res = worker.start(
        source=req.source,
        model_path=req.model,
        inspection_mode=req.mode,
        conf_thresh=req.conf,
        tracker_config=req.tracker,
        imgsz=req.imgsz,
        loop_video=req.loop,
        lost_track_buffer=req.lost_track_buffer,
        min_observation_votes=req.min_observation_votes,
        auto_save_csv=req.auto_save_csv
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
    """Cho phép tải file video lên trạm với xác thực bảo mật và giới hạn dung lượng."""
    original_filename = Path(file.filename or "").name
    ext = Path(original_filename).suffix.lower()
    if ext not in (".mp4", ".avi", ".mov", ".mkv"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file video (.mp4, .avi, .mov, .mkv)")

    # Chuẩn hóa tên file an toàn (chống chèn ký tự lạ và Path Traversal)
    base_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(original_filename).stem)
    if not base_stem:
        base_stem = f"upload_{int(time.time())}"
    safe_filename = f"{base_stem}{ext}"

    dest_path = (RAW_VIDEOS_DIR / safe_filename).resolve()
    # Kiểm tra nghiêm ngặt đường dẫn đích nằm trong RAW_VIDEOS_DIR
    if not dest_path.is_relative_to(RAW_VIDEOS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ hoặc chứa đường dẫn trái phép.")

    size_read = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    try:
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size_read += len(chunk)
                if size_read > MAX_UPLOAD_SIZE:
                    buffer.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Dung lượng file vượt quá giới hạn 200MB.")
                buffer.write(chunk)
        rel_path = f"raw_videos/{safe_filename}"
        return {"success": True, "source": rel_path, "filename": safe_filename}
    except HTTPException:
        raise
    except Exception as e:
        dest_path.unlink(missing_ok=True)
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


@app.get("/api/download_pdf_report")
async def download_pdf_report():
    """Tải về bản báo cáo nghiệm thu kỹ thuật định dạng PDF hoàn chỉnh của dự án."""
    pdf_path = REPO_ROOT / "doc" / "BAO_CAO_TONG_KET_CONVEYORVISION.pdf"
    if not pdf_path.exists():
        try:
            import importlib.util
            gen_script = REPO_ROOT / "scripts" / "generate_pdf_report.py"
            if gen_script.exists():
                spec = importlib.util.spec_from_file_location("generate_pdf_report", str(gen_script))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.build_pdf(str(pdf_path))
        except Exception as e:
            logger.error(f"Lỗi sinh báo cáo PDF: {e}")

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file báo cáo PDF tổng kết")

    return FileResponse(
        path=str(pdf_path),
        filename="BaoCao_TongKet_ConveyorVision.pdf",
        media_type="application/pdf"
    )


@app.get("/api/download_pdf_uiux")
async def download_pdf_uiux():
    """Tải về tài liệu hướng dẫn sử dụng giao diện và vận hành UI/UX định dạng PDF."""
    pdf_path = REPO_ROOT / "doc" / "HUONG_DAN_SU_DUNG_UI_UX.pdf"
    if not pdf_path.exists():
        try:
            import importlib.util
            gen_script = REPO_ROOT / "scripts" / "generate_pdf_uiux.py"
            if gen_script.exists():
                spec = importlib.util.spec_from_file_location("generate_pdf_uiux", str(gen_script))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.build_pdf(str(pdf_path))
        except Exception as e:
            logger.error(f"Lỗi sinh cẩm nang UI/UX PDF: {e}")

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file cẩm nang UI/UX PDF")

    return FileResponse(
        path=str(pdf_path),
        filename="HuongDan_SuDung_UIUX_ConveyorVision.pdf",
        media_type="application/pdf"
    )


@app.get("/api/download_pdf_master")
async def download_pdf_master():
    """Tải về tài liệu kỹ thuật toàn diện và kiến trúc hệ thống ConveyorVision định dạng PDF."""
    pdf_path = REPO_ROOT / "doc" / "TAI_LIEU_TOAN_DIEN_DO_AN_CONVEYORVISION.pdf"
    if not pdf_path.exists():
        try:
            import importlib.util
            gen_script = REPO_ROOT / "scripts" / "generate_master_doc_pdf.py"
            if gen_script.exists():
                spec = importlib.util.spec_from_file_location("generate_master_doc_pdf", str(gen_script))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.build_pdf(str(pdf_path))
        except Exception as e:
            logger.error(f"Lỗi sinh tài liệu toàn diện PDF: {e}")

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file tài liệu kỹ thuật toàn diện PDF")

    return FileResponse(
        path=str(pdf_path),
        filename="TaiLieu_ToanDien_DoAn_ConveyorVision.pdf",
        media_type="application/pdf"
    )


# ==============================================================================
# 6. REST API - ĐÁNH GIÁ MÔ HÌNH (MODEL EVALUATION)
# ==============================================================================
@app.get("/api/evaluation")
async def get_evaluation_data():
    """Trả về số liệu đánh giá mô hình, đọc cập nhật động từ kết quả huấn luyện mới nhất."""
    # Tìm file results.csv mới nhất nếu có huấn luyện thêm
    csv_candidates = []
    if (REPO_ROOT / "runs").exists():
        csv_candidates.extend(sorted((REPO_ROOT / "runs").rglob("results.csv"), key=lambda p: p.stat().st_mtime, reverse=True))
    if (EVAL_DIR / "results.csv").exists():
        csv_candidates.append(EVAL_DIR / "results.csv")

    val_metrics = {
        "num_images": 533,
        "precision": 78.7,
        "recall": 79.3,
        "map50": 82.0,
        "map50_95": 58.0,
        "box_loss": 1.097,
        "cls_loss": 2.276
    }
    training_epochs = 30
    training_time_sec = 463.2

    if csv_candidates and csv_candidates[0].exists():
        try:
            with open(csv_candidates[0], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    last_row = rows[-1]
                    clean_row = {k.strip(): v.strip() for k, v in last_row.items()}
                    if "epoch" in clean_row:
                        training_epochs = int(float(clean_row["epoch"]))
                    if "time" in clean_row:
                        training_time_sec = round(float(clean_row["time"]), 1)
                    if "metrics/precision(B)" in clean_row:
                        val_metrics["precision"] = round(float(clean_row["metrics/precision(B)"]) * 100, 1)
                    if "metrics/recall(B)" in clean_row:
                        val_metrics["recall"] = round(float(clean_row["metrics/recall(B)"]) * 100, 1)
                    if "metrics/mAP50(B)" in clean_row:
                        val_metrics["map50"] = round(float(clean_row["metrics/mAP50(B)"]) * 100, 1)
                    if "metrics/mAP50-95(B)" in clean_row:
                        val_metrics["map50_95"] = round(float(clean_row["metrics/mAP50-95(B)"]) * 100, 1)
                    if "val/box_loss" in clean_row:
                        val_metrics["box_loss"] = round(float(clean_row["val/box_loss"]), 3)
                    if "val/cls_loss" in clean_row:
                        val_metrics["cls_loss"] = round(float(clean_row["val/cls_loss"]), 3)
        except Exception as e:
            logger.warning(f"Lỗi đọc results.csv: {e}")

    return {
        "model_architecture": "YOLO26 Nano (End-to-end NMS-free)",
        "parameters": "2,504,580 (5.9 GFLOPs)",
        "weight_size_mb": 5.45,
        "training_epochs": training_epochs,
        "training_time_sec": training_time_sec,
        "validation_metrics": val_metrics,
        "test_metrics": {
            "num_images": 441,
            "num_boxes": 1032,
            "confusion_matrix_threshold": 0.25,
            "confusion_matrix_defect_misclassified_pct": 41.0,
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
                    "map50_95": 71.7,
                    "note": "Recall 85.4% tính theo đường cong PR (IoU=0.5). Ở ngưỡng cắt cố định của ma trận nhầm lẫn (conf=0.25), ~41% mẫu defect bị gán sang pass hoặc bỏ sót."
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
            "title": "Lưu ý phương pháp luận — Diễn giải chỉ số & Rủi ro cận trùng (Near-Duplicate Leakage)",
            "message": "Qua kiểm tra đối sánh hàm băm tri giác (pHash/SSIM), ghi nhận khoảng 53–54 cặp ảnh cận trùng giữa train và test (41 ảnh test có bản sao rất gần trong train, trong đó có 23/36 ảnh test chứa defect). Ngoài ra, toàn bộ tập test chỉ có 41 box defect và tại ngưỡng conf=0.25 của Confusion Matrix có khoảng 41% mẫu defect bị phân loại nhầm. Do đó, mAP 82.5% hiện tại là ngưỡng kỳ vọng tối đa (upper bound) chứ chưa phải bằng chứng tổng quát hóa độc lập ngoài thực địa. Bắt buộc phải chia lại dữ liệu theo video clip / phiên quay độc lập (session-based split) trước khi nghiệm thu.",
            "pairs_detected": "53 - 54 cặp",
            "affected_defect_test_images": "23 / 36 ảnh (63.9%)",
            "test_defect_boxes": 41,
            "recommendation": "Phân chia tập test theo session sản xuất độc lập và thực hiện ablation study có đối chứng"
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
                "title": "Ma trận nhầm lẫn Test (Normalized Confusion Matrix, conf=0.25)",
                "image_url": "/doc/evaluation/test_confusion_matrix_normalized.png",
                "description": "Ma trận chuẩn hóa tại ngưỡng conf=0.25 (khoảng 41% cột defect bị phân loại sang pass ở điểm cắt này)."
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
_dataset_cache: Dict[str, Any] = {}


@app.get("/api/dataset_info")
async def get_dataset_info():
    """Đếm động số lượng ảnh và bounding boxes thực tế từng lớp từ data/labels/."""
    now = time.time()
    if _dataset_cache and (now - _dataset_cache.get("timestamp", 0)) < 60:
        return _dataset_cache["data"]

    train_dir = REPO_ROOT / "data" / "images" / "train"
    val_dir = REPO_ROOT / "data" / "images" / "val"
    test_dir = REPO_ROOT / "data" / "images" / "test"

    train_c = len(list(train_dir.glob("*.jpg"))) if train_dir.exists() else 1692
    val_c = len(list(val_dir.glob("*.jpg"))) if val_dir.exists() else 533
    test_c = len(list(test_dir.glob("*.jpg"))) if test_dir.exists() else 441
    total_imgs = train_c + val_c + test_c

    # Đếm số lượng bounding boxes thực tế từng lớp từ thư mục data/labels
    box_counts = {0: 0, 1: 0}
    labels_dir = REPO_ROOT / "data" / "labels"
    if labels_dir.exists():
        for split in ["train", "val", "test"]:
            sp = labels_dir / split
            if sp.exists():
                for txt in sp.glob("*.txt"):
                    try:
                        with open(txt, "r", encoding="utf-8") as f:
                            for line in f:
                                parts = line.strip().split()
                                if parts:
                                    cid = int(parts[0])
                                    box_counts[cid] = box_counts.get(cid, 0) + 1
                    except Exception:
                        pass

    total_boxes = sum(box_counts.values()) or 5620
    pass_boxes = box_counts.get(0, 5096)
    defect_boxes = box_counts.get(1, 524)

    pass_pct = round(pass_boxes / total_boxes * 100, 1) if total_boxes > 0 else 90.7
    defect_pct = round(defect_boxes / total_boxes * 100, 1) if total_boxes > 0 else 9.3

    data = {
        "dataset_name": "ConveyorVision Industrial Bottles",
        "total_images": total_imgs,
        "total_boxes": total_boxes,
        "splits": {
            "train": {"count": train_c, "pct": round(train_c / total_imgs * 100, 1)},
            "val": {"count": val_c, "pct": round(val_c / total_imgs * 100, 1)},
            "test": {"count": test_c, "pct": round(test_c / total_imgs * 100, 1)}
        },
        "classes": [
            {
                "id": 0,
                "name": "pass (Đạt chuẩn)",
                "boxes": pass_boxes,
                "ratio_pct": pass_pct,
                "description": "Chai đủ thể tích, nhãn thẳng, nắp đậy khít"
            },
            {
                "id": 1,
                "name": "defect (Khuyết tật/Lỗi)",
                "boxes": defect_boxes,
                "ratio_pct": defect_pct,
                "description": "Thiếu nắp, nắp vênh, xước nhãn, nứt vỡ hoặc thiếu thể tích"
            }
        ],
        "image_resolution": "640x640 (RGB)",
        "source_format": "YOLOv8/YOLO26 PyTorch Format"
    }
    _dataset_cache["timestamp"] = now
    _dataset_cache["data"] = data
    return data


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

    models_list.sort(key=lambda m: (not m["is_active"], m["name"]))
    return models_list
