"""Quản lý phiên kiểm định và lưu trữ lịch sử ConveyorVision (Session Manager).

Hỗ trợ:
- Lưu metadata phiên vào reports/sessions.json
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


class SessionManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("reports").resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.base_dir / "sessions.json"
        self._ensure_sessions_file()

    def _ensure_sessions_file(self) -> None:
        if not self.sessions_file.exists():
            with open(self.sessions_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

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
            "tracks": []
        }

        # Khởi tạo header file CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_s", "track_id", "class_id", "class_name", "confidence", "status"])

        sessions = self.get_all_sessions()
        sessions.insert(0, session)
        self.save_sessions(sessions)
        return session

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
