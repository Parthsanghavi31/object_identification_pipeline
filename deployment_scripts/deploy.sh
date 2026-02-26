#!/bin/bash

set -e  # Exit on any error

# -------------------------------
# Validate Input Parameters
# -------------------------------
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Error: GitHub username and token are required."
    echo "Usage: ./deploy_all.sh <github_username> <github_token>"
    exit 1
fi

GITHUB_USERNAME="$1"
GITHUB_TOKEN="$2"

BASE_DIR="$HOME/computer_vision_algorithms"

CAMERA_REPO="camera_preview_pipeline_prod"
OBJECT_REPO="object_identification_pipeline"

CAMERA_URL="https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/Parthsanghavi31/${CAMERA_REPO}.git"
OBJECT_URL="https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/Parthsanghavi31/${OBJECT_REPO}.git"

echo "======================================="
echo "Creating base directory..."
echo "======================================="
mkdir -p "$BASE_DIR"
cd "$BASE_DIR"

# ==========================================================
# 1️⃣  Camera Preview Pipeline
# ==========================================================
echo "======================================="
echo "Setting up Camera Preview Pipeline..."
echo "======================================="

if [ -d "$CAMERA_REPO" ]; then
    echo "Existing $CAMERA_REPO found. Deleting..."
    rm -rf "$CAMERA_REPO"
fi

git clone "$CAMERA_URL"
cd "$CAMERA_REPO"

bash scripts/rabbitmq_setup.sh
bash scripts/setup.sh
bash scripts/setup_reboot.sh
bash bin/cv_status.sh

cd "$BASE_DIR"

# ==========================================================
# 2️⃣  Object Identification Pipeline
# ==========================================================
echo "======================================="
echo "Setting up Object Identification Pipeline..."
echo "======================================="

if [ -d "$OBJECT_REPO" ]; then
    echo "Existing $OBJECT_REPO found. Deleting..."
    rm -rf "$OBJECT_REPO"
fi

git clone "$OBJECT_URL"
cd "$OBJECT_REPO"

bash scripts/docker_setup.sh

# Automatically set CV_FLAG = False
CONFIG_FILE="utils/config.py"

if grep -q "CV_FLAG" "$CONFIG_FILE"; then
    sed -i 's/CV_FLAG *= *.*/CV_FLAG = False/' "$CONFIG_FILE"
    echo "CV_FLAG set to False."
else
    echo "Warning: CV_FLAG not found in $CONFIG_FILE"
fi

echo "Running object identification pipeline (first run may take 10–15 minutes)..."
bash scripts/run.sh

echo "======================================="
echo "🎉 Deployment Completed Successfully!"
echo "======================================="
