"""Background Inspection Worker cho ConveyorVision.

Chịu trách nhiệm:
- Chạy vòng lặp nhận diện & tracking trên background thread với độ trễ siêu thấp (Low Latency).
- Hỗ trợ 2 chế độ kiểm định:
    1. "bottle_and_other": Nhận diện & phân loại riêng Chai lọ (Bottle) và Vật thể khác / Dị vật (Other/Foreign objects).
    2. "bottle_inspection": Kiểm định chất lượng chai chuyên sâu (PASS vs DEFECT) theo tiêu chuẩn công nghiệp.
- Cơ chế đồng bộ khung hình theo điều kiện (Condition Variable) chống nghẽn bộ đệm và triệt tiêu độ trễ MJPEG.
- Tự động đồng bộ tốc độ phát video theo thời gian thực (Frame Pacing), chống lag chậm hình khi nạp file video.
- Cơ chế Multi-frame Voting & Lifecycle tracking ổn định nhãn.
"""

import csv
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from conveyorvision.inference_conveyor import resolve_track_buffer
from conveyorvision.web.session_manager import session_manager

logger = logging.getLogger("conveyorvision.worker")

# Bảng dịch nhãn COCO sang tiếng Việt thân thiện
VIETNAMESE_OBJECT_NAMES: Dict[str, str] = {
    "bottle": "Chai lọ",
    "cup": "Cốc / Ly",
    "can": "Lon kim loại",
    "bowl": "Bát / Tô",
    "wine glass": "Ly thủy tinh",
    "fork": "Nĩa",
    "knife": "Dao",
    "spoon": "Thìa",
    "banana": "Chuối",
    "apple": "Táo",
    "orange": "Cam",
    "cell phone": "Điện thoại",
    "remote": "Điều khiển",
    "mouse": "Chuột máy tính",
    "keyboard": "Bàn phím",
    "book": "Sách / Hộp",
    "scissors": "Kéo",
    "teddy bear": "Gấu bông",
    "toothbrush": "Bàn chải",
    "person": "Người / Tay",
    "backpack": "Balo / Túi",
    "handbag": "Túi xách",
    "suitcase": "Vali / Thùng",
    "clock": "Đồng hồ",
    "box": "Hộp / Thùng",
}


class InspectionWorker:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        # Đồng bộ luồng MJPEG không độ trễ
        self._frame_cond = threading.Condition()
        self._frame_seq = 0

        # Trạng thái vận hành
        self.state = "STOPPED"  # STOPPED, RUNNING, PAUSED, ERROR
        self.error_message = ""
        self.source = ""
        self.model_path = ""
        self.actual_model_name = ""
        self.inspection_mode = "bottle_and_other"  # "bottle_and_other" hoặc "bottle_inspection"
        self.tracker_config = "bytetrack.yaml"
        self.conf_thresh = 0.45
        self.inference_imgsz = 480  # Mặc định 480 để đạt 20-25 FPS trên CPU
        self.loop_video = True
        self.lost_track_buffer = 30
        self.min_observation_votes = 3
        self.auto_save_csv = True
        self.current_session_id = ""

        # Dữ liệu thời gian thực
        self.fps = 0.0
        self.inference_time_ms = 0.0
        self.total_pass = 0
        self.total_defect = 0
        self.total_other = 0  # Vật thể khác / dị vật
        self.inspecting_count = 0
        self.total_items = 0
        self.defect_rate = 0.0
        self.alert_active = False
        self.alert_message = ""
        self.alert_frames = 0
        self.frame_idx = 0
        self.start_timestamp = 0.0
        self.elapsed_sec = 0.0

        # Lịch sử tracking trong phiên
        self.track_history: Dict[int, Dict[str, Any]] = {}
        self.recent_events: List[Dict[str, Any]] = []

        # Buffer khung hình MJPEG
        self.latest_jpeg: Optional[bytes] = None
        self._generate_idle_frame("HỆ THỐNG SẴN SÀNG", "Nhấn 'Bắt đầu kiểm định' để khởi chạy camera/video")

        # Callback phát tán sự kiện (tới WebSocket manager)
        self.event_subscribers: List[Callable[[str, Dict[str, Any]], None]] = []

    def subscribe_events(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        if callback not in self.event_subscribers:
            self.event_subscribers.append(callback)

    def unsubscribe_events(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        if callback in self.event_subscribers:
            self.event_subscribers.remove(callback)

    def _broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        for cb in list(self.event_subscribers):
            try:
                cb(event_type, data)
            except Exception as e:
                logger.warning(f"Lỗi khi gửi sự kiện WebSocket {event_type}: {e}")

    def _generate_idle_frame(self, title: str, subtitle: str, is_error: bool = False) -> None:
        """Tạo khung hình tĩnh khi dừng kiểm định hoặc có lỗi."""
        h, w = 480, 640
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (15, 23, 42)  # Dark navy slate #0f172a

        # Vẽ lưới kỹ thuật mờ
        for x in range(0, w, 40):
            cv2.line(img, (x, 0), (x, h), (30, 41, 59), 1)
        for y in range(0, h, 40):
            cv2.line(img, (0, y), (w, y), (30, 41, 59), 1)

        border_color = (68, 68, 239) if is_error else (51, 65, 85)
        accent_color = (68, 68, 239) if is_error else (2, 132, 199)

        # Viền trạm
        cv2.rectangle(img, (20, 20), (w - 20, h - 20), border_color, 2)
        cv2.circle(img, (w // 2, h // 2 - 40), 45, (30, 41, 59), -1)
        cv2.circle(img, (w // 2, h // 2 - 40), 45, accent_color, 2)

        icon_text = "ERR" if is_error else "LIVE"
        cv2.putText(img, icon_text, (w // 2 - 25, h // 2 - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, accent_color, 2)

        # Tiêu đề
        cv2.putText(img, title, (w // 2 - int(len(title) * 7.5), h // 2 + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        sub = subtitle if len(subtitle) < 60 else (subtitle[:57] + "...")
        cv2.putText(img, sub, (w // 2 - int(len(sub) * 4.6), h // 2 + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (148, 163, 184), 1)

        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with self._frame_cond:
            self.latest_jpeg = buf.tobytes()
            self._frame_seq += 1
            self._frame_cond.notify_all()

    def _resolve_model_file(self, requested_path: str, mode: str) -> Optional[Path]:
        """Xác định model phù hợp với chế độ kiểm tra được chọn."""
        if mode == "bottle_and_other":
            candidates = [
                Path("yolo26n.pt").resolve(),
                Path("yolov8n.pt").resolve(),
                Path("models/yolov8n_pilot_best.pt").resolve(),
                Path("models/conveyor_yolo26_30ep_best.pt").resolve(),
            ]
            for c in candidates:
                if c.exists() and c.is_file():
                    return c

        req = Path(requested_path)
        if req.is_absolute() and req.exists() and req.is_file():
            return req
        if req.exists() and req.is_file():
            return req.resolve()

        direct_cand = Path("models") / req.name
        if direct_cand.exists() and direct_cand.is_file():
            return direct_cand.resolve()

        candidate_fallbacks = [
            Path("models/conveyor_yolo26_30ep_best.pt").resolve(),
            Path("models/yolov8n_pilot_best.pt").resolve(),
            Path("yolo26n.pt").resolve(),
            Path("yolov8n.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
        ]
        if Path("runs").exists():
            candidate_fallbacks.extend(sorted(Path("runs").rglob("best.pt"), key=lambda p: p.stat().st_mtime, reverse=True))

        for p in candidate_fallbacks:
            if p.exists() and p.is_file():
                return p
        return None

    def start(
        self,
        source: str = "raw_videos/conveyor_demo.mp4",
        model_path: str = "models/conveyor_yolo26_30ep_best.pt",
        inspection_mode: str = "bottle_and_other",
        conf_thresh: float = 0.45,
        tracker_config: str = "bytetrack.yaml",
        imgsz: int = 480,
        loop_video: bool = True,
        lost_track_buffer: Optional[int] = None,
        min_observation_votes: Optional[int] = None,
        auto_save_csv: Optional[bool] = None
    ) -> Dict[str, Any]:
        with self._lock:
            if self.state in ("RUNNING", "PAUSED"):
                return {"success": False, "message": "Kiểm định đang chạy hoặc đang tạm dừng."}

            sys_settings = session_manager.get_settings()
            self.lost_track_buffer = int(lost_track_buffer) if lost_track_buffer is not None else sys_settings.get("lost_track_buffer", 30)
            self.min_observation_votes = int(min_observation_votes) if min_observation_votes is not None else sys_settings.get("min_observation_votes", 3)
            self.auto_save_csv = bool(auto_save_csv) if auto_save_csv is not None else sys_settings.get("auto_save_csv", True)

            self.source = str(source).strip()
            self.inspection_mode = inspection_mode
            self.conf_thresh = float(conf_thresh)
            self.tracker_config = tracker_config
            self.inference_imgsz = int(imgsz)
            self.loop_video = loop_video
            self.error_message = ""

            resolved_model = self._resolve_model_file(model_path, inspection_mode)
            if not resolved_model:
                err_msg = f"Không tìm thấy file trọng số phù hợp: {model_path}"
                logger.error(err_msg)
                self.state = "ERROR"
                self.error_message = err_msg
                self._generate_idle_frame("LỖI CHECKPOINT", err_msg, is_error=True)
                self._broadcast("status_changed", self.get_status())
                return {"success": False, "message": err_msg}

            self.model_path = str(resolved_model)
            self.actual_model_name = resolved_model.name

            # Reset thống kê
            self.total_pass = 0
            self.total_defect = 0
            self.total_other = 0
            self.inspecting_count = 0
            self.total_items = 0
            self.defect_rate = 0.0
            self.alert_active = False
            self.alert_message = ""
            self.alert_frames = 0
            self.frame_idx = 0
            self.start_timestamp = time.time()
            self.elapsed_sec = 0.0
            self.fps = 0.0
            self.inference_time_ms = 0.0
            self.track_history.clear()
            self.recent_events.clear()

            session = session_manager.create_session(
                source=self.source,
                model_name=self.actual_model_name,
                tracker=tracker_config,
                conf_thresh=self.conf_thresh
            )
            self.current_session_id = session["session_id"]

            self._stop_event.clear()
            self._pause_event.clear()
            self.state = "RUNNING"

            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            # Bắn sự kiện RUNNING ngay lập tức để mở khóa nút trên giao diện
            self._broadcast("status_changed", self.get_status())

            logger.info(f"Đã khởi chạy kiểm định: {self.current_session_id} | Chế độ: {self.inspection_mode} | Nguồn: {self.source}")
            return {
                "success": True,
                "session_id": self.current_session_id,
                "model": self.actual_model_name,
                "mode": self.inspection_mode
            }

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            if self.state != "RUNNING":
                return {"success": False, "message": "Hệ thống không trong trạng thái đang chạy."}
            self.state = "PAUSED"
            self._pause_event.set()
            self._broadcast("status_changed", self.get_status())
            return {"success": True, "state": "PAUSED"}

    def resume(self) -> Dict[str, Any]:
        with self._lock:
            if self.state != "PAUSED":
                return {"success": False, "message": "Hệ thống không trong trạng thái tạm dừng."}
            self.state = "RUNNING"
            self._pause_event.clear()
            self._broadcast("status_changed", self.get_status())
            return {"success": True, "state": "RUNNING"}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if self.state == "STOPPED":
                return {"success": False, "message": "Hệ thống đã dừng từ trước."}

            self.state = "STOPPED"
            self._stop_event.set()
            self._pause_event.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.5)

        self._generate_idle_frame("PHIÊN KIỂM ĐỊNH KẾT THÚC", f"Đã hoàn thành phiên: {self.current_session_id}")
        self._broadcast("status_changed", self.get_status())
        return {"success": True, "session_id": self.current_session_id}

    def capture_snapshot(self) -> Optional[str]:
        if not self.latest_jpeg:
            return None
        out_dir = Path("reports/snapshots").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = out_dir / filename
        with open(filepath, "wb") as f:
            f.write(self.latest_jpeg)
        return str(filepath)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self.state,
                "error_message": self.error_message,
                "session_id": self.current_session_id,
                "source": self.source,
                "mode": self.inspection_mode,
                "model": self.actual_model_name or (Path(self.model_path).name if self.model_path else "YOLO26n"),
                "tracker": self.tracker_config,
                "conf_thresh": self.conf_thresh,
                "fps": round(self.fps, 1),
                "inference_ms": round(self.inference_time_ms, 1),
                "total_pass": self.total_pass,
                "total_defect": self.total_defect,
                "total_other": self.total_other,
                "inspecting_count": self.inspecting_count,
                "total_items": self.total_items,
                "defect_rate": round(self.defect_rate, 1),
                "alert_active": self.alert_active,
                "alert_message": self.alert_message,
                "frame_idx": self.frame_idx,
                "elapsed_sec": round(time.time() - self.start_timestamp, 1) if self.state in ("RUNNING", "PAUSED") else round(self.elapsed_sec, 1)
            }

    def _handle_error(self, title: str, error_msg: str) -> None:
        logger.error(f"{title}: {error_msg}")
        self.state = "ERROR"
        self.error_message = error_msg
        if self.current_session_id:
            session_manager.fail_session(self.current_session_id, error_msg)
        self._generate_idle_frame(title, error_msg, is_error=True)
        self._broadcast("status_changed", self.get_status())

    def _run_loop(self) -> None:
        try:
            from ultralytics import YOLO
        except ImportError:
            self._handle_error("LỖI HỆ THỐNG", "Chưa cài đặt thư viện Ultralytics.")
            return

        model_file = self._resolve_model_file(self.model_path, self.inspection_mode)
        if not model_file:
            self._handle_error("LỖI CHECKPOINT", f"Không tìm thấy file weights YOLO: {self.model_path}")
            return

        try:
            model = YOLO(str(model_file))
        except Exception as e:
            self._handle_error("LỖI NẠP MODEL", str(e))
            return

        is_webcam = self.source.isdigit()
        cap_source = int(self.source) if is_webcam else self.source

        if not is_webcam and not Path(cap_source).exists():
            demo_cand = Path("raw_videos/conveyor_demo.mp4")
            if demo_cand.exists():
                cap_source = str(demo_cand)
                self.source = str(demo_cand)
            else:
                self._handle_error("LỖI NGUỒN VIDEO", f"Không tìm thấy video: {cap_source}")
                return

        cap = cv2.VideoCapture(cap_source)
        if not cap.isOpened():
            self._handle_error("LỖI KẾT NỐI", f"Không thể mở nguồn video {cap_source}")
            return

        # Tối ưu độ trễ cho Webcam: Buffer size = 1 để luôn lấy khung hình mới nhất
        if is_webcam:
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if video_fps <= 0 or video_fps > 120:
            video_fps = 25.0

        track_buffer = self.lost_track_buffer or resolve_track_buffer(self.tracker_config)
        min_votes = self.min_observation_votes

        csv_file = None
        csv_writer = None
        if self.auto_save_csv:
            csv_path = session_manager.get_session_csv_path(self.current_session_id)
            if csv_path:
                try:
                    csv_file = open(csv_path, "a", newline="", encoding="utf-8")
                    csv_writer = csv.writer(csv_file)
                except Exception as e:
                    logger.warning(f"Không thể mở file CSV: {e}")

        # Đồng bộ thời gian thực cho video file (chống trôi chậm hình ảnh)
        last_frame_wall_time = time.time()
        fps_history = []
        is_coco_model = (len(model.names) >= 80) or ("bottle" in model.names.values())

        try:
            while not self._stop_event.is_set():
                if self._pause_event.is_set():
                    time.sleep(0.08)
                    continue

                # Frame pacing cho video file: Đọc đồng bộ theo thời gian thực
                if not is_webcam:
                    now = time.time()
                    elapsed = now - last_frame_wall_time
                    target_interval = 1.0 / video_fps
                    if elapsed < target_interval:
                        time.sleep(max(0.001, target_interval - elapsed))
                    last_frame_wall_time = time.time()

                ret, frame = cap.read()
                if not ret:
                    if not is_webcam and self.loop_video and not self._stop_event.is_set():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret:
                            break
                    else:
                        break

                self.frame_idx += 1
                t_start = time.time()
                curr_ts = self.frame_idx / video_fps

                # Tối ưu kích thước đầu vào (imgsz) để triệt tiêu độ trễ
                # Chạy inference kèm tracking ByteTrack
                results = model.track(
                    frame,
                    persist=True,
                    tracker=self.tracker_config,
                    conf=self.conf_thresh,
                    imgsz=self.inference_imgsz,
                    verbose=False
                )
                t_end = time.time()
                self.inference_time_ms = (t_end - t_start) * 1000.0

                # Tính FPS thực tế
                curr_fps = 1.0 / max(1e-4, (t_end - t_start))
                fps_history.append(curr_fps)
                if len(fps_history) > 20:
                    fps_history.pop(0)
                self.fps = sum(fps_history) / len(fps_history)

                has_defect_in_frame = False
                has_other_in_frame = False
                other_names_in_frame = []

                if results and len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        track_id = int(box.id[0].item()) if box.id is not None else -1

                        raw_name = model.names.get(cls_id, str(cls_id)).lower()

                        # Logic phân loại theo Chế độ kiểm định (Inspection Mode)
                        if self.inspection_mode == "bottle_and_other" or is_coco_model:
                            # Phân định Chai lọ vs Vật thể khác
                            if raw_name == "bottle" or cls_id == 39 or raw_name == "pass":
                                item_category = "BOTTLE"
                                display_name = "Chai lọ"
                                color = (0, 220, 0)  # Xanh lá
                            elif raw_name == "defect":
                                item_category = "BOTTLE_DEFECT"
                                display_name = "Chai lỗi"
                                color = (0, 0, 255)  # Đỏ
                                has_defect_in_frame = True
                            else:
                                item_category = "OTHER"
                                vi_name = VIETNAMESE_OBJECT_NAMES.get(raw_name, raw_name)
                                display_name = f"Vật thể khác: {vi_name}"
                                color = (220, 0, 180)  # Tím hồng nổi bật (Dị vật)
                                has_other_in_frame = True
                                other_names_in_frame.append(vi_name)
                        else:
                            # Chế độ kiểm định Chai chuyên sâu (Pass / Defect)
                            if cls_id == 1 or raw_name == "defect":
                                item_category = "BOTTLE_DEFECT"
                                display_name = "DEFECT (Chai lỗi)"
                                color = (0, 0, 255)  # Đỏ
                                has_defect_in_frame = True
                            else:
                                item_category = "BOTTLE_PASS"
                                display_name = "PASS (Đạt chuẩn)"
                                color = (0, 255, 0)  # Xanh lá

                        # Cập nhật vòng đời Tracking (Multi-frame Tracking Lifecycle)
                        if track_id != -1:
                            if track_id not in self.track_history:
                                self.track_history[track_id] = {
                                    "track_id": track_id,
                                    "category": item_category,
                                    "display_name": display_name,
                                    "pass_votes": 0,
                                    "defect_votes": 0,
                                    "other_votes": 0,
                                    "max_conf": conf,
                                    "state": "INSPECTING",
                                    "first_ts": curr_ts,
                                    "last_seen_ts": curr_ts,
                                    "last_seen_frame": self.frame_idx,
                                    "logged": False,
                                    "logged_status": "NONE",
                                    "was_corrected": False
                                }
                                # Phát sự kiện phát hiện vật thể mới vào góc quét
                                self._broadcast("track_event", {
                                    "event": "NEW_ITEM",
                                    "track_id": track_id,
                                    "category": item_category,
                                    "status": "INSPECTING",
                                    "class_name": display_name,
                                    "conf": conf,
                                    "timestamp": f"{curr_ts:.2f}s",
                                    "message": f"Phát hiện #{track_id}: {display_name}"
                                })

                            th = self.track_history[track_id]
                            th["last_seen_frame"] = self.frame_idx
                            th["last_seen_ts"] = curr_ts
                            th["display_name"] = display_name
                            if conf > th["max_conf"]:
                                th["max_conf"] = conf

                            if item_category == "OTHER":
                                th["other_votes"] += 1
                                th["category"] = "OTHER"
                                if th["other_votes"] >= 2 and th["state"] != "OTHER":
                                    th["state"] = "OTHER"
                                    if not th["logged"]:
                                        th["logged"] = True
                                        th["logged_status"] = "OTHER"
                                        if csv_writer:
                                            csv_writer.writerow([f"{curr_ts:.2f}", track_id, cls_id, display_name, f"{conf:.2f}", "OTHER"])
                                            csv_file.flush()
                                        self._broadcast("track_event", {
                                            "event": "OTHER_CONFIRMED",
                                            "track_id": track_id,
                                            "status": "OTHER",
                                            "class_name": display_name,
                                            "conf": conf,
                                            "timestamp": f"{curr_ts:.2f}s",
                                            "message": f"Dị vật #{track_id}: {display_name}"
                                        })

                            elif item_category == "BOTTLE_DEFECT":
                                th["defect_votes"] += 1
                                if th["defect_votes"] >= 2 or conf >= 0.5:
                                    if th["state"] != "DEFECT":
                                        was_pass = (th.get("logged_status") == "PASS")
                                        th["state"] = "DEFECT"
                                        th["category"] = "BOTTLE_DEFECT"
                                        th["logged"] = True
                                        th["logged_status"] = "DEFECT"
                                        th["was_corrected"] = was_pass

                                        if csv_writer:
                                            tag = "DEFECT_CORRECTION" if was_pass else "DEFECT"
                                            csv_writer.writerow([f"{curr_ts:.2f}", track_id, 1, "Chai lỗi", f"{conf:.2f}", tag])
                                            csv_file.flush()

                                        self._broadcast("track_event", {
                                            "event": "DEFECT_CORRECTION" if was_pass else "DEFECT_CONFIRMED",
                                            "track_id": track_id,
                                            "status": "DEFECT",
                                            "class_name": "Chai lỗi (Defect)",
                                            "conf": conf,
                                            "timestamp": f"{curr_ts:.2f}s",
                                            "is_update": was_pass,
                                            "message": f"Chai #{track_id}: PHÁT HIỆN LỖI ({conf:.2f})"
                                        })
                            else:
                                th["pass_votes"] += 1

                        # Vẽ Bounding Box & Tag nhãn trực quan
                        label = f"{display_name} #{track_id} {conf:.2f}" if track_id != -1 else f"{display_name} {conf:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
                        cv2.rectangle(frame, (x1, max(0, y1 - 22)), (x1 + lw + 6, max(22, y1)), color, -1)
                        cv2.putText(frame, label, (x1 + 3, max(16, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2)

                # Chốt trạng thái cho các vật thể đã đi qua khỏi tầm nhìn (lost >= track_buffer frames)
                for tid, th in self.track_history.items():
                    if not th["logged"] and th["state"] == "INSPECTING":
                        if (self.frame_idx - th["last_seen_frame"]) >= track_buffer:
                            total_obs = th["pass_votes"] + th["defect_votes"] + th["other_votes"]
                            if th["other_votes"] >= 2:
                                th["state"] = "OTHER"
                                th["logged"] = True
                                if csv_writer:
                                    csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 2, th["display_name"], f"{th['max_conf']:.2f}", "OTHER"])
                            elif total_obs >= min_votes:
                                th["state"] = "PASS"
                                th["logged"] = True
                                if csv_writer:
                                    csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 0, "Chai đạt chuẩn", f"{th['max_conf']:.2f}", "PASS"])
                                    csv_file.flush()

                                self._broadcast("track_event", {
                                    "event": "PASS_FINALIZED",
                                    "track_id": tid,
                                    "status": "PASS",
                                    "class_name": "Chai đạt chuẩn",
                                    "conf": th["max_conf"],
                                    "timestamp": f"{th['last_seen_ts']:.2f}s",
                                    "message": f"Chai #{tid}: XÁC NHẬN ĐẠT CHUẨN"
                                })
                            else:
                                th["state"] = "INVALID"

                # Quản lý Cảnh báo (Defect hoặc Dị vật lạ)
                if has_defect_in_frame:
                    self.alert_frames = 15
                    self.alert_active = True
                    self.alert_message = "PHÁT HIỆN CHAI LỖI (DEFECT) — KÍCH HOẠT CƠ CHẾ GẠT"
                elif has_other_in_frame:
                    self.alert_frames = 15
                    self.alert_active = True
                    other_str = ", ".join(set(other_names_in_frame)) if other_names_in_frame else "Vật thể khác"
                    self.alert_message = f"CẢNH BÁO DỊ VẬT / VẬT THỂ LẠ TRÊN BĂNG TẢI: {other_str.upper()}"
                elif self.alert_frames > 0:
                    self.alert_frames -= 1
                    self.alert_active = True
                else:
                    self.alert_active = False
                    self.alert_message = ""

                # Thống kê số lượng theo nhóm
                self.total_pass = sum(1 for th in self.track_history.values() if th["state"] == "PASS")
                self.total_defect = sum(1 for th in self.track_history.values() if th["state"] == "DEFECT")
                self.total_other = sum(1 for th in self.track_history.values() if th["state"] == "OTHER")
                self.inspecting_count = sum(1 for th in self.track_history.values() if th["state"] == "INSPECTING" and (self.frame_idx - th["last_seen_frame"]) < track_buffer)
                self.total_items = self.total_pass + self.total_defect + self.total_other
                total_bottles = self.total_pass + self.total_defect
                self.defect_rate = (self.total_defect / total_bottles * 100) if total_bottles > 0 else 0.0

                # Vẽ HUD & Rejection/Other Banner
                overlay = frame.copy()
                hud_h = 160 if self.inspection_mode == "bottle_and_other" else 135
                cv2.rectangle(overlay, (10, 10), (330, hud_h), (15, 23, 42), -1)
                cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
                cv2.rectangle(frame, (10, 10), (330, hud_h), (51, 65, 85), 1)

                cv2.putText(frame, f"FPS: {self.fps:.1f} ({self.inference_time_ms:.1f}ms)", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)
                cv2.putText(frame, f"DANG QUET (ON BELT): {self.inspecting_count}", (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 215, 255), 2)
                cv2.putText(frame, f"CHAI PASS          : {self.total_pass}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 0), 2)
                cv2.putText(frame, f"CHAI DEFECT (LOI)  : {self.total_defect}", (20, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 255), 2)
                if self.inspection_mode == "bottle_and_other":
                    cv2.putText(frame, f"VAT THE KHAC (DI VAT): {self.total_other}", (20, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 0, 220), 2)
                    cv2.putText(frame, f"TY LE LOI CHAI     : {self.defect_rate:.1f}%", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)
                else:
                    cv2.putText(frame, f"TY LE LOI          : {self.defect_rate:.1f}%", (20, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)

                if self.alert_active:
                    banner_color = (0, 0, 220) if "DEFECT" in self.alert_message else (180, 0, 180)
                    cv2.rectangle(frame, (0, 0), (width, 42), banner_color, -1)
                    banner_txt = f">>> {self.alert_message} <<<"
                    cv2.putText(frame, banner_txt, (max(10, int(width / 2) - int(len(banner_txt) * 5.2)), 28),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)

                # Nén JPEG chất lượng 72 để giảm 50% băng thông mạng và triệt tiêu độ trễ
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
                with self._frame_cond:
                    self.latest_jpeg = buf.tobytes()
                    self._frame_seq += 1
                    self._frame_cond.notify_all()

                # Bắn cập nhật chỉ số qua WebSocket
                if self.frame_idx % 4 == 0:
                    self._broadcast("stats_update", {
                        "fps": round(self.fps, 1),
                        "inference_ms": round(self.inference_time_ms, 1),
                        "total_pass": self.total_pass,
                        "total_defect": self.total_defect,
                        "total_other": self.total_other,
                        "inspecting_count": self.inspecting_count,
                        "total_items": self.total_items,
                        "defect_rate": round(self.defect_rate, 1),
                        "alert_active": self.alert_active,
                        "alert_message": self.alert_message,
                        "frame_idx": self.frame_idx
                    })

        except Exception as e:
            self._handle_error("LỖI XỬ LÝ KHUNG HÌNH", str(e))
            return
        finally:
            cap.release()
            if csv_file:
                try:
                    csv_file.flush()
                    csv_file.close()
                except Exception:
                    pass

            if self.state != "ERROR":
                for tid, th in self.track_history.items():
                    if not th["logged"]:
                        total_obs = th["pass_votes"] + th["defect_votes"] + th["other_votes"]
                        if th["other_votes"] >= 2:
                            th["state"] = "OTHER"
                            th["logged"] = True
                            if csv_writer:
                                csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 2, th["display_name"], f"{th['max_conf']:.2f}", "OTHER"])
                        elif th["defect_votes"] >= 2 or (th["defect_votes"] >= 1 and th["category"] == "BOTTLE_DEFECT"):
                            th["state"] = "DEFECT"
                            th["logged"] = True
                            if csv_writer:
                                csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 1, "Chai lỗi", f"{th['max_conf']:.2f}", "DEFECT"])
                        elif total_obs >= min_votes:
                            th["state"] = "PASS"
                            th["logged"] = True
                            if csv_writer:
                                csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 0, "Chai đạt chuẩn", f"{th['max_conf']:.2f}", "PASS"])
                        else:
                            th["state"] = "INVALID"

                self.total_pass = sum(1 for th in self.track_history.values() if th["state"] == "PASS")
                self.total_defect = sum(1 for th in self.track_history.values() if th["state"] == "DEFECT")
                self.total_other = sum(1 for th in self.track_history.values() if th["state"] == "OTHER")
                self.elapsed_sec = time.time() - self.start_timestamp

                tracks_summary = [
                    {
                        "track_id": th["track_id"],
                        "state": th["state"],
                        "class_name": th.get("display_name", th["state"]),
                        "max_conf": round(th["max_conf"], 2),
                        "first_ts": round(th["first_ts"], 2),
                        "last_ts": round(th["last_seen_ts"], 2),
                        "obs_votes": th["pass_votes"] + th["defect_votes"] + th["other_votes"],
                        "was_corrected": th.get("was_corrected", False)
                    }
                    for th in self.track_history.values()
                    if th["state"] in ("PASS", "DEFECT", "OTHER")
                ]

                session_manager.finalize_session(
                    session_id=self.current_session_id,
                    total_pass=self.total_pass,
                    total_defect=self.total_defect,
                    avg_fps=self.fps,
                    duration_sec=self.elapsed_sec,
                    tracks=tracks_summary
                )

                self.state = "STOPPED"
                self._broadcast("session_finished", {
                    "session_id": self.current_session_id,
                    "total_pass": self.total_pass,
                    "total_defect": self.total_defect,
                    "total_other": self.total_other,
                    "total_items": self.total_pass + self.total_defect + self.total_other,
                    "defect_rate": round(self.defect_rate, 1),
                    "duration_sec": round(self.elapsed_sec, 1)
                })
                self._broadcast("status_changed", self.get_status())
                logger.info(f"Đã hoàn thành phiên: {self.current_session_id}")


# Singleton instance
worker = InspectionWorker()
