# Node-RED SmartHome IoT - Configuración y Flujo de Trabajo

Este directorio contiene los flujos y scripts necesarios para programar y sincronizar Node-RED de manera local desde el repositorio de Git, sin perder cambios y permitiendo a todos los integrantes del grupo trabajar cómodamente desde su propio editor de código.

---

## 1. Requisitos Previos en Docker

Para que los flujos carguen sin errores, el contenedor Docker de Node-RED necesita tener instalados los nodos del Dashboard y de Telegram.

Ejecuta el siguiente comando en tu terminal para instalar las dependencias directamente dentro del contenedor:

```bash
docker exec -u 0 mynodered npm install --prefix /data node-red-dashboard node-red-contrib-telegrambot
```

> [!IMPORTANT]
> **Reinicio Obligatorio:** Después de instalar nuevos nodos por primera vez, debes reiniciar el contenedor para que Node-RED registre los nuevos tipos de nodos:
> ```bash
> docker restart mynodered
> ```

---

## 2. Flujo de Trabajo y Sincronización

Los flujos de Node-RED se definen localmente en el archivo [flows.json](file:///home/maruzs/Desktop/IoT_Proyecto1/nodered/flows.json). Para que cualquier cambio que realices se aplique a tu contenedor Docker de inmediato sin tener que reiniciar el contenedor, hemos creado un script automatizado.

Cada vez que edites `flows.json`, ejecuta en tu terminal:

```bash
./nodered/sync.sh
```

### ¿Qué hace el script `sync.sh`?
1. Copia el archivo `flows.json` local al volumen del contenedor en `/data/flows.json`.
2. Llama al API Admin de Node-RED para **recargar instantáneamente** los flujos sin necesidad de reiniciar el Docker (tarda < 2 segundos).

---

## 3. Acceso a las Interfaces

Una vez sincronizado el flujo:
* **Editor de Node-RED (Visual/UI):** [http://localhost:1880/](http://localhost:1880/)
* **Dashboard de SmartHome (Panel de control):** [http://localhost:1880/ui](http://localhost:1880/ui)

---

## 4. Detalles del Flujo Implementado

* **Broker MQTT:** Se conecta automáticamente al contenedor `mosquitto` en el puerto `1883` usando la red interna de Docker `iot_network`.
* **Suscripción de datos:** Suscrito a `smarthome/+/datos` para parsear lecturas de temperatura, humedad, gas y sonido en tiempo real.
* **Registro Histórico:** Los datos recibidos se guardan de forma continua con su timestamp en `/data/historial.csv` dentro de la persistencia del contenedor.
* **Control Manual:** Dispone de botones en el Dashboard para interactuar con la cámara y mandar comandos `ON/OFF` a los actuadores (LED y Buzzer) mediante los tópicos correspondientes.
* **Reglas Automáticas:** Si la temperatura supera los 30°C o el gas supera los 400 ppm, se activa automáticamente la alarma local (LED y Buzzer) y se prepara el envío del mensaje de alerta.
