current_dir=$(pwd)
current_dir=${current_dir%/scripts}

# sudo systemctl stop rabbitmq-server.service
# sudo systemctl disable rabbitmq-server.service
# sudo systemctl stop camera-preview.service
# sudo systemctl disable camera-preview.service

echo "Stopping Watcher containers"
# docker stop camera-preview-pipeline
docker stop watcher
docker rm -f watcher 2>/dev/null || true

# docker create -it --restart always \
# --user $(id -u):$(id -g) \
# $(for dev in /dev/video[0-31]; do echo --device=$dev; done) \
# -p 5672:5672 -p 15672:15672 \
# -v ${current_dir}/:/app/ \
# -v ${current_dir}/post_archive:/app/post_archive \
# -v ${current_dir}/archive:/app/archive \
# -w /app/ \
# --name camera-preview-pipeline \
# camera-preview-cv-rpi4b:1.1.0 \
# bash -c "bash /scripts/rabbitmq_setup.sh && python3 main.py"

docker start camera-preview-pipeline

docker create -it --restart always \
--user $(id -u):$(id -g) \
-v ${current_dir}/:/app/ \
-v ${current_dir}/post_archive:/app/post_archive \
-w /app/ \
--name watcher \
parths3/object-identification:1.1.0 \
bash -c "python3 watcher_v3.py"

docker start watcher

# #Creating container for Upload service
# docker create -it \
# --user $(id -u):$(id -g) \
# -v ${current_dir}/:/app/ \
# -w /app/ \
# --name camera-preview-reupload-pipeline \
# camera-preview-cv-rpi4b:1.1.0 \
# bash -c "python3 upload_module.py"

echo "Setting up Docker auto-start at 2:10 AM..."
temp_cron=$(mktemp)
sudo crontab -l > "$temp_cron" 2>/dev/null
docker_start_job="10 2 * * * /usr/bin/docker start camera-preview-reupload-pipeline"
if ! grep -Fxq "$docker_start_job" "$temp_cron"; then
    echo "$docker_start_job" >> "$temp_cron"
fi
sudo crontab "$temp_cron"
rm "$temp_cron"

# Restart cron service
sudo systemctl restart cron
echo "Docker auto-start configured."
