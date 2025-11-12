#sudo apt-get update -y
#sudo apt-get upgrade -y
sudo apt-get install docker.io -y
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
