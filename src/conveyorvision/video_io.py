"""Trich frame tu video bang OpenCV, theo buoc thoi gian co dinh.

Vi du:
    python video_io.py --video raw_videos/video1.mp4 \
        --out_dir data/images/train --fps 2

Moi lan chay se:
  - Luu anh JPG vao --out_dir, dat ten theo <video_id>_<frame_idx>.jpg
  - Append vao data/manifest.csv (tao moi neu chua co) voi cac cot:
    video_id, frame_idx, timestamp_s, image_path
"""

import argparse
import csv
import os
from pathlib import Path

import cv2


def extract_frames(video_path: str, out_dir: str, target_fps: float, manifest_path: str) -> int:
    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    video_id = video_path.stem
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Khong mo duoc video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    # So frame goc can bo qua giua 2 lan lay mau, de dat target_fps mong muon
    step = max(int(round(native_fps / target_fps)), 1)

    manifest_exists = os.path.exists(manifest_path)
    manifest_file = open(manifest_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(manifest_file)
    if not manifest_exists:
        writer.writerow(["video_id", "frame_idx", "timestamp_s", "image_path"])

    frame_idx = 0
    saved = 0
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

    cap.release()
    manifest_file.close()
    return saved


def main():
    parser = argparse.ArgumentParser(description="Trich frame tu video cho ConveyorVision")
    parser.add_argument("--video", required=True, help="Duong dan file video")
    parser.add_argument("--out_dir", required=True, help="Thu muc luu anh (vd. data/images/train)")
    parser.add_argument("--fps", type=float, default=2.0, help="So frame lay moi giay (mac dinh 2)")
    parser.add_argument(
        "--manifest",
        default="data/manifest.csv",
        help="Duong dan file manifest.csv (mac dinh data/manifest.csv)",
    )
    args = parser.parse_args()

    saved = extract_frames(args.video, args.out_dir, args.fps, args.manifest)
    print(f"Da luu {saved} frame vao {args.out_dir}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
