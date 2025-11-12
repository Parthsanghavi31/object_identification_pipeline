import os
import numpy as np

# ==============================
# 📁 general paths & logging
# ==============================
base_path = os.getcwd() + "/"
log_folder = "logs"
log_file = "camera-preview.log"
version_file_path = "version.txt"

# ==============================
# 📷 camera settings
# ==============================
camera_resolution = (640, 480)   # for arducam
resize_images = (640, 480)
cameras_to_flip = [2]  # e.g. [0, 1] if you want to flip some streams

# ==============================
# 🌐 network & queue config
# ==============================
pika_name = "nano"
vicki_app = "http://192.168.1.140:8085/tsv/flashapi"
Queue = "cvRequest"
local_queue = "cvCPP"
message_timeout = 3600  # seconds

# ==============================
# ⏱️ timing configs
# ==============================
save_frame = 2  # save every alternate frame
pipeline_status_interval = 10800  # 3 hours
minutes_to_end_transcation = 300
warning_message_time = 180
delete_logs_days = 30
no_camera_alert_time = "last_alert.txt"

# ==============================
# 🧠 model & product config
# ==============================
model_path = {
    "0": "weights/checkpoint-1098-best",
    "1": "weights/checkpoint-1098-best"
}
["Quest-chips Chili lime", "Quest Chips - Loaded Taco", "Legendary Protein Chip - Ranch"]
cv_products = {
    "0": [
        "Quest-chips Chili lime",
        "Quest Chips - Loaded Taco",
        "Legendary Protein Chip - Ranch"
    ],
    "1": [
        "pepsi 500ml",
        "diet pepsi 500ml",
        "mountain dew 500ml"
    ]
}

no_product_label = 'no_product'

# ==============================
# 🟩 region / roi config
# ==============================
tray_region = {
    "0": None,
    "1": None,
    "2": {  # camera 1 (e.g., right camera)
        "tray_1": [
            (626.0, 263.38), (626.0, 124.0), (9.0, 116.0),
            (7.0, 123.0), (4.67, 205.25), (138.0, 218.0),
            (301.0, 215.0), (445.0, 229.0), (507.0, 235.0),
            (569.0, 248.0)
        ],
        "tray_2": [
            (4.67, 205.25), (3.0, 264.0), (626.0, 294.0),
            (626.0, 263.38), (569.0, 248.0), (507.0, 235.0),
            (445.0, 229.0), (301.0, 215.0), (138.0, 218.0)
        ]
    }
}

lr_section = {
    "0": None,
    "1": None,
    "2": {
        "left_section": [
            (5.0, 125.0), (10.0, 269.0), (301.97, 278.43),
            (333.0, 202.0), (339.79, 124.29), (2.0, 120.0)
        ],
        "right_section": [
            (301.97, 278.43), (629.0, 289.0), (631.0, 128.0),
            (339.79, 124.29), (333.0, 202.0)
        ]
    }
}

# ==============================
# 📍 perspective points (for calibration)
# ==============================
cam_for_cv = ['0', '1']

pnts = {
    "0": [(0, 113), (320, 96), (320, 61), (0, 78)],   # Fisheye cam
    "1": [(0, 48), (320, 39), (320, 111), (0, 120)]    # Non-fisheye cam
}

bbox_coordinates = {
    "0": {
        "BBOX_SCALE": 2,
        "BBOX_OFFSET_TRAY_1": [-45, -25, 45, 75],
        "BBOX_OFFSETS_TRAY_2": [-50, -25, 60, 55],
        "BBOX_OFFSETS_DEFAULT": [-50, -25, 60, 55],
        "BBOX_OFFSETS_OPTICAL_FLOW": [-60, -25, 50, 55]
    },
    "1": {
        "BBOX_SCALE": 2,
        "BBOX_OFFSETS_TRAY_1": [-45, -25, 45, 75],
        "BBOX_OFFSETS_TRAY_2": [-50, -25, 60, 55],
        "BBOX_OFFSETS_DEFAULT": [-50, -25, 60, 55],
        "BBOX_OFFSETS_OPTICAL_FLOW": [-60, -25, 50, 55]
    }
}
