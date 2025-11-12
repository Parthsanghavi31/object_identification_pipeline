from pathlib import Path
import os

WORK_DIR =  "/home/parth/camera-preview-pipeline/failed_uploads"

for item in Path(WORK_DIR).iterdir():
    print(os.path.basename(item))