# Camera-preview-pipeline
The Camera Preview Pipeline monitor the retail machine's transactions, detecting when door is opened and locked while recording transaction details. Once an OrderSettled message is received, the recorded transaction is finalized and uploaded to the designated endpoint

# 1. Setup the Machine
## Step 1.1 Install docker
Run the following command
```
bash scripts/docker_setup.sh
```
## Step 1.2 Setup the reboot
Run the following command
```
bash scripts/setup_reboot.sh
```

# 2 Setup the Pipeline
## Step 2.1 Build the docker image
Run the following command
```
sudo docker build -t camera:1.0.0 .
```
or download the pre-build image for docker hub using the following command
```
docker login -u mo190
password : dckr_pat_dYsm-xanlDnuemTQD5YyUOROFqw
docker pull mo190/camera-preview-pipeline:latest
```
Update the docker image name in scripts/run.sh

# 3 Start the Pipeline
## Step 3.1 Start the docker containers
Run the following command
```
sudo bash sripts/run.sh
```

# 4. Check the status of the pipeline
Run the following command
```
bash bin/cv_status.sh
```
NOTE : You can run the other scripts inside the bin folder to stop, restart, disable, enable the pipeline

