# SDD Proposal: Spec 00 — Infraestructura de Contenedores

## Intent

Implementar la infraestructura base de contenedores Docker (Mosquitto + Node-RED) que es **prerrequisito** para todos los specs 01-07 del proyecto SmartHome IoT.

## Scope

Crear carpeta `deploy/` en la raíz del proyecto con:

| Archivo | Propósito |
|---|---|
| `deploy/docker-compose.yml` | Orquestación de mosquitto + nodered |
| `deploy/mosquitto/config/mosquitto.conf` | Config del broker MQTT (sin auth, puerto 1883, persistencia) |
| `deploy/nodered/data/` | Bind mount para persistencia de flujos Node-RED |
| `deploy/README.md` | Instrucciones de uso, requisitos, troubleshooting |

## Approach

- **Imágenes oficiales**: `eclipse-mosquitto` (latest stable) + `nodered/node-red` (LTS)
- **Persistencia**: Bind mounts para Node-RED (`deploy/nodered/data/`) + volumen Docker para Mosquitto
- **Nodos preinstalados**: Dockerfile derivado de Node-RED que ejecute `npm install` de los 4 nodos requeridos (dashboard, tfjs-coco-ssd, email, telegrambot)
- **Red**: Docker network interna para comunicación entre servicios; ports 1883/1880 expuestos al host
- **Sin autenticación**: Configuración de Mosquitto sin auth para prototipo/demo

## Impact

- **Nuevos archivos**: Solo `deploy/` (4 archivos + directorios)
- **Sin modificaciones**: No se toca código existente (src/, firmware, etc.)
- **Sin dependencias**: No requiere cambios en otras partes del proyecto

## Risk

**BAJO** — Infraestructura aislada, sin impacto en firmware ni en código existente. Rollback = `rm -rf deploy/`.

## Dependencies

- **Pre-requisito**: Es la base de specs 01-07. Ningún otro spec puede implementarse sin esto.
- **No depende de**: Ningún spec previo.

## Acceptance Criteria (del spec)

1. `deploy/` creada con estructura completa
2. `docker-compose.yml` funcional
3. `mosquitto.conf` sin auth, puerto 1883, persistencia
4. Node-RED accesible en `http://localhost:1880`
5. Mosquitto accesible en `localhost:1883`
6. 4 nodos requeridos instalados
7. Flujos persisten entre `down`/`up`
8. `deploy/README.md` con instrucciones
9. `docker compose up -d` levanta sin errores
