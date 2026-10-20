"""Quản lý phiên kiểm định, lưu trữ lịch sử và cấu hình ConveyorVision (Session Manager).

Hỗ trợ:
- Lưu metadata phiên vào reports/sessions.json
- Đánh dấu phiên COMPLETED hoặc FAILED khi gặp lỗi (tránh kẹt trạng thái RUNNING)
- Lưu trữ cấu hình hệ thống reports/settings.json
- Xuất log chi tiết từng track ra CSV
- Truy vấn lịch sử phiên, đọc bản ghi chi tiết
"""

import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SETTINGS: Dict[str, Any] = {
    "tracker": "bytetrack.yaml",
    "lost_track_buffer": 30,
    "min_observation_votes": 3,
    "auto_save_csv": True,
    "sound_alarm": True,
    "default_conf": 0.45
}


class SessionManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("reports").resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.base_dir / "sessions.json"
        self.settings_file = self.base_dir / "settings.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.sessions_file.exists():
            with open(self.sessions_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        if not self.settings_file.exists():
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2, ensure_ascii=False)

    def get_settings(self) -> Dict[str, Any]:
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                res = DEFAULT_SETTINGS.copy()
                res.update(data)
                return res
        except Exception:
            return DEFAULT_SETTINGS.copy()

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_settings()
        # Ép kiểu an toàn
        if "tracker" in new_settings:
            current["tracker"] = str(new_settings["tracker"]).strip()
        if "lost_track_buffer" in new_settings:
            current["lost_track_buffer"] = max(1, int(new_settings["lost_track_buffer"]))
        if "min_observation_votes" in new_settings:
            current["min_observation_votes"] = max(1, int(new_settings["min_observation_votes"]))
        if "auto_save_csv" in new_settings:
            current["auto_save_csv"] = bool(new_settings["auto_save_csv"])
        if "sound_alarm" in new_settings:
            current["sound_alarm"] = bool(new_settings["sound_alarm"])
        if "default_conf" in new_settings:
            current["default_conf"] = round(float(new_settings["default_conf"]), 2)

        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        return current

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        try:
            with open(self.sessions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        with open(self.sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)

    def create_session(
        self,
        source: str,
        model_name: str,
        tracker: str,
        conf_thresh: float
    ) -> Dict[str, Any]:
        now = datetime.now()
        session_id = f"SES_{now.strftime('%Y%m%d_%H%M%S')}"
        csv_filename = f"inspection_{session_id}.csv"
        csv_path = self.base_dir / csv_filename

        session = {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "start_time": now.strftime("%H:%M:%S %d/%m/%Y"),
            "end_time": "",
            "duration_sec": 0,
            "source": source,
            "model_name": model_name,
            "tracker": tracker,
            "conf_thresh": conf_thresh,
            "status": "RUNNING",
            "total_items": 0,
            "total_pass": 0,
            "total_defect": 0,
            "defect_rate": 0.0,
            "avg_fps": 0.0,
            "csv_file": csv_filename,
            "video_file": "",
            "tracks": [],
            "error_message": ""
        }

        # Khởi tạo header file CSV
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp_s", "track_id", "class_id", "class_name", "confidence", "status"])
        except Exception:
            pass

        sessions = self.get_all_sessions()
        sessions.insert(0, session)
        self.save_sessions(sessions)
        return session

    def fail_session(self, session_id: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Đánh dấu phiên kiểm định bị lỗi (tránh kẹt trạng thái RUNNING)."""
        sessions = self.get_all_sessions()
        target = None
        for s in sessions:
            if s.get("session_id") == session_id:
                now = datetime.now()
                s["status"] = "FAILED"
                s["end_time"] = now.strftime("%H:%M:%S %d/%m/%Y")
                s["error_message"] = str(error_message)
                target = s
                break

        if target:
            self.save_sessions(sessions)
        return target

    def finalize_session(
        self,
        session_id: str,
        total_pass: int,
        total_defect: int,
        avg_fps: float,
        duration_sec: float,
        tracks: List[Dict[str, Any]],
        video_filename: str = ""
    ) -> Optional[Dict[str, Any]]:
        sessions = self.get_all_sessions()
        target = None
        for s in sessions:
            if s.get("session_id") == session_id:
                now = datetime.now()
                total_items = total_pass + total_defect
                rate = (total_defect / total_items * 100) if total_items > 0 else 0.0

                s["status"] = "COMPLETED"
                s["end_time"] = now.strftime("%H:%M:%S %d/%m/%Y")
                s["duration_sec"] = round(duration_sec, 1)
                s["total_items"] = total_items
                s["total_pass"] = total_pass
                s["total_defect"] = total_defect
                s["defect_rate"] = round(rate, 2)
                s["avg_fps"] = round(avg_fps, 1)
                s["video_file"] = video_filename
                s["tracks"] = tracks
                target = s
                break

        if target:
            self.save_sessions(sessions)
        return target

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        sessions = self.get_all_sessions()
        for s in sessions:
            if s.get("session_id") == session_id:
                return s
        return None

    def get_session_csv_path(self, session_id: str) -> Optional[Path]:
        s = self.get_session(session_id)
        if s and s.get("csv_file"):
            p = self.base_dir / s["csv_file"]
            if p.exists():
                return p
        # Thử tìm theo tên file mặc định
        p = self.base_dir / f"inspection_{session_id}.csv"
        return p if p.exists() else None

    def delete_session(self, session_id: str) -> bool:
        sessions = self.get_all_sessions()
        found = False
        remaining = []
        for s in sessions:
            if s.get("session_id") == session_id:
                found = True
                # Xóa file csv kèm theo nếu có
                if s.get("csv_file"):
                    csv_p = self.base_dir / s["csv_file"]
                    if csv_p.exists():
                        try:
                            csv_p.unlink()
                        except Exception:
                            pass
            else:
                remaining.append(s)

        if found:
            self.save_sessions(remaining)
        return found


# Singleton instance
session_manager = SessionManager()
