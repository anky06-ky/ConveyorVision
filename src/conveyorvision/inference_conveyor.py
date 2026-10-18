"""Pipeline kiểm định & đếm sản phẩm thời gian thực trên băng chuyền (ConveyorVision).

Tính năng:
    - Nhận diện và theo vết (Object Tracking với ByteTrack) qua từng frame.
    - Cơ chế Multi-frame Voting: Không khóa cứng nhãn ở frame đầu; tự động cập nhật trạng thái
      lỗi (DEFECT) nếu phát hiện khuyết tật trên bất kỳ frame quan sát tin cậy nào.
    - Khởi tạo an toàn biến thống kê (tránh UnboundLocalError khi video rỗng hoặc không mở được).
    - Thống kê thời gian thực: Tổng Pass, Tổng Defect, Tỷ lệ lỗi (Defect Rate %), FPS.
    - Cảnh báo trực quan (Visual Rejection Alert) khi phát hiện phế phẩm.
    - Xuất video kết quả và file log CSV.

Sử dụng:
    python src/conveyorvision/inference_conveyor.py --source raw_videos/video1.mp4
    python src/conveyorvision/inference_conveyor.py --source 0  # Webcam trực tiếp
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import cv2

# Thiết lập encoding UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_conveyor_inspection(
    source: str = "0",
    model_path: str = "models/conveyor_yolo26_30ep_best.pt",
    conf_thresh: float = 0.45,
    tracker_config: str = "bytetrack.yaml",
    out_video: str = "",
    out_csv: str = "reports/conveyor_inspection_log.csv",
    show_window: bool = True
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[LỖI] Chưa cài đặt Ultralytics. Vui lòng chạy: pip install -r requirements.txt")
        return None

    model_file = Path(model_path).resolve()
    if not model_file.exists():
        candidate_fallbacks = [
            Path("models/conveyor_yolo26_30ep_best.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
            Path("runs/detect/runs/train/conveyor_yolo26_30/weights/best.pt").resolve(),
            Path("runs/train/conveyor_yolo26_30/weights/last.pt").resolve(),
            Path("runs/detect/runs/train/conveyor_yolo26_30/weights/last.pt").resolve(),
            Path("weights/best.pt").resolve()
        ]
        found_fallback = next((p for p in candidate_fallbacks if p.exists()), None)
        if found_fallback:
            print(f"[INFO] Không tìm thấy {model_file}, sử dụng checkpoint: {found_fallback}")
            model_file = found_fallback
        else:
            print(f"[LỖI] Không tìm thấy file model: {model_file}")
            print("💡 Gợi ý: File trọng số (*.pt) không được lưu trên Git theo .gitignore.")
            print("   Bạn có thể tạo trọng số bằng cách:")
            print("     1. Chạy notebook notebooks/ConveyorVision_YOLO_Training.ipynb trên Google Colab GPU (~7.7 phút)")
            print("     2. Hoặc chạy CLI: python src/conveyorvision/train_pilot.py --epochs 30")
            print("     3. Hoặc tải file weights về và đặt vào models/conveyor_yolo26_30ep_best.pt")
            return None

    # Khởi tạo mô hình YOLO26
    print(f"[INFO] Nạp mô hình YOLO26: {model_file}...")
    model = YOLO(str(model_file))

    # Mở nguồn video (Webcam int hoặc file path)
    is_webcam = source.isdigit()
    cap_source = int(source) if is_webcam else source
    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        print(f"[LỖI] Không thể mở nguồn video: {source}")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Video Writer
    writer = None
    if out_video:
        out_v_path = Path(out_video).resolve()
        out_v_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_v_path), fourcc, fps_in, (width, height))
        print(f"[INFO] Lưu video kết quả tại: {out_v_path}")

    # CSV Logger
    csv_file = None
    csv_writer = None
    if out_csv:
        csv_p = Path(out_csv).resolve()
        csv_p.parent.mkdir(parents=True, exist_ok=True)
        csv_file = open(csv_p, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp_s", "track_id", "class_id", "class_name", "confidence", "status"])

    # Khởi tạo biến thống kê trước vòng lặp để tránh UnboundLocalError khi video rỗng
    track_history = {}     # {track_id: {"pass_votes": int, "defect_votes": int, "max_defect_conf": float, "logged": bool}}
    tracked_objects = {}   # {track_id: int(0: pass, 1: defect)}
    total_pass = 0
    total_defect = 0
    defect_rate = 0.0
    alert_frames = 0
    frame_idx = 0
    prev_time = time.time()

    print("\n" + "=" * 65)
    print("      HỆ THỐNG KIỂM ĐỊNH BĂNG CHUYỀN THỜI GIAN THỰC ĐANG CHẠY")
    print("=" * 65)
    print(f"  * Nguồn video:   {source}")
    print(f"  * Tracker:       {tracker_config} (ByteTrack)")
    print(f"  * Độ tự tin:     {conf_thresh}")
    print("  * Bấm phím 'q' trên cửa sổ video để dừng kiểm tra.")
    print("=" * 65 + "\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            curr_time = time.time()
            fps = 1.0 / max(1e-5, (curr_time - prev_time))
            prev_time = curr_time

            # Chạy tracking qua YOLO26 với cấu hình ByteTrack tường minh
            results = model.track(
                frame,
                persist=True,
                tracker=tracker_config,
                conf=conf_thresh,
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

                    # Cơ chế Multi-frame Voting: Cập nhật tích lũy nhãn quan sát cho từng track ID
                    if track_id != -1:
                        if track_id not in track_history:
                            track_history[track_id] = {
                                "pass_votes": 0,
                                "defect_votes": 0,
                                "max_defect_conf": 0.0,
                                "logged": False
                            }

                        if cls_id == 1:
                            track_history[track_id]["defect_votes"] += 1
                            if conf > track_history[track_id]["max_defect_conf"]:
                                track_history[track_id]["max_defect_conf"] = conf
                        else:
                            track_history[track_id]["pass_votes"] += 1

                        # Tiêu chí phân loại công nghiệp:
                        # Nếu vật thể xuất hiện defect >= 2 frames hoặc 1 frame defect với conf >= max(0.5, conf_thresh),
                        # chai sẽ được chốt là DEFECT (tránh việc gán nhầm pass ở frame đầu rìa ảnh).
                        is_defect = (
                            track_history[track_id]["defect_votes"] >= 2 or
                            (track_history[track_id]["defect_votes"] >= 1 and track_history[track_id]["max_defect_conf"] >= max(0.5, conf_thresh))
                        )
                        resolved_cls = 1 if is_defect else 0
                        tracked_objects[track_id] = resolved_cls

                        # Ghi log CSV khi đã quan sát đủ tin cậy (>= 3 frames hoặc khi phát hiện defect rõ ràng)
                        total_obs = track_history[track_id]["pass_votes"] + track_history[track_id]["defect_votes"]
                        if not track_history[track_id]["logged"] and (is_defect or total_obs >= 3):
                            track_history[track_id]["logged"] = True
                            if csv_writer:
                                ts = frame_idx / fps_in
                                cname = "defect" if resolved_cls == 1 else "pass"
                                status_str = "DEFECT" if resolved_cls == 1 else "PASS"
                                csv_writer.writerow([f"{ts:.2f}", track_id, resolved_cls, cname, f"{conf:.2f}", status_str])
                    else:
                        resolved_cls = cls_id

                    # Màu sắc: Xanh lá (pass = 0), Đỏ (defect = 1)
                    if resolved_cls == 1 or cls_id == 1:
                        color = (0, 0, 255)  # Đỏ
                        label = f"DEFECT #{track_id} {conf:.2f}" if track_id != -1 else f"DEFECT {conf:.2f}"
                        has_defect_in_frame = True
                    else:
                        color = (0, 255, 0)  # Xanh lá
                        label = f"PASS #{track_id} {conf:.2f}" if track_id != -1 else f"PASS {conf:.2f}"

                    # Vẽ Bounding Box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Cập nhật trạng thái báo động
            if has_defect_in_frame:
                alert_frames = 15

            # Đếm tổng pass và defect duy nhất
            total_pass = sum(1 for c in tracked_objects.values() if c == 0)
            total_defect = sum(1 for c in tracked_objects.values() if c == 1)
            total_items = total_pass + total_defect
            defect_rate = (total_defect / total_items * 100) if total_items > 0 else 0.0

            # Vẽ bảng điều khiển Dashboard (HUD) trên frame
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (320, 130), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

            cv2.putText(frame, f"FPS: {fps:.1f}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"TOTAL PASS  : {total_pass}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"TOTAL DEFECT: {total_defect}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, f"DEFECT RATE : {defect_rate:.1f}%", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # Banner cảnh báo loại bỏ phế phẩm (Rejection Banner)
            if alert_frames > 0:
                alert_frames -= 1
                cv2.rectangle(frame, (0, 0), (width, 40), (0, 0, 220), -1)
                cv2.putText(frame, ">>> REJECTION TRIGGERED: DEFECT DETECTED <<<", (int(width / 2) - 260, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            if writer:
                writer.write(frame)

            if show_window:
                cv2.imshow("ConveyorVision — YOLO26 Inspection", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[INFO] Người dùng bấm dừng.")
                    break
    finally:
        cap.release()
        if writer:
            writer.release()
        # Ghi nốt các track chưa kịp log vào CSV trước khi đóng file
        if csv_writer:
            for tid, th in track_history.items():
                if not th["logged"]:
                    resolved_cls = tracked_objects.get(tid, 0)
                    cname = "defect" if resolved_cls == 1 else "pass"
                    status_str = "DEFECT" if resolved_cls == 1 else "PASS"
                    csv_writer.writerow(["END", tid, resolved_cls, cname, f"{th['max_defect_conf']:.2f}", status_str])
        if csv_file:
            csv_file.close()
        cv2.destroyAllWindows()

    print("\n" + "=" * 65)
    print("                     TỔNG KẾT BĂNG CHUYỀN                      ")
    print("=" * 65)
    print(f"  - Tổng số sản phẩm qua kiểm tra: {len(tracked_objects)}")
    print(f"  - Số sản phẩm ĐẠT CHUẨN (PASS):  {total_pass}")
    print(f"  - Số sản phẩm LỖI (DEFECT):      {total_defect}")
    print(f"  - Tỷ lệ lỗi (Defect Rate):       {defect_rate:.2f}%")
    if out_csv:
        print(f"  - Chi tiết lịch sử ghi nhận tại: {out_csv}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConveyorVision Realtime Inspection")
    parser.add_argument("--source", type=str, default="0", help="Nguồn video (0 cho webcam, hoặc đường dẫn file .mp4)")
    parser.add_argument("--model", type=str, default="models/conveyor_yolo26_30ep_best.pt", help="File trọng số YOLO26")
    parser.add_argument("--tracker", type=str, default="bytetrack.yaml", help="File cấu hình tracker (mặc định bytetrack.yaml)")
    parser.add_argument("--conf", type=float, default=0.45, help="Ngưỡng tin cậy (Confidence threshold)")
    parser.add_argument("--out-video", type=str, default="", help="Đường dẫn file video đầu ra (tùy chọn)")
    parser.add_argument("--out-csv", type=str, default="reports/conveyor_inspection_log.csv", help="File log CSV")
    parser.add_argument("--no-show", action="store_true", help="Không mở cửa sổ GUI (chạy headless)")

    args = parser.parse_args()
    run_conveyor_inspection(
        source=args.source,
        model_path=args.model,
        conf_thresh=args.conf,
        tracker_config=args.tracker,
        out_video=args.out_video,
        out_csv=args.out_csv,
        show_window=not args.no_show
    )
