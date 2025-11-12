is_rabbitmq_installed() {
    dpkg -l | grep -q rabbitmq-server
}
if is_rabbitmq_installed; then
    echo "RabbitMQ is already installed."
    rabbitmq-plugins enable rabbitmq_management
    service rabbitmq-server start
    if rabbitmqctl list_users | grep -q "^nano"; then
        echo "User 'nano' already exists in RabbitMQ."
    else
        echo "Creating 'nano' user in RabbitMQ..."
        rabbitmqctl add_user nano nano
        rabbitmqctl set_permissions -p / nano ".*" ".*" ".*"
    fi
else
    echo "Installing RabbitMQ..."
    apt update -y
    apt upgrade -y
    apt install rabbitmq-server -y
    rabbitmq-plugins enable rabbitmq_management
    service rabbitmq-server start

    echo "Creating 'nano' user in RabbitMQ..."
    rabbitmqctl add_user nano nano
    rabbitmqctl set_permissions -p / nano ".*" ".*" ".*"
    service rabbitmq-server restart
fi
