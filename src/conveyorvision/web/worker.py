"""Background Inspection Worker cho ConveyorVision.

Chịu trách nhiệm:
- Chạy vòng lặp nhận diện & tracking trên background thread.
- Áp dụng thuật toán Multi-frame Voting & Lifecycle tracking theo tiêu chuẩn công nghiệp.
- Tạo luồng MJPEG stream cho trình duyệt qua `/api/video_feed`.
- Bắn sự kiện thời gian thực (stats, track_updated, defect_alert, session_finished) tới WebSocket.
- Không bao giờ gọi cv2.imshow(), đảm bảo tương thích hoàn hảo trên web server.
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


class InspectionWorker:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        # Trạng thái vận hành
        self.state = "STOPPED"  # STOPPED, RUNNING, PAUSED, ERROR
        self.source = ""
        self.model_path = ""
        self.tracker_config = "bytetrack.yaml"
        self.conf_thresh = 0.45
        self.current_session_id = ""

        # Dữ liệu thời gian thực
        self.fps = 0.0
        self.total_pass = 0
        self.total_defect = 0
        self.inspecting_count = 0
        self.total_items = 0
        self.defect_rate = 0.0
        self.alert_active = False
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

    def _generate_idle_frame(self, title: str, subtitle: str) -> None:
        """Tạo khung hình tĩnh khi dừng kiểm định."""
        h, w = 480, 640
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (15, 23, 42)  # Dark navy slate #0f172a

        # Vẽ lưới kỹ thuật mờ
        for x in range(0, w, 40):
            cv2.line(img, (x, 0), (x, h), (30, 41, 59), 1)
        for y in range(0, h, 40):
            cv2.line(img, (0, y), (w, y), (30, 41, 59), 1)

        # Viền trạm
        cv2.rectangle(img, (20, 20), (w - 20, h - 20), (51, 65, 85), 2)
        cv2.circle(img, (w // 2, h // 2 - 40), 45, (30, 41, 59), -1)
        cv2.circle(img, (w // 2, h // 2 - 40), 45, (2, 132, 199), 2)

        # Biểu tượng camera
        cv2.putText(img, "LIVE", (w // 2 - 25, h // 2 - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (2, 132, 199), 2)

        # Tiêu đề
        cv2.putText(img, title, (w // 2 - int(len(title) * 7.5), h // 2 + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(img, subtitle, (w // 2 - int(len(subtitle) * 4.8), h // 2 + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (148, 163, 184), 1)

        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        self.latest_jpeg = buf.tobytes()

    def start(
        self,
        source: str = "raw_videos/conveyor_demo.mp4",
        model_path: str = "models/conveyor_yolo26_30ep_best.pt",
        conf_thresh: float = 0.45,
        tracker_config: str = "bytetrack.yaml",
        loop_video: bool = True
    ) -> Dict[str, Any]:
        with self._lock:
            if self.state in ("RUNNING", "PAUSED"):
                return {"success": False, "message": "Kiểm định đang chạy hoặc đang tạm dừng."}

            self.source = str(source).strip()
            self.model_path = model_path
            self.conf_thresh = float(conf_thresh)
            self.tracker_config = tracker_config
            self.loop_video = loop_video

            # Reset các biến thống kê
            self.total_pass = 0
            self.total_defect = 0
            self.inspecting_count = 0
            self.total_items = 0
            self.defect_rate = 0.0
            self.alert_active = False
            self.alert_frames = 0
            self.frame_idx = 0
            self.start_timestamp = time.time()
            self.elapsed_sec = 0.0
            self.fps = 0.0
            self.track_history.clear()
            self.recent_events.clear()

            # Tạo session mới
            session = session_manager.create_session(
                source=self.source,
                model_name=Path(model_path).name,
                tracker=tracker_config,
                conf_thresh=self.conf_thresh
            )
            self.current_session_id = session["session_id"]

            self._stop_event.clear()
            self._pause_event.clear()
            self.state = "RUNNING"

            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            logger.info(f"Đã khởi động phiên kiểm định: {self.current_session_id} trên nguồn: {self.source}")
            return {"success": True, "session_id": self.current_session_id}

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            if self.state != "RUNNING":
                return {"success": False, "message": "Hệ thống không trong trạng thái đang chạy."}
            self.state = "PAUSED"
            self._pause_event.set()
            self._broadcast("status_changed", {"state": "PAUSED"})
            return {"success": True, "state": "PAUSED"}

    def resume(self) -> Dict[str, Any]:
        with self._lock:
            if self.state != "PAUSED":
                return {"success": False, "message": "Hệ thống không trong trạng thái tạm dừng."}
            self.state = "RUNNING"
            self._pause_event.clear()
            self._broadcast("status_changed", {"state": "RUNNING"})
            return {"success": True, "state": "RUNNING"}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if self.state == "STOPPED":
                return {"success": False, "message": "Hệ thống đã dừng từ trước."}

            self.state = "STOPPED"
            self._stop_event.set()
            self._pause_event.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        self._generate_idle_frame("PHIÊN KIỂM ĐỊNH KẾT THÚC", f"Đã hoàn thành phiên: {self.current_session_id}")
        self._broadcast("status_changed", {"state": "STOPPED"})
        return {"success": True, "session_id": self.current_session_id}

    def capture_snapshot(self) -> Optional[str]:
        """Lưu khung hình hiện tại thành file ảnh vi phạm."""
        if not self.latest_jpeg:
            return None
        out_dir = Path("reports/snapshots")
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
                "session_id": self.current_session_id,
                "source": self.source,
                "model": Path(self.model_path).name if self.model_path else "YOLO26n",
                "tracker": self.tracker_config,
                "conf_thresh": self.conf_thresh,
                "fps": round(self.fps, 1),
                "total_pass": self.total_pass,
                "total_defect": self.total_defect,
                "inspecting_count": self.inspecting_count,
                "total_items": self.total_items,
                "defect_rate": round(self.defect_rate, 1),
                "alert_active": self.alert_active,
                "frame_idx": self.frame_idx,
                "elapsed_sec": round(time.time() - self.start_timestamp, 1) if self.state in ("RUNNING", "PAUSED") else round(self.elapsed_sec, 1)
            }

    def _find_model_file(self) -> Optional[Path]:
        model_file = Path(self.model_path).resolve()
        if model_file.exists():
            return model_file

        candidate_fallbacks = [
            Path("models/conveyor_yolo26_30ep_best.pt").resolve(),
            Path("models/yolov8n_pilot_best.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
            Path("runs/detect/runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
            Path("runs/pilot/pilot_test/weights/best.pt").resolve(),
            Path("runs/pilot/pilot_run/weights/best.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/last.pt").resolve(),
            Path("weights/best.pt").resolve()
        ]
        if Path("runs").exists():
            candidate_fallbacks.extend(sorted(Path("runs").rglob("best.pt"), key=lambda p: p.stat().st_mtime, reverse=True))

        for p in candidate_fallbacks:
            if p.exists():
                return p
        return None

    def _run_loop(self) -> None:
        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error("Chưa cài đặt Ultralytics.")
            self.state = "ERROR"
            self._generate_idle_frame("LỖI HỆ THỐNG", "Chưa cài đặt thư viện Ultralytics")
            return

        model_file = self._find_model_file()
        if not model_file:
            logger.error(f"Không tìm thấy checkpoint: {self.model_path}")
            self.state = "ERROR"
            self._generate_idle_frame("LỖI CHECKPOINT", "Không tìm thấy file weights YOLO (.pt)")
            return

        try:
            model = YOLO(str(model_file))
        except Exception as e:
            logger.error(f"Lỗi khởi tạo YOLO: {e}")
            self.state = "ERROR"
            self._generate_idle_frame("LỖI NẠP MODEL", str(e))
            return

        # Mở nguồn video
        is_webcam = self.source.isdigit()
        cap_source = int(self.source) if is_webcam else self.source

        # Kiểm tra file video tồn tại nếu không phải webcam
        if not is_webcam and not Path(cap_source).exists():
            # Thử tìm file demo mặc định
            demo_cand = Path("raw_videos/conveyor_demo.mp4")
            if demo_cand.exists():
                cap_source = str(demo_cand)
                self.source = str(demo_cand)
            else:
                logger.error(f"Không tìm thấy file video: {cap_source}")
                self.state = "ERROR"
                self._generate_idle_frame("LỖI NGUỒN VIDEO", f"Không tìm thấy: {cap_source}")
                return

        cap = cv2.VideoCapture(cap_source)
        if not cap.isOpened():
            self.state = "ERROR"
            self._generate_idle_frame("LỖI KẾT NỐI", f"Không thể mở nguồn video {cap_source}")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 25.0

        track_buffer = resolve_track_buffer(self.tracker_config)
        csv_path = session_manager.get_session_csv_path(self.current_session_id)
        csv_file = open(csv_path, "a", newline="", encoding="utf-8") if csv_path else None
        csv_writer = csv.writer(csv_file) if csv_file else None

        prev_time = time.time()
        fps_history = []

        try:
            while not self._stop_event.is_set():
                # Xử lý khi tạm dừng
                if self._pause_event.is_set():
                    time.sleep(0.1)
                    continue

                ret, frame = cap.read()
                if not ret:
                    if not is_webcam and self.loop_video and not self._stop_event.is_set():
                        # Video file chạy hết -> Tự động tua lại đầu để kiểm định liên tục
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret:
                            break
                    else:
                        break

                self.frame_idx += 1
                curr_time = time.time()
                dt = curr_time - prev_time
                prev_time = curr_time
                curr_fps = 1.0 / max(1e-5, dt)
                fps_history.append(curr_fps)
                if len(fps_history) > 30:
                    fps_history.pop(0)
                self.fps = sum(fps_history) / len(fps_history)
                curr_ts = self.frame_idx / fps_in

                # Chạy tracking qua YOLO với cấu hình ByteTrack tường minh
                results = model.track(
                    frame,
                    persist=True,
                    tracker=self.tracker_config,
                    conf=self.conf_thresh,
                    verbose=False
                )

                has_defect_in_frame = False

                if results and len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        track_id = int(box.id[0].item()) if box.id is not None else -1

                        if track_id != -1:
                            is_new_track = track_id not in self.track_history
                            if is_new_track:
                                self.track_history[track_id] = {
                                    "track_id": track_id,
                                    "pass_votes": 0,
                                    "defect_votes": 0,
                                    "max_defect_conf": 0.0,
                                    "max_conf": conf,
                                    "is_defect": False,
                                    "state": "INSPECTING",
                                    "first_ts": curr_ts,
                                    "last_seen_ts": curr_ts,
                                    "last_seen_frame": self.frame_idx,
                                    "logged": False,
                                    "logged_status": "NONE",
                                    "was_corrected": False
                                }
                                # Phát sự kiện phát hiện chai mới vào băng chuyền
                                self._broadcast("track_event", {
                                    "event": "NEW_ITEM",
                                    "track_id": track_id,
                                    "status": "INSPECTING",
                                    "class_name": "Đang kiểm tra",
                                    "conf": conf,
                                    "timestamp": f"{curr_ts:.2f}s",
                                    "message": f"Chai #{track_id} vào góc quét camera"
                                })

                            th = self.track_history[track_id]
                            th["last_seen_frame"] = self.frame_idx
                            th["last_seen_ts"] = curr_ts
                            if conf > th["max_conf"]:
                                th["max_conf"] = conf

                            if cls_id == 1:
                                th["defect_votes"] += 1
                                if conf > th["max_defect_conf"]:
                                    th["max_defect_conf"] = conf
                            else:
                                th["pass_votes"] += 1

                            # Tiêu chuẩn phán quyết khuyết tật:
                            # Khóa DEFECT ngay khi phát hiện defect >= 2 frames hoặc 1 frame có conf >= max(0.5, conf_thresh)
                            if not th["is_defect"]:
                                if th["defect_votes"] >= 2 or (th["defect_votes"] >= 1 and th["max_defect_conf"] >= max(0.5, self.conf_thresh)):
                                    th["is_defect"] = True
                                    th["state"] = "DEFECT"
                                    has_defect_in_frame = True

                                    if not th["logged"]:
                                        th["logged"] = True
                                        th["logged_status"] = "DEFECT"
                                        if csv_writer:
                                            csv_writer.writerow([f"{curr_ts:.2f}", track_id, 1, "defect", f"{th['max_defect_conf']:.2f}", "DEFECT"])
                                            csv_file.flush()

                                        # Phát sự kiện xác nhận lỗi
                                        self._broadcast("track_event", {
                                            "event": "DEFECT_CONFIRMED",
                                            "track_id": track_id,
                                            "status": "DEFECT",
                                            "class_name": "defect",
                                            "conf": th["max_defect_conf"],
                                            "timestamp": f"{curr_ts:.2f}s",
                                            "message": f"Chai #{track_id} PHÁT HIỆN LỖI (Conf: {th['max_defect_conf']:.2f})"
                                        })
                                        self._broadcast("defect_alert", {
                                            "track_id": track_id,
                                            "conf": th["max_defect_conf"],
                                            "timestamp": f"{curr_ts:.2f}s"
                                        })
                                    elif th.get("logged_status") == "PASS":
                                        # Tình huống đặc biệt: Chai từng tạm chốt PASS nhưng ByteTrack nhận lại và phát hiện defect
                                        th["logged_status"] = "DEFECT"
                                        th["was_corrected"] = True
                                        if csv_writer:
                                            csv_writer.writerow([f"{curr_ts:.2f}", track_id, 1, "defect", f"{th['max_defect_conf']:.2f}", "DEFECT_CORRECTION"])
                                            csv_file.flush()

                                        # Phát sự kiện CẬP NHẬT TẠI CHỖ (tránh gây hiểu nhầm đếm 2 chai)
                                        self._broadcast("track_event", {
                                            "event": "DEFECT_CORRECTION",
                                            "track_id": track_id,
                                            "status": "DEFECT",
                                            "class_name": "defect",
                                            "conf": th["max_defect_conf"],
                                            "timestamp": f"{curr_ts:.2f}s",
                                            "is_update": True,
                                            "message": f"Cập nhật kết quả chai #{track_id}: Chuyển từ PASS sang DEFECT"
                                        })
                                        self._broadcast("defect_alert", {
                                            "track_id": track_id,
                                            "conf": th["max_defect_conf"],
                                            "timestamp": f"{curr_ts:.2f}s"
                                        })

                            is_defect_now = th["is_defect"]
                            state_now = th["state"]
                        else:
                            is_defect_now = (cls_id == 1)
                            state_now = "DEFECT" if is_defect_now else "PASS"

                        # Vẽ Bounding Box & Label trực quan
                        if is_defect_now:
                            color = (0, 0, 255)  # Đỏ (Defect)
                            label = f"DEFECT #{track_id} {conf:.2f}" if track_id != -1 else f"DEFECT {conf:.2f}"
                            has_defect_in_frame = True
                        elif state_now == "PASS":
                            color = (0, 255, 0)  # Xanh lá (Pass)
                            label = f"PASS #{track_id} {conf:.2f}" if track_id != -1 else f"PASS {conf:.2f}"
                        else:
                            # Đang quan sát tích lũy (INSPECTING)
                            color = (0, 200, 255)  # Cam vàng
                            label = f"SCAN #{track_id} {conf:.2f}" if track_id != -1 else f"SCAN {conf:.2f}"

                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        # Tag nền nhãn giúp đọc rõ trên nền công nghiệp
                        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                        cv2.rectangle(frame, (x1, max(0, y1 - 22)), (x1 + lw + 6, max(22, y1)), color, -1)
                        cv2.putText(frame, label, (x1 + 3, max(16, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2)

                # Chốt trạng thái cho các chai rời khỏi vùng nhìn camera (lost >= track_buffer frames)
                for tid, th in self.track_history.items():
                    if not th["logged"] and th["state"] == "INSPECTING":
                        if (self.frame_idx - th["last_seen_frame"]) >= track_buffer:
                            total_obs = th["pass_votes"] + th["defect_votes"]
                            if total_obs >= 3:
                                th["state"] = "PASS"
                                th["logged"] = True
                                th["logged_status"] = "PASS"
                                if csv_writer:
                                    csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 0, "pass", f"{th['max_conf']:.2f}", "PASS"])
                                    csv_file.flush()

                                self._broadcast("track_event", {
                                    "event": "PASS_FINALIZED",
                                    "track_id": tid,
                                    "status": "PASS",
                                    "class_name": "pass",
                                    "conf": th["max_conf"],
                                    "timestamp": f"{th['last_seen_ts']:.2f}s",
                                    "message": f"Chai #{tid} XÁC NHẬN ĐẠT CHUẨN (PASS)"
                                })
                            else:
                                th["state"] = "INVALID"

                # Quản lý Rejection Alert
                if has_defect_in_frame:
                    self.alert_frames = 18
                if self.alert_frames > 0:
                    self.alert_frames -= 1
                    self.alert_active = True
                else:
                    self.alert_active = False

                # Tính toán KPI thời gian thực
                self.total_pass = sum(1 for th in self.track_history.values() if th["state"] == "PASS")
                self.total_defect = sum(1 for th in self.track_history.values() if th["state"] == "DEFECT")
                self.inspecting_count = sum(1 for th in self.track_history.values() if th["state"] == "INSPECTING" and (self.frame_idx - th["last_seen_frame"]) < track_buffer)
                self.total_items = self.total_pass + self.total_defect
                self.defect_rate = (self.total_defect / self.total_items * 100) if self.total_items > 0 else 0.0

                # Vẽ HUD & Rejection Banner trên frame
                overlay = frame.copy()
                cv2.rectangle(overlay, (10, 10), (310, 135), (15, 23, 42), -1)
                cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
                cv2.rectangle(frame, (10, 10), (310, 135), (51, 65, 85), 1)

                cv2.putText(frame, f"FPS: {self.fps:.1f}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.putText(frame, f"DANG QUET (ON BELT): {self.inspecting_count}", (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 215, 255), 2)
                cv2.putText(frame, f"TOTAL PASS         : {self.total_pass}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                cv2.putText(frame, f"TOTAL DEFECT       : {self.total_defect}", (20, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                cv2.putText(frame, f"DEFECT RATE        : {self.defect_rate:.1f}%", (20, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

                if self.alert_active:
                    cv2.rectangle(frame, (0, 0), (width, 42), (0, 0, 220), -1)
                    cv2.putText(frame, ">>> REJECTION TRIGGERED: DEFECT DETECTED <<<",
                                (max(10, int(width / 2) - 250), 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # Nén JPEG cho stream
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                self.latest_jpeg = buf.tobytes()

                # Bắn cập nhật chỉ số định kỳ qua WebSocket (mỗi 5 frame)
                if self.frame_idx % 5 == 0:
                    self._broadcast("stats_update", {
                        "fps": round(self.fps, 1),
                        "total_pass": self.total_pass,
                        "total_defect": self.total_defect,
                        "inspecting_count": self.inspecting_count,
                        "total_items": self.total_items,
                        "defect_rate": round(self.defect_rate, 1),
                        "alert_active": self.alert_active,
                        "frame_idx": self.frame_idx
                    })

                # Tốc độ nạp frame tương thích
                time.sleep(0.01)

        finally:
            cap.release()

            # Chốt các sản phẩm còn đang quét khi kết thúc
            for tid, th in self.track_history.items():
                if not th["logged"]:
                    total_obs = th["pass_votes"] + th["defect_votes"]
                    if th["is_defect"]:
                        th["state"] = "DEFECT"
                        th["logged"] = True
                        th["logged_status"] = "DEFECT"
                        if csv_writer:
                            csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 1, "defect", f"{th['max_defect_conf']:.2f}", "DEFECT"])
                    elif total_obs >= 3:
                        th["state"] = "PASS"
                        th["logged"] = True
                        th["logged_status"] = "PASS"
                        if csv_writer:
                            csv_writer.writerow([f"{th['last_seen_ts']:.2f}", tid, 0, "pass", f"{th['max_conf']:.2f}", "PASS"])
                    else:
                        th["state"] = "INVALID"

            if csv_file:
                csv_file.flush()
                csv_file.close()

            # Cập nhật kết quả vào SessionManager
            self.total_pass = sum(1 for th in self.track_history.values() if th["state"] == "PASS")
            self.total_defect = sum(1 for th in self.track_history.values() if th["state"] == "DEFECT")
            self.elapsed_sec = time.time() - self.start_timestamp

            tracks_summary = [
                {
                    "track_id": th["track_id"],
                    "state": th["state"],
                    "class_name": "defect" if th["state"] == "DEFECT" else ("pass" if th["state"] == "PASS" else "invalid"),
                    "max_conf": round(th["max_conf"], 2),
                    "first_ts": round(th["first_ts"], 2),
                    "last_ts": round(th["last_seen_ts"], 2),
                    "obs_votes": th["pass_votes"] + th["defect_votes"],
                    "was_corrected": th.get("was_corrected", False)
                }
                for th in self.track_history.values()
                if th["state"] in ("PASS", "DEFECT")
            ]

            finalized_session = session_manager.finalize_session(
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
                "total_items": self.total_pass + self.total_defect,
                "defect_rate": round(self.defect_rate, 1),
                "duration_sec": round(self.elapsed_sec, 1)
            })
            logger.info(f"Đã hoàn thành và lưu phiên: {self.current_session_id}")


# Singleton instance
worker = InspectionWorker()
