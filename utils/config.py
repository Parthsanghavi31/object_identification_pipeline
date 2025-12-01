import os
import numpy as np

CV_FLAG = False

vicki_app = "http://192.168.1.140:8085/tsv/flashapi"

# ==============================
# 📁 general paths & logging
# ==============================
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
base_folder_path = os.path.join(repo_root, "transaction_videos_folders")

# Frames saved during algorithm processing 
algo_frames = os.path.join("transaction_videos_folders", "algo_frames")

# ==============================
# 🧠 model & product config
# ==============================
model_path = {
    "0": "weights_mobilevit/v3",
    "1": "weights_mobilevit/v3"
}
confidence_threshold = 0.92 # originally at 98%

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
