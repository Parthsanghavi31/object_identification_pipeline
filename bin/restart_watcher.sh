echo "Stopping object_identification services"
sudo docker stop object_identification
echo "Killed all object_identification services"
sleep 3
echo " Starting object_identification services"
sudo docker start object_identification
echo "Finished restart procedure"
