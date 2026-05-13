❯ docker run -d -p 1883:1883 \
  --name mosquitto \
  --network iot_network \
  -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto
bbf37a63a4f530ab8e93a899072de37234e788f86fa3f51bb188ebed4d5b96d1

~
❯ docker run -d -p 1880:1880 \
  --name mynodered \
  --network iot_network \
  -v node_red_data:/data \
  nodered/node-red
3b03ac6763f2e6383baebd2b3ec95c38c97fd42712c4dee093b9e530bf1bfba2

~
❯ docker ps
CONTAINER ID   IMAGE               COMMAND                  CREATED              STATUS                        PORTS                                         NAMES
3b03ac6763f2   nodered/node-red    "./entrypoint.sh"        About a minute ago   Up About a minute (healthy)   0.0.0.0:1880->1880/tcp, [::]:1880->1880/tcp   mynodered
bbf37a63a4f5   eclipse-mosquitto   "/docker-entrypoint.…"   About a minute ago   Up About a minute             0.0.0.0:1883->1883/tcp, [::]:1883->1883/tcp   mosquitto