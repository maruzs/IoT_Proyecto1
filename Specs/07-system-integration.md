# Spec: Integración del Sistema SmartHome IoT

## Contexto

Este spec define la integración end-to-end de todos los componentes del sistema SmartHome IoT. Cubre la arquitectura general, flujos de datos, y la interacción entre hardware, MQTT, Node-RED y servicios externos.

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SMARTHOME IoT SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     MQTT      ┌──────────────────────────────┐   │
│  │  Arduino     │ ───────────►  │         Node-RED             │   │
│  │  MKR1000     │               │                              │   │
│  │              │               │  ┌────────────────────────┐  │   │
│  │ • SHT30      │ ◄─────────── │  │  Dashboard             │  │   │
│  │ • MQ (Gas)   │   Control     │  │  • Sensores en vivo    │  │   │
│  │ • MAX4466    │   MQTT        │  │  • Cámara              │  │   │
│  │ • LED        │               │  │  • Controles manuales  │  │   │
│  │ • Buzzer     │               │  │  • Gráfico histórico   │  │   │
│  └──────────────┘               │  └────────────────────────┘  │   │
│                                 │                              │   │
│  ┌──────────────┐     HTTP      │  ┌────────────────────────┐  │   │
│  │  ESP32-CAM   │ ───────────►  │  │  Automatización        │  │   │
│  │              │   Stream      │  │  • Regla temp > 30°C   │  │   │
│  │ • Stream     │               │  │  • Regla gas > umbral  │  │   │
│  │ • Snapshot   │               │  │  • Regla detección     │  │   │
│  └──────────────┘               │  └────────────────────────┘  │   │
│                                 │                              │   │
│                                 │  ┌────────────────────────┐  │   │
│                                 │  │  Visión Artificial     │  │   │
│                                 │  │  • COCO-SSD / TF.js    │  │   │
│                                 │  │  • Detección personas  │  │   │
│                                 │  └────────────────────────┘  │   │
│                                 │                              │   │
│                                 │  ┌────────────────────────┐  │   │
│                                 │  │  Notificaciones        │  │   │
│                                 │  │  • Telegram / Email    │  │   │
│                                 │  └────────────────────────┘  │   │
│                                 │                              │   │
│                                 │  ┌────────────────────────┐  │   │
│                                 │  │  Registro Histórico    │  │   │
│                                 │  │  • CSV / SQLite        │  │   │
│                                 │  └────────────────────────┘  │   │
│                                 └──────────────────────────────┘   │
│                                             │                      │
│                                             │ MQTT                 │
│                                  ┌──────────▼──────────┐          │
│                                  │   Broker Mosquitto   │          │
│                                  │   (localhost:1883)   │          │
│                                  └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## Requisitos Funcionales

### RF-1: Flujo de datos end-to-end

```
Sensor → MKR1000 → MQTT → Node-RED → Dashboard / Reglas / Logging / Notificaciones
```

1. Los sensores leen datos cada 2-5 segundos
2. El MKR1000 publica los datos en tópicos MQTT individuales
3. Node-RED suscribe a todos los tópicos y procesa los datos
4. El dashboard muestra los valores en tiempo real
5. Las reglas de automatización evalúan condiciones
6. El histórico registra cada lectura
7. Las notificaciones se envían cuando se activan alertas

### RF-2: Flujo de cámara a detección

```
ESP32-CAM → HTTP Stream → Node-RED → TF.js COCO-SSD → MQTT Evento → Dashboard + Alerta
```

1. La ESP32-CAM sirve un stream MJPEG
2. Node-RED captura frames periódicamente
3. Cada frame se procesa con COCO-SSD
4. Si se detecta persona, se publica evento MQTT
5. El dashboard muestra la detección
6. Se activa alerta y notificación

### RF-3: Flujo de control manual

```
Dashboard Botón → MQTT Control → MKR1000 → Actuador (LED/Buzzer)
```

1. El usuario presiona un botón en el dashboard
2. Node-RED publica en el tópico de control correspondiente
3. El MKR1000 recibe el comando y activa/desactiva el actuador

### RF-4: Flujo de automatización

```
Sensor → MQTT → Node-RED Regla → Actuador + Notificación + Logging
```

1. Un sensor publica un valor que supera un umbral
2. La regla en Node-RED detecta la condición
3. Se activan actuadores (LED, buzzer)
4. Se envía notificación externa
5. Se registra el evento en el histórico

## Requisitos No Funcionales

### RNF-1: Demo funcional

- El sistema completo DEBE funcionar en vivo durante la defensa oral
- Todos los componentes deben estar operativos simultáneamente
- La demo debe durar 8 minutos dentro de los 15 minutos totales

### RNF-2: Repositorio ordenado

El repositorio DEBE tener la siguiente estructura:
```
IoT_Proyecto1/
├── src/
│   ├── mkr1000_firmware/       # Código Arduino MKR1000
│   ├── esp32cam_firmware/      # Código ESP32-CAM
│   └── pruebas/                # Pruebas individuales de sensores
├── node-red/
│   └── flows.json              # Flujo de Node-RED exportado
├── data/
│   └── historico/              # Archivos CSV de registro
├── documentos/
│   └── informe-tecnico.pdf     # Informe de 10-15 páginas
├── Specs/                      # Especificaciones del proyecto
└── README.md                   # Documentación del proyecto
```

### RNF-3: Informe técnico

El informe DEBE incluir:
- Arquitectura del sistema con diagramas
- Descripción de tópicos MQTT y jerarquía
- Capturas del dashboard funcionando
- Descripción de reglas de automatización
- Conclusiones y lecciones aprendidas
- 10-15 páginas de extensión

### RNF-4: Defensa oral

- 15 minutos totales: 8 min demo + 7 min preguntas
- Todos los integrantes deben participar
- Explicar decisiones técnicas con claridad

## Escenarios de Aceptación

### Escenario 1: Sistema completo operativo
```
DADO que todos los componentes están configurados
CUANDO se inicia el sistema
ENTONCES el MKR1000 publica datos de sensores
Y la ESP32-CAM sirve el stream
Y Node-RED muestra el dashboard
Y el histórico registra datos
Y las reglas de automatización están activas
```

### Escenario 2: Demo exitosa
```
DADO que el sistema está corriendo
CUANDO se realiza la demo en vivo
ENTONCES se muestran las 4 variables en el dashboard
Y se demuestra al menos 1 regla de automatización
Y se muestra la detección de persona
Y se muestra una notificación externa
Y se muestra el archivo histórico con datos
```

### Escenario 3: Repositorio completo
```
DADO que el proyecto está terminado
CUANDO se revisa el repositorio
ENTONCES contiene el código de ambos firmwares
Y el archivo flows.json de Node-RED
Y los archivos CSV del histórico
Y el informe técnico en PDF
Y la documentación del proyecto
```

## Criterios de Éxito

1. [ ] Sistema completo funcionando end-to-end
2. [ ] Demo funcional con todos los componentes
3. [ ] Repositorio ordenado con toda la estructura
4. [ ] Informe técnico de 10-15 páginas completado
5. [ ] Todos los integrantes pueden explicar el sistema
6. [ ] Las 4 variables físicas se leen y publican correctamente
7. [ ] La detección de persona funciona en Node-RED
8. [ ] Al menos 2 reglas de automatización operativas
9. [ ] Notificaciones externas funcionando
10. [ ] Registro histórico con datos acumulados
