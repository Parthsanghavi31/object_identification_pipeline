apt-get install -y git libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev  gstreamer1.0-plugins-good libavcodec-dev libavformat-dev libavutil-dev libswscale-dev build-essential
export OPENCV_VER="86"
git clone --branch ${OPENCV_VER} --depth 1 --recurse-submodules --shallow-submodules https://github.com/opencv/opencv-python.git opencv-python-${OPENCV_VER}
export ENABLE_CONTRIB=0
export ENABLE_HEADLESS=0
export CMAKE_ARGS="-DWITH_GSTREAMER=ON -DWITH_FFMPEG=ON"
cd opencv-python-${OPENCV_VER} 
MAKEFLAGS="-j8" python3 -m pip wheel . --verbose
python3 -m pip install --no-cache-dir --force-reinstall opencv_python*.whl
