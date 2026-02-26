#!/bin/bash

set -e  # Exit on any error

# -------------------------------
# Validate Input Parameters
# -------------------------------
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Error: ROI points and machine name are required."
    echo "Usage:"
    echo "./create_roi_config.sh \"[(0,105),(320,52),(320,100),(0,153)]\" Parthedo"
    exit 1
fi

ROI_POINTS="$1"
MACHINE_NAME="$2"

BASE_DIR="$HOME/computer_vision_algorithms/object_identification_pipeline"
UTILS_DIR="$BASE_DIR/utils"
CONFIG_FILE="$UTILS_DIR/configuration_paramters.py"

# Ensure utils directory exists
mkdir -p "$UTILS_DIR"

echo "Creating configuration_paramters.py..."

cat <<EOF > "$CONFIG_FILE"
# ---------------------------------------------
# Auto-generated ROI Configuration File
# ---------------------------------------------

# ROI points dictionary
pnts = {'0' : $ROI_POINTS}

# Machine name
machine_name = "$MACHINE_NAME"

EOF

echo "ROI configuration file created."

# ---------------------------------------------
# Set CV_FLAG = True
# ---------------------------------------------
echo "======================================="
echo "Enabling CV_FLAG..."
echo "======================================="

if [ -f "$CV_CONFIG_FILE" ]; then
    if grep -q "CV_FLAG" "$CV_CONFIG_FILE"; then
        sed -i 's/CV_FLAG *= *.*/CV_FLAG = True/' "$CV_CONFIG_FILE"
    else
        echo "CV_FLAG = True" >> "$CV_CONFIG_FILE"
    fi
    echo "CV_FLAG set to True."
else
    echo "Warning: config.py not found in utils/"
fi

# ---------------------------------------------
# Restart Pipeline
# ---------------------------------------------
echo "======================================="
echo "Restarting Pipeline..."
echo "======================================="

cd "$BASE_DIR"
bash scripts/run.sh

echo "======================================="
echo "🎉 ROI Configured & Pipeline Restarted Successfully!"
echo "======================================="
