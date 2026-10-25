# -*- coding: utf-8 -*-
"""Trích frame từ video bằng OpenCV, theo bước thời gian cố định.

Module này cung cấp chức năng trích xuất các khung hình từ file video 
và lưu dưới dạng hình ảnh JPG để phục vụ cho việc tạo dataset huấn luyện.

Example:
    Trích xuất 2 frame mỗi giây từ video:
    
    >>> from conveyorvision.video_io import extract_frames
    >>> extract_frames(
    ...     video_path="raw_videos/demo.mp4",
    ...     out_dir="data/images/train",
    ...     target_fps=2.0,
    ...     manifest_path="data/manifest.csv"
    ... )

Hoặc qua command line:
    $ python src/conveyorvision/video_io.py \\
        --video raw_videos/video1.mp4 \\
        --out_dir data/images/train \\
        --fps 2

Mỗi lần chạy sẽ:
    - Lưu ảnh JPG vào --out_dir, đặt tên theo <video_id>_<frame_idx>.jpg
    - Append vào data/manifest.csv (tạo mới nếu chưa có) với các cột:
        video_id, frame_idx, timestamp_s, image_path
"""

import argparse
import csv
import os
from pathlib import Path
from typing import Optional

import cv2


def extract_frames(
    video_path: str,
    out_dir: str,
    target_fps: float = 2.0,
    manifest_path: str = "data/manifest.csv"
) -> int:
    """Trích xuất các khung hình từ video theo tần suất chỉ định.
    
    Args:
        video_path: Đường dẫn đến file video nguồn.
        out_dir: Thư mục đích để lưu các ảnh đã trích xuất.
        target_fps: Số frame cần lấy mỗi giây (mặc định: 2.0).
        manifest_path: Đường dẫn đến file manifest CSV (mặc định: data/manifest.csv).
    
    Returns:
        Số lượng frame đã được lưu thành công.
    
    Raises:
        RuntimeError: Nếu không thể mở file video.
    
    Example:
        >>> extract_frames("demo.mp4", "output/", target_fps=5.0)
        150  # số frame đã lưu
    """
    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    video_id = video_path.stem
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    # Số frame gốc cần bỏ qua giữa 2 lần lấy mẫu, để đạt target_fps mong muốn
    step = max(int(round(native_fps / target_fps)), 1)

    manifest_exists = os.path.exists(manifest_path)
    manifest_file = open(manifest_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(manifest_file)
    
    if not manifest_exists:
        writer.writerow(["video_id", "frame_idx", "timestamp_s", "image_path"])

    frame_idx = 0
    saved = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % step == 0:
                timestamp_s = frame_idx / native_fps
                image_name = f"{video_id}_{frame_idx:06d}.jpg"
                image_path = out_dir / image_name
                cv2.imwrite(str(image_path), frame)
                writer.writerow([video_id, frame_idx, f"{timestamp_s:.2f}", str(image_path)])
                saved += 1
            frame_idx += 1
    finally:
        cap.release()
        manifest_file.close()
    
    return saved


def main():
    """Entry point cho command-line interface."""
    parser = argparse.ArgumentParser(
        description="Trích frame từ video cho ConveyorVision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Trích 2 frame mỗi giây từ video:
    python video_io.py --video demo.mp4 --out_dir data/images/train --fps 2
    
    # Trích 1 frame mỗi 2 giây (0.5 fps):
    python video_io.py --video demo.mp4 --out_dir data/images/val --fps 0.5
        """
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Đường dẫn file video"
    )
    parser.add_argument(
        "--out_dir",
        required=True,
        help="Thư mục lưu ảnh (vd. data/images/train)"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="Số frame lấy mỗi giây (mặc định: 2)"
    )
    parser.add_argument(
        "--manifest",
        default="data/manifest.csv",
        help="Đường dẫn file manifest.csv (mặc định: data/manifest.csv)",
    )
    args = parser.parse_args()

    try:
        saved = extract_frames(args.video, args.out_dir, args.fps, args.manifest)
        print(f"✓ Đã lưu {saved} frame vào {args.out_dir}")
        print(f"✓ Manifest: {args.manifest}")
    except RuntimeError as e:
        print(f"✗ Lỗi: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
