# Spec 00: Infraestructura de Contenedores — Node-RED + Mosquitto

## Contexto

El sistema SmartHome IoT requiere dos servicios de infraestructura corriendo de forma estable y reproducible para la demo y el desarrollo:

- **Mosquitto**: Broker MQTT que recibe publicaciones del MKR1000/ESP32-CAM y distribuye mensajes a Node-RED
- **Node-RED**: Motor de flujos que consume MQTT, procesa visión, dashboard, automatización, notificaciones y logging

Ambos servicios DEBEN estar contenerizados en una carpeta `deploy/` en la raíz del proyecto, permitiendo levantar toda la infraestructura con un solo comando (`docker compose up`).

Esta spec es la **base de todas las demás**: los specs 01-07 asumen que Mosquitto y Node-RED están corriendo y accesibles.

## Requisitos Funcionales

### RF-1: Estructura de `deploy/`

La carpeta `deploy/` en la raíz del proyecto DEBE contener:

| Archivo | Propósito |
|---|---|
| `deploy/docker-compose.yml` | Orquestación de servicios |
| `deploy/mosquitto/config/mosquitto.conf` | Configuración del broker |
| `deploy/nodered/data/` | Persistencia de flujos y configuración de Node-RED |
| `deploy/README.md` | Instrucciones de uso |

### RF-2: Servicio Mosquitto

El servicio Mosquitto en `docker-compose.yml` DEBE:

- Usar la imagen oficial `eclipse-mosquitto` (versión estable más reciente)
- Exponer el puerto `1883` en el host
- Montar `mosquitto.conf` como volumen de configuración
- Persistir datos en un volumen Docker o bind mount para logs

### RF-3: Servicio Node-RED

El servicio Node-RED en `docker-compose.yml` DEBE:

- Usar la imagen oficial `nodered/node-red` (versión LTS)
- Exponer el puerto `1880` en el host
- Montar `deploy/nodered/data/` como bind mount para persistir flujos (`flows.json`), configuración (`settings.js`) y credenciales
- Depender del servicio Mosquitto (`depends_on: mosquitto`)

### RF-4: Node-RED — Nodos preinstalados

El contenedor de Node-RED DEBE tener instalados los siguientes nodos antes de la demo:

| Nodo | Propósito |
|---|---|
| `node-red-dashboard` | UI del dashboard |
| `node-red-contrib-tfjs-coco-ssd` | Detección de personas (COCO-SSD) |
| `node-red-node-email` | Notificaciones por email |
| `node-red-contrib-telegrambot` | Notificaciones por Telegram |

La instalación DEBE realizarse vía `NODE_RED_OPTIONS` o `package.json` en el volumen de datos, o mediante un Dockerfile derivado que ejecute `npm install` en el build.

### RF-5: Configuración de Mosquitto

El archivo `mosquitto.conf` DEBE:

- Escuchar en el puerto `1883`
- Permitir conexiones sin autenticación (prototipo/demo)
- Habilitar listeners para acceso desde la red local
- Configurar persistencia en disco (`persistence true`)

## Requisitos No Funcionales

### RNF-1: Docker Compose

- Versión mínima de Docker Compose: v2
- Los servicios DEBEN levantarse con `docker compose up -d` desde `deploy/`
- Los servicios DEBEN detenerse con `docker compose down`
- `docker compose down` NO DEBE eliminar los datos persistidos de Node-RED (bind mount)

### RNF-2: Red y conectividad

- Mosquitto DEBE ser accesible desde Node-RED usando el nombre de servicio `mosquitto` como hostname dentro de la red Docker
- Mosquitto DEBE ser accesible desde el host en `localhost:1883` (para el MKR1000/ESP32-CAM en la misma red local)
- Node-RED DEBE ser accesible desde el navegador en `http://localhost:1880`

### RNF-3: Recursos

- Mosquitto: mínimo 64MB RAM
- Node-RED: mínimo 256MB RAM (más si se usa COCO-SSD con TensorFlow.js)
- Los límites DEBEN documentarse en `deploy/README.md`

### RNF-4: Persistencia

- Los flujos de Node-RED (`flows.json`) DEBEN persistir entre reinicios del contenedor
- La configuración de Mosquitto DEBE persistir entre reinicios
- Los datos NO DEBEN perderse al ejecutar `docker compose down && docker compose up`

## Escenarios de Aceptación

### Escenario 1: Levantar infraestructura
```
DADO que Docker y Docker Compose están instalados
CUANDO se ejecuta `docker compose up -d` desde `deploy/`
ENTONCES ambos servicios (mosquitto y nodered) están en estado "running"
Y mosquitto escucha en el puerto 1883 del host
Y nodered escucha en el puerto 1880 del host
```

### Escenario 2: Mosquitto acepta conexiones
```
DADO que los contenedores están corriendo
CUANDO un cliente MQTT se conecta a localhost:1883
ENTONCES la conexión se establece exitosamente
Y el cliente puede publicar y suscribirse a tópicos
```

### Escenario 3: Node-RED se conecta a Mosquitto
```
DADO que los contenedores están corriendo
CUANDO se configura un nodo MQTT en Node-RED con servidor "mosquitto:1883"
ENTONCES Node-RED se conecta al broker exitosamente
Y puede publicar y recibir mensajes
```

### Escenario 4: Persistencia de flujos
```
DADO que se creó un flujo en Node-RED y se desplegó
CUANDO se ejecuta `docker compose down` y luego `docker compose up -d`
ENTONCES el flujo creado sigue presente al abrir Node-RED
Y no se perdió ningún dato de configuración
```

### Escenario 5: Nodos de Node-RED disponibles
```
DADO que los contenedores están corriendo
CUANDO se abre el editor de Node-RED en http://localhost:1880
ENTONCES los nodos node-red-dashboard están disponibles en la paleta
Y los nodos node-red-contrib-tfjs-coco-ssd están disponibles
Y los nodos de email y telegram están disponibles
```

### Escenario 6: Detener sin perder datos
```
DADO que hay flujos guardados en Node-RED
CUANDO se ejecuta `docker compose down`
ENTONCES los archivos en `deploy/nodered/data/` permanecen en el filesystem
Y al volver a levantar, los flujos se restauran
```

## Criterios de Éxito

1. [ ] Carpeta `deploy/` creada con estructura completa
2. [ ] `docker-compose.yml` funcional con mosquitto y nodered
3. [ ] `mosquitto.conf` configurado sin auth, puerto 1883, persistencia
4. [ ] Node-RED accesible en `http://localhost:1880`
5. [ ] Mosquitto accesible en `localhost:1883`
6. [ ] Los 4 nodos requeridos están instalados en Node-RED
7. [ ] Los flujos persisten entre `down` y `up`
8. [ ] `deploy/README.md` con instrucciones de uso y requisitos
9. [ ] `docker compose up -d` levanta ambos servicios sin errores
