Aquí tienes el contenido del proyecto condensado en formato Markdown, estructurado de manera clara y directa para su fácil lectura:

# Proyecto Unidad 1: Internet de las Cosas

**SmartHome IoT - Sistema de automatización y monitoreo para una casa inteligente**
- **Institución:** Universidad de Talca, Chile
- **Docente / Contacto:** Ricardo Pérez (riperez@utalca.cl)

## 1. Descripción del Proyecto y Objetivos

El objetivo principal es diseñar e implementar un prototipo funcional de casa inteligente utilizando hardware real, comunicación MQTT, Node-RED y control automático basado en reglas. El sistema busca mejorar la seguridad, el confort y el ahorro energético de un hogar , reaccionando de forma autónoma y mostrando la información en un dashboard local.

### Objetivos específicos:

1. Conectar y programar sensores en una placa Arduino MKR y/o ESP32.
2. Capturar imágenes con una ESP32-CAM y detectar personas en Node-RED (se recomienda TensorFlow.js).
3. Publicar datos en un broker MQTT con una jerarquía de tópicos ordenada.
4. Diseñar un dashboard en Node-RED en tiempo real.
5. Implementar al menos dos estrategias de control automático.
6. Integrar notificaciones externas (Telegram o Email) para eventos críticos.
7. Registrar el histórico de datos en CSV o base de datos.
8. Documentar el desarrollo en un informe técnico.

## 2. Funcionalidades Mínimas Requeridas

### 2.1 Sensores y Publicación MQTT

El nodo debe leer al menos **4 variables físicas** (incluyendo un sensor diferencial) y publicar en formato **JSON**.

**Jerarquía de tópicos:**

- `smarthome/equipoXX/temperatura`
- `smarthome/equipoXX/humedad`
- `smarthome/equipoXX/gas`
- `smarthome/equipoXX/movimiento`
- `smarthome/equipoXX/sensor_extra`
- `smarthome/equipoXX/alerta`
- `smarthome/equipoXX/control/led`
- `smarthome/equipoXX/control/buzzer`
- `smarthome/equipoXX/camara/evento`

### 2.2 ESP32-CAM y Visión Artificial

- La ESP32-CAM transmite imágenes (snapshot o stream MJPEG).
- **Node-RED procesa la imagen** con el nodo `node-red-contrib-tfjs-coco-ssd` para detectar personas (la detección no ocurre en la cámara).
- Al detectar a alguien, se publica un mensaje MQTT y se activa una alerta.

### 2.3 Dashboard en Node-RED

Debe incluir como mínimo:

- Valores en tiempo real de las 4 variables físicas.
- Estado de movimiento y detección de persona (sí/no).
- Estado de alerta e indicador visual del estado general.
- Imagen actual de la cámara y botón para captura manual.
- Botón de control manual para los actuadores.
- Gráfico histórico de temperatura o gas.

### 2.4 Control Automático y Notificaciones

- **Control:** Implementar al menos dos reglas en Node-RED (ej. si temperatura > 30°C, encender LED de alerta y notificar; o si hay gas alto, activar buzzer y capturar imagen).
- **Notificaciones:** Enviar alertas críticas vía **Telegram** (`node-red-contrib-telegrambot`) o **Email** (`node-red-node-email`) con el tipo de evento, valor y timestamp.
- **Historial:** Registro continuo de timestamp, temperatura, humedad, gas y alerta en un archivo `.csv` o base de datos (InfluxDB / SQLite).

## 3. Entregables y Evaluación

### Entregables:

- **a) Prototipo funcional:** Demostración en vivo en la sala.
- **b) Código fuente:** Códigos de las placas, flujo `.json` de Node-RED, todo en un repositorio ordenado.
- **c) Informe técnico:** Documento de 10-15 páginas con arquitectura, diagramas, tópicos y conclusiones.
- **d) Defensa oral:** 15 minutos en total (8 min de demo, 7 min de preguntas) con participación de todos los integrantes.

### Ponderación de la Rúbrica:

|**Criterio**|**Peso**|**Requisito para Puntaje Máximo (4 pts)**|
|---|---|---|
|**Sensores e integración**|20%|4 variables correctamente leídas y publicadas (incluye dif.)|
|**Comunicación MQTT**|15%|Broker activo, tópicos ordenados y mensajes JSON|
|**ESP32-CAM y detección**|15%|Stream activo y detección en Node-RED funcionando|
|**Dashboard Node-RED**|15%|Dashboard completo con variables, gráfico e imagen|
|**Control automático**|10%|2 reglas implementadas y verificables en la demo|
|**Notificaciones y registro**|10%|Notificación externa activa y registro histórico guardando datos|
|**Informe técnico**|10%|Completo, ordenado, con todos los elementos y capturas|
|**Defensa oral**|5%|Todos participan y explican con claridad las decisiones técnicas|

### Sistema de Calificación:

La nota final es en escala de 1.0 a 7.0, siendo **4.0 la nota mínima de aprobación** (equivalente al 50% o 50 puntos). La fórmula de conversión es:

$$Nota = 1,0 + \frac{Puntaje~obtenido}{100} \times 6,0$$