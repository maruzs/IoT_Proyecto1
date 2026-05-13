## Run mosquitto
docker run -d -p 1883:1883 \
  --name mosquitto \
  --network iot_network \
  -v "$(pwd)/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto


## Run node-RED
docker run -d -p 1880:1880 \
  --name mynodered \
  --network iot_network \
  -v node_red_data:/data \
  nodered/node-red



Categoría,Tópico exacto requerido,Propósito
Sensores,smarthome/equipoXX/temperatura,Envío de datos del SHT30.  
,smarthome/equipoXX/humedad,Envío de datos del SHT30.  
,smarthome/equipoXX/gas,Envío de datos del MQ Sensor.  
,smarthome/equipoXX/sensor_extra,Envío de datos del MAX4466 (Sonido).  
Eventos,smarthome/equipoXX/alerta,Mensajes de texto sobre estados críticos.  
,smarthome/equipoXX/camara/evento,Notificación cuando se detecta una persona.  
Control,smarthome/equipoXX/control/led,Recibir comandos para encender/apagar LEDs.  
,smarthome/equipoXX/control/buzzer,Recibir comandos para el sonido de alerta.  