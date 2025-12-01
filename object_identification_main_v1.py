#!/usr/bin/env python3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
from threading import Thread
import os
import time
import sys
import zipfile
import traceback
from pathlib import Path
import shutil
import logging
from utils.inhouse_cv_v3 import *
from utils.updating_database import *
from utils.send_sms import *
from utils.upload_cv_video import *
from utils.check_cvproduct import *
from utils import login
from utils import config
from logging.handlers import RotatingFileHandler

# ---------------- Setup ----------------
BASE_DIR = Path("transaction_videos_folders")
TEMP_DIR = BASE_DIR / "post_archive"
FAILED_UPLOADS_DIR = BASE_DIR / "failed_uploads"
LOG_FILE = Path("logs_object_identification") / "object_identification_v2.log"

# Ensure directories exist
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ---------------- Logging ----------------
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5)
stream_handler = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[file_handler, stream_handler]
)
log = logging.getLogger("watchdog")


# ---------------- Safe unzip ----------------
def _is_within(base: Path, target: Path) -> bool:
    try:
        base = base.resolve()
        target = target.resolve()
        return str(target).startswith(str(base))
    except Exception:
        return False

def safe_extractall(zf: zipfile.ZipFile, dest: Path):
    for member in zf.namelist():
        member_path = dest / member
        if not _is_within(dest, member_path):
            raise RuntimeError(f"Unsafe ZIP path detected: {member}")
    zf.extractall(dest)


def unzip_in_place(zip_path):
    zip_path = Path(zip_path)
    extract_dir = zip_path.parent / zip_path.stem
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for file in zf.namelist():
            log.info(f" - {file}")
        safe_extractall(zf, extract_dir)
    return extract_dir


def extract_transaction_info(extract_dir: Path):
    subfolders = list(extract_dir.glob("*"))
    if not subfolders:
        raise FileNotFoundError(f"No subfolders found in {extract_dir}")

    subfolder = subfolders[0]
    transaction_name = subfolder.name
    video_path_0 = subfolder / "media_0.mp4"
    video_path_1 = subfolder / "media_1.mp4"
    
    json_path = subfolder / "user_activities.json"
    if not json_path.exists():
        json_path = None

    available_cams = []

    if video_path_0.exists():
        available_cams.append(str(video_path_0))
    if video_path_1.exists():
        available_cams.append(str(video_path_1))
    if not available_cams:
        raise FileNotFoundError(f"No media_*.mp4 files found in {subfolder}")

    return transaction_name, available_cams, str(subfolder), json_path


def wait_until_stable(filepath, wait_sec=1, max_wait=50):
    last_size = -1
    stable_count = 0
    for _ in range(max_wait):
        current_size = os.path.getsize(filepath)
        if current_size == last_size:
            stable_count += 1
            if stable_count >= 3:
                return True
        else:
            stable_count = 0
        last_size = current_size
        time.sleep(wait_sec)
    return False


def calculate_frames(sub_folder_path, stream):
    video_path = os.path.join(sub_folder_path, f"media_{stream}.mp4")
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")
    total = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    video.release()
    log.info(f"Total frames in {video_path}: {total}")
    return total

def camera_logger(base_logger, stream):
    class CamLogger:
        def __getattr__(self, name):
            def wrapper(msg, *args, **kwargs):
                getattr(base_logger, name)(f"[CAM {stream}] {msg}", *args, **kwargs)
            return wrapper
    return CamLogger()

def convert_video_to_frames(logger, sub_folder_path, transaction_number, stream):
    video_path = os.path.join(sub_folder_path, f"media_{stream}.mp4")
    algo_frames = config.algo_frames
    vid_to_frames_save_path = os.path.join(algo_frames, f"video_frames_cam{stream}/{transaction_number}/Frames")
    logger.info(f"Output directories created: frames -> {vid_to_frames_save_path}")
    os.makedirs(vid_to_frames_save_path, exist_ok=True)
    frames_path, total_frames = vid_to_frames_save(video_path, vid_to_frames_save_path)
    kept = len([f for f in os.listdir(frames_path) if f.lower().endswith((".jpg", ".png", ".jpeg"))])
    logger.info(f"Extracted {kept} frames from the video")


def cv_algo(logger, sub_folder_path, json_file_path, transaction_number, stream):
    t0 = time.time()
    bbox_data = generate_bboxes(
        logger,
        sub_folder_path=sub_folder_path,
        json_file_path=json_file_path,
        transaction_number=transaction_number,
        stream=stream
    )
    activity_list = process_bboxes_and_classify(logger, bbox_data)
    logger.info(f"Completed CV algorithm in {time.time()-t0:.2f}s")
    return activity_list


# ---------------- Worker ----------------
def worker(q: Queue):
    try:
        # Cleanup non-ZIP files before starting
        for item in Path(TEMP_DIR).iterdir():
            try:
                if item.is_file() and not item.name.endswith(".zip"):
                    item.unlink()
                    log.info(f"Deleted non-ZIP file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    log.info(f"Deleted leftover directory: {item}")
            except Exception as e:
                log.error(f"Error deleting {item}: {e}")

        while True:
            zip_file_path = q.get()
            start = time.time()
            extracted_dir = None
            transaction_number = None
            json_file_path = None

            try:
                if zip_file_path:
                    log.info(f"Detected new file: {zip_file_path}")

                log.info("Checking stability…")
                if not wait_until_stable(zip_file_path):
                    log.error("File never stabilized, moving to failed_uploads")
                    shutil.move(zip_file_path, FAILED_UPLOADS_DIR / Path(zip_file_path).name)
                    continue

                extracted_dir = unzip_in_place(zip_file_path)
                transaction_number, available_cams, sub_folder_path, json_file_path = extract_transaction_info(extracted_dir)
                if json_file_path is None:
                    log.info("Json file doesn't exist, Just uploading just the video, nothing else")
                else:
                    json_file_path = str(json_file_path)

                total_frames = calculate_frames(sub_folder_path, stream="0")
                # recording_successful(log, json_file_path, transaction_number)

                if total_frames >= 30000:
                    if json_file_path:
                        log.info("Not Processing this transaction—it is too big")
                        transaction_too_big_alert(log, json_file_path, transaction_number)
                        shutil.move(zip_file_path, FAILED_UPLOADS_DIR / Path(zip_file_path).name)
                        shutil.rmtree(extracted_dir)
                        continue

                products_cam0 = set()
                products_cam1 = set()
                cv_activities_cam0 = []
                cv_activities_cam1 = []
                cam0_logger = camera_logger(log, "0")
                cam1_logger = camera_logger(log, "1")

                if len(available_cams) >= 1:
                    if any("media_0" in cam for cam in available_cams):
                        stream = "0"
                        if config.CV_FLAG:
                            cv_activities_cam0 = cv_algo(cam0_logger, sub_folder_path, json_file_path, transaction_number, stream)
                            log.info(f" CV ACTIVITIES of CAM 0: {cv_activities_cam0}")
                            if json_file_path:
                                products_cam0 = cv_product_present(json_file_path, cv_activities_cam0, stream)
                                log.info(f"Products (Cam 0): {products_cam0}")
                        else:
                            convert_video_to_frames(cam0_logger, sub_folder_path, transaction_number, stream)

                    if any("media_1" in cam for cam in available_cams):
                        stream = "1"
                        log.info(f"CV_FLAG : {config.CV_FLAG}")
                        if config.CV_FLAG:
                            log.info("CV Flag is True")
                            cv_activities_cam1 = cv_algo(cam1_logger, sub_folder_path, json_file_path, transaction_number, stream)
                            log.info(f" CV ACTIVITIES of CAM 1: {cv_activities_cam1}")
                            if json_file_path:
                                products_cam1 = cv_product_present(json_file_path, cv_activities_cam1, stream)
                                log.info(f"Products (Cam 1): {products_cam1}")
                        else:
                            convert_video_to_frames(cam1_logger, sub_folder_path, transaction_number, stream)
                            
                    # log.info(f" Products_Cam 0: {products_cam0}")
                    # log.info(f"CV Activities Cam 0: {cv_activities_cam0}")
                    if config.CV_FLAG:
                        combined_products = products_cam0.union(products_cam1)
                        combined_activities = cv_activities_cam0 + cv_activities_cam1
                        
                        if combined_products:
                            log.info(f"✅ Found CV product(s): {combined_products}")
                            if json_file_path:
                                update_view_activities_dashboard(log, json_file_path, combined_activities)
                                log.info(f"CV Activities Combined: {combined_activities}")
                                log.info(f"CV Products Combined: {config.cv_products}")
                            upload_both_bbox_videos(log, transaction_number)
                        else:
                            log.info("No products detected in CV pipeline — uploading normal videos")
                            # upload_both_normal_videos(log, transaction_number)
                            upload_both_bbox_videos(log, transaction_number)
                            
                        if json_file_path:
                            sms_alert(log, json_file_path, combined_activities, transaction_number, config.cv_products)
                    else:
                        upload_both_normal_videos(log, transaction_number)
                
                #shutil.move(zip_file_path, FAILED_UPLOADS_DIR / Path(zip_file_path).name)
                if extracted_dir.exists():
                    shutil.rmtree(extracted_dir)
                if Path(zip_file_path).exists():
                    os.remove(zip_file_path)
                log.info(f"✓ Completed all steps for {transaction_number} in {time.time()-start:.2f}s")

            except Exception as e:
                log.error(f"CV Algo failed. Unexpected error on {zip_file_path}: {e}")
                if transaction_number:
                    log.info("Due to failed transaction, Uploading it without processing")
                    upload_both_normal_videos(log, transaction_number)
                shutil.move(zip_file_path, FAILED_UPLOADS_DIR / Path(zip_file_path).name)
                if json_file_path:
                    transaction_failure_alert(log, json_file_path, transaction_number)
                if extracted_dir and extracted_dir.exists():
                    shutil.rmtree(extracted_dir)
                log.exception(f"Unexpected error on {zip_file_path}")

            finally:
                q.task_done()

    except Exception as e:
        log.error(f"[FATAL] Worker thread Crashed: {e}")
        log.exception(e)
        raise

# ---------------- Watchdog / Threads ----------------
def recovery_worker(queue: Queue, scan_dir: Path, scan_interval: int = 1800):
    log.info("[recovery_worker] Started background ZIP scanner")
    while True:
        try:
            if queue.empty():
                for z in scan_dir.glob("*.zip"):
                    if time.time() - z.stat().st_mtime > 10:
                        log.info(f"[recovery_worker] queueing: {z}")
                        queue.put(str(z))
        except Exception:
            log.exception("[recovery_worker] error")
        time.sleep(scan_interval)


class MyHandler(FileSystemEventHandler):
    def __init__(self, queue):
        self.q = queue

    def on_created(self, event):
        if not event.src_path.endswith(".zip"):
            return
        if event.is_directory:
            return
        self.q.put(event.src_path)
        log.info(f"ZIP file created: {event.src_path} (queue size: {self.q.qsize()})")


class LoggingQueue(Queue):
    def put(self, item, *args, **kwargs):
        with self.mutex:
            if item in self.queue:
                log.info(f"[QUEUE PUT] skipped duplicate item={item!r}")
                return
        super().put(item, *args, **kwargs)
        with self.mutex:
            snapshot = list(self.queue)
        log.info(f"[QUEUE PUT] new item={item!r}, snapshot={snapshot}")

    def get(self, *args, **kwargs):
        item = super().get(*args, **kwargs)
        with self.mutex:
            snapshot = list(self.queue)
        log.info(f"[QUEUE GET] popped={item!r}, remaining={snapshot}")
        return item


def heartbeat(q: Queue, threads: dict, interval: int = 300):
    log.info(f"[heartbeat] started (interval={interval}s)")
    while True:
        try:
            w_alive = threads.get('worker').is_alive() if threads.get('worker') else False
            r_alive = threads.get('recovery').is_alive() if threads.get('recovery') else False
            log.info(f"[heartbeat] alive | queue={q.qsize()} | worker_alive={w_alive} | recovery_alive={r_alive}")
        except Exception:
            log.exception("[heartbeat] error")
        time.sleep(interval)


def start_worker(q: Queue):
    t = Thread(target=worker, args=(q,), daemon=True, name="worker")
    t.start()
    log.info("[supervisor] started worker thread")
    return t


def start_recovery(q: Queue, scan_dir: Path):
    t = Thread(target=recovery_worker, args=(q, scan_dir), daemon=True, name="recovery")
    t.start()
    log.info("[supervisor] started recovery thread")
    return t


def supervisor(q: Queue, scan_dir: Path, threads: dict, check_every: int = 60):
    log.info(f"[supervisor] started (interval={check_every}s)")
    while True:
        try:
            if threads.get('worker') is None or not threads['worker'].is_alive():
                log.error("[supervisor] worker thread is dead; restarting")
                threads['worker'] = start_worker(q)

            if threads.get('recovery') is None or not threads['recovery'].is_alive():
                log.error("[supervisor] recovery thread is dead; restarting")
                threads['recovery'] = start_recovery(q, scan_dir)
        except Exception:
            log.exception("[supervisor] error while supervising")
        time.sleep(check_every)


# ---------------- Main ----------------
if __name__ == "__main__":
    q = LoggingQueue()
    threads = {}
    
    log.info("Running initial scan for ZIP files...")
    for z in Path(TEMP_DIR).glob("*.zip"):
        try:
            # Skip if zip is still being written (very new)
            if time.time() - z.stat().st_mtime > 5:
                log.info(f"[INITIAL SCAN] Queueing existing ZIP: {z}")
                q.put(str(z))
            else:
                log.info(f"[INITIAL SCAN] Skipping {z} because it's too new")
        except Exception as e:
            log.error(f"[INITIAL SCAN] Error reading {z}: {e}")
            
    threads['worker'] = start_worker(q)
    threads['recovery'] = start_recovery(q, TEMP_DIR)

    Thread(target=heartbeat, args=(q, threads, 1500), daemon=True, name="heartbeat").start()
    Thread(target=supervisor, args=(q, TEMP_DIR, threads, 100), daemon=True, name="supervisor").start()

    observer = Observer()
    observer.schedule(MyHandler(q), path=str(TEMP_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
