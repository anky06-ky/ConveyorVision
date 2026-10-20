"""Khởi chạy ứng dụng Web Dashboard ConveyorVision.

Sử dụng:
    python run_app.py
    python run_app.py --port 8080 --host 0.0.0.0
"""

import argparse
import sys
from pathlib import Path

# Đảm bảo src/ nằm trong sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Thiết lập UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="ConveyorVision Web Dashboard Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Địa chỉ IP host (mặc định 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Cổng dịch vụ (mặc định 8000)")
    parser.add_argument("--reload", action="store_true", help="Kích hoạt hot reload khi phát triển")
    args = parser.parse_args()

    import uvicorn

    print("\n" + "=" * 70)
    print("      CONVEYORVISION — HỆ THỐNG KIỂM ĐỊNH BĂNG CHUYỀN THỜI GIAN THỰC")
    print("=" * 70)
    print(f"  * Giao diện Dashboard: http://{args.host}:{args.port}")
    print(f"  * Luồng Video Stream:  http://{args.host}:{args.port}/api/video_feed")
    print(f"  * API Docs (Swagger):  http://{args.host}:{args.port}/docs")
    print("  * Nhấn Ctrl+C trong terminal để dừng server.")
    print("=" * 70 + "\n")

    uvicorn.run(
        "conveyorvision.web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()

