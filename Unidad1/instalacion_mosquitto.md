Instalación de Mosquitto y Node-RED en Windows

1. Instalar Docker Desktop

1.1. Descargar Docker Desktop desde la página oficial:
https://www.docker.com/products/docker-desktop/

1.2. Instalar Docker Desktop aceptando la opción de WSL 2.

1.3. Reiniciar el computador si lo solicita.

1.4. Abrir Docker Desktop y esperar a que quede iniciado.

2. Crear una carpeta de trabajo

Abrir PowerShell y ejecutar:

mkdir C:\iot-docker
cd C:\iot-docker

3. Crear la red de Docker

Ejecutar en PowerShell:

docker network create iot_network
a700063695749f76dbe419cd56238d9ff7861205df9494f4df1c13aaf86bf0af
4. Crear carpeta de configuración para Mosquitto

Ejecutar en PowerShell:

mkdir mosquitto
mkdir mosquitto\config
notepad mosquitto\config\mosquitto.conf

Dentro del archivo pegar:

listener 1883 0.0.0.0
allow_anonymous true

Guardar y cerrar el archivo.

5. Instalar y ejecutar Mosquitto

Ejecutar en PowerShell:

docker run -d -p 1883:1883 `
  --name mosquitto `
  --network iot_network `
  -v "$PWD\mosquitto\config:/mosquitto/config" `
  eclipse-mosquitto

6. Instalar y ejecutar Node-RED

Ejecutar en PowerShell:

docker run -d -p 1880:1880 `
  --name mynodered `
  --network iot_network `
  -v node_red_data:/data `
  nodered/node-red

7. Abrir Node-RED

Abrir el navegador e ingresar a:

http://localhost:1880

8. Configurar MQTT en Node-RED

En el nodo MQTT de Node-RED usar:

Servidor: mosquitto
Puerto: 1883

9. Verificar que ambos contenedores estén activos

Ejecutar en PowerShell:

docker ps

Deben aparecer los contenedores:

mosquitto
mynodered

