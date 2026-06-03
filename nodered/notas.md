Flujo de Trabajo para Programar Node-RED mediante Código
Para editar flows.json en el repositorio y verlo reflejado en tu Docker:

Crearemos el archivo nodered/flows.json en este repositorio.
Sincronización: Cada vez que hagamos un cambio en nodered/flows.json, usaremos el siguiente comando para copiarlo al contenedor y reiniciar Node-RED:
bash

docker cp nodered/flows.json mynodered:/data/flows.json && docker restart mynodered
(También se puede recargar usando la API de Node-RED sin reiniciar el contenedor, lo cual implementaremos para que sea instantáneo).