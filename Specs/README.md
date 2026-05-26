# Especificaciones del Proyecto SmartHome IoT

## Índice de Specs

| # | Spec | Descripción | Estado |
|---|------|-------------|--------|
| 00 | [Infraestructura Contenedores](00-infraestructura-contenedores.md) | Docker Compose: Node-RED + Mosquitto en `deploy/` | 📋 Definido |
| 01 | [Comunicación MQTT](01-mqtt-communication.md) | Jerarquía de tópicos, contratos JSON, QoS | 📋 Definido |
| 02 | [Visión Artificial](02-vision-processing.md) | ESP32-CAM + COCO-SSD en Node-RED | 📋 Definido |
| 03 | [Dashboard Node-RED](03-node-red-dashboard.md) | Visualización en tiempo real, controles | 📋 Definido |
| 04 | [Control Automático](04-automation-rules.md) | Reglas de automatización en Node-RED | 📋 Definido |
| 05 | [Notificaciones](05-notifications.md) | Telegram / Email para eventos críticos | 📋 Definido |
| 06 | [Registro Histórico](06-data-logging.md) | Persistencia en CSV o base de datos | 📋 Definido |
| 07 | [Integración del Sistema](07-system-integration.md) | Arquitectura end-to-end, flujos, demo | 📋 Definido |

## Relación con el Proyecto

Estos specs derivan de `Proyecto.md` — Unidad 1: Internet de las Cosas, Universidad de Talca.

### Cobertura de requisitos del proyecto

| Requisito Proyecto | Spec(s) que lo cubre(n) |
|---|---|
| Infraestructura y despliegue | 00 |
| Sensores e integración (20%) | 00, 01, 07 |
| Comunicación MQTT (15%) | 00, 01, 07 |
| ESP32-CAM y detección (15%) | 00, 02, 07 |
| Dashboard Node-RED (15%) | 00, 03, 07 |
| Control automático (10%) | 00, 04, 07 |
| Notificaciones y registro (10%) | 00, 05, 06, 07 |
| Informe técnico (10%) | 07 |
| Defensa oral (5%) | 07 |

### Dependencias entre specs

```
00 (Infra) ──────────────────────────────────► TODOS los demás specs
                                                │
01 (MQTT) ─────────────────────────────────┐   │
                                            │   │
02 (Visión) ──► 03 (Dashboard) ◄───────────┤   │
                 │                          │   │
04 (Auto) ──────►┤                          │   │
                 │                          │   │
05 (Notif) ◄─────┤                          │   │
                 │                          │   │
06 (Logging) ◄───┘                          │   │
                                            │   │
07 (Integración) ◄──────────────────────────┘   │
```

- **00 (Infraestructura)** es la base absoluta: todos los specs requieren Mosquitto y Node-RED corriendo
- **01 (MQTT)** es la base de comunicación: todos los demás specs dependen de la comunicación MQTT
- **03 (Dashboard)** consume datos de MQTT, visión, y controles
- **04 (Automatización)** evalúa datos MQTT y activa actuadores
- **05 (Notificaciones)** se dispara desde las reglas de automatización
- **06 (Logging)** registra datos de sensores y eventos de alerta
- **07 (Integración)** orquesta todos los componentes juntos

## Spec Existente (Archivado)

| Spec | Ubicación | Estado |
|------|-----------|--------|
| Modularización Firmware | `specs.md` (root) | ✅ Archivado |

El spec de modularización de firmware ya fue implementado y archivado. Cubre la reestructuración del código del MKR1000 y ESP32-CAM en módulos separados con `config.h`, `secrets.h`, y archivos `.cpp/.h` en `src/`.
