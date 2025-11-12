import threading
import time
import requests
import os
import cv2
from utils import config
from pathlib import Path 
import shutil
from utils import login
from utils import config
import json
from datetime import datetime
from collections import defaultdict
import sys
import traceback
import re
from natsort import natsorted
import moviepy.video.io.ImageSequenceClip
from utils.send_alert import send_alert
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

def upload_to_dashboard(base_url, post_transid, fileobj, access_token, logger):
    """
    Attempts a direct upload of the archive to the dashboard endpoint. Returns True if successful, else False.
    """
    url = f"{base_url}/loyalty/upload-media/cv?media_event_type=COMPUTER_VISION&invoice_id={post_transid}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response_media = requests.post(url, files={'file': fileobj}, headers=headers)
        if response_media.status_code == 200:
            status = f'CV Media Uploaded Successfully (Transaction: {post_transid})'
            logger.info(f"      Uploaded {post_transid}")
            threading.Thread(target=send_alert, args=(logger, config.vicki_app, status, False)).start()
            return True
        elif response_media.status_code == 504:
            status = (
                f'Endpoint Time-out Error for CV Media Upload ({response_media.status_code}) '
                f'(Transaction: {post_transid})'
            )
            logger.info(response_media)
            logger.info(f"      Uploading CV media - FAILED (Reason: Gateway Timeout) for {post_transid}")
            threading.Thread(target=send_alert, args=(logger, config.vicki_app, status)).start()
            return False
        else:
            status = f'Media Upload Failed (Transaction: {post_transid})'
            logger.info(response_media)
            logger.info(f"      Uploading CV media - FAILED for {post_transid}")
            logger.info("      Archiving Transaction for batch processing")
            threading.Thread(target=send_alert, args=(logger, config.vicki_app, status)).start()
            return False
    except Exception as e:
        logger.info(f"      Uploading CV media with exception: {e}")
        return False
   
def make_archive(source, destination, format="zip"):
    """
    Create an archive of `source` directly into `destination` (no temp dir).
    """
    source = Path(source)
    destination = Path(destination)

    # Strip extension if passed
    base_name = str(destination.with_suffix(""))

    shutil.make_archive(base_name, format, root_dir=str(source.parent), base_dir=source.name)
    return destination

def upload_file_to_dashboard(file_path, post_transid, logger):
    with file_path.open("rb") as fp:
        base_url, machine_id, machine_token, machine_api_key = login.get_custom_machine_settings(config.vicki_app, logger)
        access_token = login.get_current_access_token(base_url, machine_id, machine_token, machine_api_key, logger)
        return upload_to_dashboard(base_url, post_transid, fp, access_token, logger)


# --- helper: gather and (optionally) thin images ---
def _gather_images(images_dir: Path):
    files = natsorted(os.listdir(images_dir))
    imgs  = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))]

    # Re-ordered so >10000 is actually reachable
    if len(imgs) > 10000:
        imgs = [img for idx, img in enumerate(imgs) if idx % 4 == 0]
    elif len(imgs) > 3000:
        imgs = [img for idx, img in enumerate(imgs) if idx % 2 == 0]
    
    return imgs

def upload_video(logger, post_transid, stream="0", is_bbox=False):
    """
    Creates and uploads an MP4 video from frame_*.jpg/png images.

    - If is_bbox=False → expects: output_data/video_frames_cam{stream}/{txn}/Frames
    - If is_bbox=True  → expects: output_data/bbox_labelled_frames_cam{stream}/{txn}/Frames
    
    Then zips, uploads, and cleans up.
    Returns True/False.
    """
    label = "BBOX" if is_bbox else "NORMAL"
    try:
        assert stream in ("0", "1"), "stream must be '0' or '1'"
        logger.info(f"[UPLOAD START] Transaction={post_transid} | Stream={stream} | Type={label}")

        base_root = (
            f"output_data/bbox_labelled_frames_cam{stream}"
            if is_bbox
            else f"output_data/video_frames_cam{stream}"
        )
        base_directory = Path(base_root) / f"{post_transid}"
        images_dir = base_directory / "Frames"
        video_dir = base_directory
        video_dir.mkdir(parents=True, exist_ok=True)

        if not images_dir.exists():
            status = f"No '{label}' frame folder found → {images_dir}"
            threading.Thread(target=send_alert, args=(logger, config.vicki_app, status)).start()
            logger.warning(f"[UPLOAD {label}] {status} | Txn={post_transid} | Stream={stream}")
            return False

        images = _gather_images(images_dir)
        if not images:
            status = f"No {label.lower()} frames found for stream {stream}"
            threading.Thread(target=send_alert, args=(logger, config.vicki_app, status)).start()
            logger.warning(f"[UPLOAD {label}] {status} | Txn={post_transid}")
            return False
        
        if is_bbox:
            points = np.array(config.pnts[str(stream)], dtype=np.int32)
            points_scaled = (points * 2).astype(np.int32)  # scale ×2
            logger.info(f"[UPLOAD BBOX] Drawing ROI polygon for stream {stream}: {points_scaled.tolist()}")

            for img_name in images:
                img_path = str(images_dir / img_name)
                frame = cv2.imread(img_path)
                if frame is None:
                    continue
                cv2.polylines(frame, [points_scaled], isClosed=True, color=(0, 255, 0), thickness=3)
                cv2.putText(frame, f"CAM {stream} ROI", (30, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                cv2.imwrite(img_path, frame)
                
        frames = [str(images_dir / img) for img in images]
        out_file = video_dir / "media.mp4"

        logger.info(f"[UPLOAD {label}] Creating MP4 with {len(images)} frames | Txn={post_transid} | Stream={stream}")
        clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(frames, fps=10)
        clip.write_videofile(str(out_file), logger=None)
        clip.close()

        # remove raw frames
        shutil.rmtree(images_dir, ignore_errors=True)

        # archive for upload
        cv_upload_dir = Path("cv_upload_dir")
        cv_upload_dir.mkdir(parents=True, exist_ok=True)
        zip_name = f"{post_transid}_{label.lower()}_{stream}.zip"
        archive_path = cv_upload_dir / zip_name
        make_archive(str(base_directory), str(archive_path))

        logger.info(f"[UPLOAD {label}] Uploading video archive → {archive_path.name}")
        success = upload_file_to_dashboard(archive_path, post_transid, logger)

        # clean up
        try:
            archive_path.unlink(missing_ok=True)
        except Exception:
            pass
        shutil.rmtree(base_directory, ignore_errors=True)

        if success:
            logger.info(f"[UPLOAD COMPLETE] {label} Video uploaded successfully | Txn={post_transid} | Stream={stream}")
        else:
            logger.warning(f"[UPLOAD FAILED] {label} Video upload failed | Txn={post_transid} | Stream={stream}")

        return bool(success)

    except Exception:
        err_msg = traceback.format_exc()
        logger.error(f"[UPLOAD EXCEPTION] {label} | Txn={post_transid} | Stream={stream}\n{err_msg}")
        return False

def upload_both_videos(logger, post_transid, is_bbox=False):
    """
    Parallel version:
      - Detects available cam0/cam1
      - Uploads them concurrently (threaded)
      - Returns True if at least one upload succeeds
    """
    label = "BBOX" if is_bbox else "NORMAL"
    logger.info(f"[UPLOAD START - {label}] Transaction={post_transid}")

    stream_paths = {
        "0": (
            Path(f"output_data/bbox_labelled_frames_cam0/{post_transid}/Frames")
            if is_bbox
            else Path(f"output_data/video_frames_cam0/{post_transid}/Frames")
        ),
        "1": (
            Path(f"output_data/bbox_labelled_frames_cam1/{post_transid}/Frames")
            if is_bbox
            else Path(f"output_data/video_frames_cam1/{post_transid}/Frames")
        ),
    }
    
    # Detect available streams
    available_streams = [
        stream for stream, p in stream_paths.items()
        if p.exists() and any(p.glob("*.jpg"))
    ]

    if not available_streams:
        logger.warning(f"[UPLOAD {label}] No frame folders found for txn={post_transid}")
        return False

    logger.info(f"[UPLOAD {label}] Available streams: {available_streams}")

    results = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=len(available_streams)) as executor:
        futures = {
            executor.submit(upload_video, logger, post_transid, stream, is_bbox): stream
            for stream in available_streams
        }

        for future in as_completed(futures):
            stream = futures[future]
            try:
                result = future.result()
                results[stream] = result
                if result:
                    logger.info(f"[UPLOAD COMPLETE] {label} Stream={stream} ✅ Success")
                else:
                    logger.warning(f"[UPLOAD FAILED] {label} Stream={stream} ❌ Failure")
            except Exception as e:
                results[stream] = False
                logger.error(f"[UPLOAD EXCEPTION] {label} Stream={stream}: {e}")

    duration = time.time() - start_time
    logger.info(f"[UPLOAD SUMMARY - {label}] Transaction={post_transid} | Results={results} | Duration={duration:.2f}s")

    return any(results.values())

def upload_both_normal_videos(logger, post_transid):
    return upload_both_videos(logger, post_transid, is_bbox=False)

def upload_both_bbox_videos(logger, post_transid):
    return upload_both_videos(logger, post_transid, is_bbox=True)