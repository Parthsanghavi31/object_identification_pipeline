mkdir -p ~/computer_vision_algorithms/transaction_videos_folders/post_archive
mkdir -p ~/computer_vision_algorithms/transaction_videos_folders/cv_upload_dir
mkdir -p ~/computer_vision_algorithms/transaction_videos_folders/archive
mkdir -p ~/computer_vision_algorithms/transaction_videos_folders/failed_uploads
mkdir -p ~/computer_vision_algorithms/transaction_videos_folders/algo_frames

current_dir=$(pwd)
current_dir=${current_dir%/scripts}

echo "Stopping object_identification containers"
docker stop object_identification 2>/dev/null || true
docker rm -f object_identification 2>/dev/null || true

docker create -it --restart always \
  --user $(id -u):$(id -g) \
  -v ${current_dir}/:/app/ \
  -v ~/computer_vision_algorithms/transaction_videos_folders/:/app/transaction_videos_folders/ \
  -w /app/ \
  --name object_identification \
  parths3/object-identification:1.1.0 \
  bash -c "python3 object_identification_main.py"

docker start object_identification
# echo "Docker auto-start configured."
