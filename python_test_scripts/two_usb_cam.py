import cv2
import os
import time
from multiprocessing import Process, Event

def record_video(device_id, output_path, stop_event, width=1280, height=960, fps=100):
    print(f"[INFO] Starting camera {device_id} recording...")

    pipeline = (
        f'v4l2src device={device_id} ! '
        f'image/jpeg, width={width}, height={height}, framerate={fps}/1 ! '
        'jpegdec ! '
        'videoconvert ! '
        'appsink'
    )

    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera: {device_id}")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20, (width, height))

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            print(f"[ERROR] Failed to read frame from {device_id}")
            break
        out.write(frame)

    cap.release()
    out.release()
    print(f"[INFO] Finished recording camera {device_id}.")

if __name__ == "__main__":
    # from multiprocessing import Event

    stop_event = Event()

    # Define output files
    output_path_cam0 = "output_data/cam0_output.mp4"
    output_path_cam1 = "output_data/cam1_output_17.mp4"

    # Start both camera processes2
    # p1 = Process(target=record_video, args=("/dev/video0", output_path_cam0, stop_event))
    p2 = Process(target=record_video, args=("/dev/video0", output_path_cam1, stop_event))

    # p1.start()
    p2.start()

    print("Recording... Press 'q' then ENTER to stop.")
    while True:
        key = input().strip().lower()
        if key == 'q':
            stop_event.set()
            break

    # p1.join()
    p2.join()
    print("Recording stopped.")


# Save images instead of videos, which is much computationally heavy then saving videos.
# import cv2
# import os
# import threading

# def capture_camera(device_id, output_dir, width=1920, height=1080, fps=60):
#     print(f"Starting capture on camera: {device_id}")

#     # GStreamer pipeline for each device
#     pipeline = (
#         f'v4l2src device={device_id} ! '
#         f'image/jpeg, width={width}, height={height}, framerate={fps}/1 ! '
#         'jpegdec ! '
#         'videoconvert ! '
#         'appsink'
#     )

#     os.makedirs(output_dir, exist_ok=True)
#     cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

#     if not cap.isOpened():
#         print(f"Error: Could not open camera {device_id}")
#         return

#     i = 0
#     try:
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 print(f"Error reading frame from {device_id}")
#                 break
#             frame_path = os.path.join(output_dir, f"image{i}.png")
#             cv2.imwrite(frame_path, frame)
#             i += 1
#     except KeyboardInterrupt:
#         print(f"Stopping camera {device_id}")
#     finally:
#         cap.release()

# # Define output directories for both cams
# cam0_dir = "/home/parth/camera-preview-pipeline/output_data/cam0"
# cam1_dir = "/home/parth/camera-preview-pipeline/output_data/cam1"

# # Create threads for both cameras
# thread0 = threading.Thread(target=capture_camera, args=("/dev/video0", cam0_dir))
# thread1 = threading.Thread(target=capture_camera, args=("/dev/video2", cam1_dir))

# # Start both threads
# thread0.start()
# thread1.start()

# # Wait for both threads to complete (or Ctrl+C)
# thread0.join()
# thread1.join()
