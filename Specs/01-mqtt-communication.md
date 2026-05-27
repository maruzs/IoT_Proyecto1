# Spec: Comunicación MQTT — Jerarquía de Tópicos y Contratos de Mensajes

## Contexto

El sistema SmartHome IoT utiliza un broker MQTT (Mosquitto) como columna vertebral de comunicación entre:
- **Arduino MKR1000**: publica lecturas de sensores y recibe comandos de actuadores
- **ESP32-CAM**: publica eventos de cámara y recibe comandos de captura
- **Node-RED**: suscribe a todos los tópicos para dashboard, automatización y notificaciones

El `equipoXX` es un placeholder que cada equipo reemplaza con su identificador (ej: `equipo01`).

## Requisitos Funcionales

### RF-1: Jerarquía de tópicos

El sistema DEBE usar la siguiente jerarquía de tópicos bajo el prefijo `smarthome/{equipoXX}/`:

| Tópico | Dirección | Descripción |
|---|---|---|
| `smarthome/{equipoXX}/temperatura` | Publish | Lectura de temperatura (°C) |
| `smarthome/{equipoXX}/humedad` | Publish | Lectura de humedad (%) |
| `smarthome/{equipoXX}/gas` | Publish | Lectura de gas (ppm o valor analógico) |
| `smarthome/{equipoXX}/movimiento` | Publish | Estado de movimiento (bool o JSON) |
| `smarthome/{equipoXX}/sensor_extra` | Publish | Lectura del sensor diferencial (sonido MAX4466) |
| `smarthome/{equipoXX}/alerta` | Publish | Evento de alerta cuando se superan umbrales |
| `smarthome/{equipoXX}/control/led` | Subscribe | Comando remoto para LED (ON/OFF) |
| `smarthome/{equipoXX}/control/buzzer` | Subscribe | Comando remoto para buzzer (ON/OFF) |
| `smarthome/{equipoXX}/camara/evento` | Publish | Evento de cámara (stream activo, detección, etc.) |

### RF-2: Formato JSON en publicaciones

Todos los mensajes publicados DEBEN tener formato JSON válido.

**Mensaje de sensores individuales** (ej: temperatura):
```json
{
  "equipo": "equipoXX",
  "valor": 25.3,
  "unidad": "°C",
  "timestamp": "2026-05-26T10:30:00Z"
}
```

**Mensaje de alerta**:
```json
{
  "equipo": "equipoXX",
  "tipo": "gas_alto",
  "valor": 520,
  "umbral": 400,
  "mensaje": "Gas detectado por encima del umbral",
  "timestamp": "2026-05-26T10:30:00Z"
}
```

**Mensaje de evento de cámara**:
```json
{
  "equipo": "equipoXX",
  "evento": "stream_activo",
  "timestamp": "2026-05-26T10:30:00Z"
}
```

**Mensaje de detección de persona**:
```json
{
  "equipo": "equipoXX",
  "evento": "persona_detectada",
  "confianza": 0.87,
  "timestamp": "2026-05-26T10:30:00Z"
}
```

### RF-3: Comandos de control

Los tópicos de control DEBEN aceptar payloads simples:
- `"ON"` para activar
- `"OFF"` para desactivar

### RF-4: QoS y retención

- Publicaciones de sensores: QoS 0 (fire-and-forget, alta frecuencia)
- Publicaciones de alerta: QoS 1 (al menos una vez)
- Tópicos de control: QoS 1, con retención (retain = true) para que el estado persista

## Requisitos No Funcionales

### RNF-1: Broker Mosquitto

- El broker DEBE estar corriendo localmente o en red accesible
- Puerto por defecto: 1883 (sin TLS para prototipo)
- Sin autenticación para prototipo (aceptable para demo)

### RNF-2: Consistencia de equipoID

- El `equipoXX` DEBE ser consistente en TODOS los tópicos
- Un solo punto de definición en el firmware (config.h)
- Node-RED DEBE usar wildcards `smarthome/+/` para suscripción genérica

### RNF-3: Frecuencia de publicación

- Sensores: cada 2-5 segundos
- Alertas: solo cuando cambia el estado (no repetitivas)
- Eventos de cámara: por evento (no periódicos)

## Escenarios de Aceptación

### Escenario 1: Publicación periódica de sensores
```
DADO que el MKR1000 está conectado al broker MQTT
CUANDO pasan 2 segundos
ENTONCES se publica un mensaje JSON válido en smarthome/equipoXX/temperatura
Y el mensaje contiene valor, unidad y timestamp
```

### Escenario 2: Recepción de comando de control
```
DADO que el MKR1000 está suscrito a smarthome/equipoXX/control/led
CUANDO se publica "ON" en ese tópico
ENTONCES el LED se enciende
```

### Escenario 3: Alerta por umbral superado
```
DADO que el umbral de gas es 400
CUANDO la lectura de gas supera 400
ENTONCES se publica un mensaje en smarthome/equipoXX/alerta
Y el mensaje incluye tipo, valor, umbral y timestamp
```

### Escenario 4: Consistencia de equipoID
```
DADO que el equipoID está definido como "equipo05"
CUANDO se publican mensajes en cualquier tópico
ENTONCES todos los tópicos usan "equipo05" como prefijo
Y no hay ningún tópico con "equipoXX" hardcodeado
```

## Criterios de Éxito

1. [ ] Broker Mosquitto corriendo y accesible
2. [ ] Todos los tópicos de la jerarquía están implementados
3. [ ] Los mensajes JSON son válidos y parseables
4. [ ] El equipoID es consistente en todos los tópicos
5. [ ] Los comandos de control funcionan bidireccionalmente
6. [ ] Las alertas se publican solo cuando cambia el estado
