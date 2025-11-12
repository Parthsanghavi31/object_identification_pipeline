echo "Stopping watcher services"
sudo docker stop watcher
echo "Killed all watcher services"
sleep 3
echo " Starting watcher services"
sudo docker start watcher
echo "Finished restart procedure"
