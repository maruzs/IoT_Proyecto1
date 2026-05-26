# Spec: ESP32-CAM y Visión Artificial con Node-RED

## Contexto

La ESP32-CAM captura imágenes y las transmite como stream MJPEG o snapshots. La detección de personas NO ocurre en la cámara — se procesa en Node-RED usando TensorFlow.js con el modelo COCO-SSD.

## Requisitos Funcionales

### RF-1: Stream de imagen desde ESP32-CAM

- La ESP32-CAM DEBE servir un stream MJPEG accesible vía HTTP
- La URL del stream DEBE ser configurable (ej: `http://{esp32-ip}/stream`)
- La ESP32-CAM DEBE publicar un evento MQTT al iniciar el stream

### RF-2: Captura de snapshot desde Node-RED

- Node-RED DEBE poder solicitar un snapshot a la ESP32-CAM vía HTTP
- Node-RED DEBE poder capturar frames del stream MJPEG periódicamente
- La captura DEBE ser configurable en frecuencia (ej: cada 5 segundos)

### RF-3: Detección de personas con TensorFlow.js

- Node-RED DEBE usar el nodo `node-red-contrib-tfjs-coco-ssd` para procesar imágenes
- El modelo COCO-SSD DEBE detectar personas (clase "person")
- La detección DEBE retornar confianza (score) y bounding box

### RF-4: Publicación de detección

- Al detectar una persona, Node-RED DEBE publicar en `smarthome/{equipoXX}/camara/evento`:
```json
{
  "equipo": "equipoXX",
  "evento": "persona_detectada",
  "confianza": 0.87,
  "timestamp": "2026-05-26T10:30:00Z"
}
```

### RF-5: Activación de alerta por detección

- Al detectar una persona, el sistema DEBE:
  - Activar indicador visual en el dashboard
  - Publicar una alerta en `smarthome/{equipoXX}/alerta`
  - Opcionalmente: activar buzzer o LED de alerta

### RF-6: Botón de captura manual

- El dashboard DEBE incluir un botón para captura manual de imagen
- Al presionarlo, Node-RED DEBE:
  - Solicitar snapshot a la ESP32-CAM
  - Procesar la imagen con detección
  - Mostrar el resultado en el dashboard

## Requisitos No Funcionales

### RNF-1: Rendimiento de detección

- La detección NO debe bloquear el flujo principal de Node-RED
- Usar cola o buffer para evitar acumulación de imágenes pendientes
- Timeout de detección: máximo 10 segundos por imagen

### RNF-2: Calidad de imagen

- Resolución mínima para detección: 320x240
- Formato: JPEG
- Compresión configurable para balancear calidad vs rendimiento

### RNF-3: Modelo COCO-SSD

- El modelo DEBE cargarse una sola vez al iniciar Node-RED
- No recargar el modelo por cada imagen
- El modelo puede tardar en cargar la primera vez (normal)

## Escenarios de Aceptación

### Escenario 1: Stream activo
```
DADO que la ESP32-CAM está encendida y conectada a WiFi
CUANDO se accede a la URL del stream
ENTONCES se recibe un stream MJPEG válido
Y se publica un evento MQTT "stream_activo"
```

### Escenario 2: Detección de persona
```
DADO que Node-RED está procesando imágenes del stream
CUANDO una persona aparece frente a la cámara
ENTONCES el modelo COCO-SSD detecta la persona con confianza > 0.5
Y se publica un evento "persona_detectada" en MQTT
Y el dashboard muestra indicador de presencia
```

### Escenario 3: Falso positivo manejado
```
DADO que no hay personas frente a la cámara
CUANDO se procesa una imagen
ENTONCES no se publica ningún evento de detección
Y el dashboard NO muestra indicador de presencia
```

### Escenario 4: Captura manual
```
DADO que el dashboard está visible
CUANDO se presiona el botón de captura manual
ENTONCES se solicita un snapshot a la ESP32-CAM
Y la imagen se procesa con detección
Y el resultado se muestra en el dashboard
```

## Criterios de Éxito

1. [ ] Stream MJPEG accesible desde Node-RED
2. [ ] Nodo tfjs-coco-ssd instalado y funcionando en Node-RED
3. [ ] Detección de personas funciona con confianza medible
4. [ ] Evento MQTT se publica al detectar persona
5. [ ] Dashboard muestra imagen y estado de detección
6. [ ] Botón de captura manual funciona
7. [ ] La detección no bloquea otros flujos de Node-RED
