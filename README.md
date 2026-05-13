# Inventario

## Inventario Placas/ Sensores

| Componente     | Nombre           |
| -------------- | ---------------- |
| Placa Port.    | Arduino MKR 1000 |
| S. Gas         | MQ Sensor        |
| Camara         | ESP 32-CAM       |
| S. Temperatura | SHT30            |
| S. Humedad     | SHT30            |
| Microfono      | MAX4466          |

## Inventario Componentes

| Componente     | Cantidad |
| -------------- | -------- |
| Potenciometros | 4        |
| Led Amarillo   | 7        |
| Led Verde      | 9        |
| Led Rojos      | 10       |
| Led Azules     | 4        |


---
# CHECKLIST DEL PROYECTO

## 1. Hardware y Sensores (20% de la nota)
- [ ] Lectura de 4 variables físicas: Configurar y leer datos del SHT30 (Temperatura), SHT30 (Humedad), MQ Sensor (Gas) y el MAX4466 (Sonido/Diferencial).
- [ ] Conexión de Placas: Programar la Arduino MKR 1000 o ESP32 para gestionar los sensores
- [ ] Actuadores: Instalar y cablear los LEDs y un Buzzer para las respuestas automáticas.
- [ ] Sensor Diferencial: Integrar correctamente el sensor extra (Micrófono) en el sistema.

## 2. Comunicación MQTT (15% de la nota)
- [ ] Jerarquía de Tópicos: Configurar los mensajes bajo la ruta smarthome/equipoXX/ (temperatura, humedad, gas, movimiento, sensor_extra, alerta, control/led, control/buzzer, camara/evento).
- [ ] Formato JSON: Asegurar que todos los mensajes enviados al broker tengan la estructura de objeto JSON requerida.
- [ ] Broker Activo: Verificar la conexión estable entre las placas y el broker MQTT.

## 3. ESP32-CAM y Visión Artificial (15% de la nota)
- [x]Transmisión de Imagen: Configurar la ESP32-CAM para enviar snapshots o stream MJPEG.
- [ ] Procesamiento en Node-RED: Implementar el nodo node-red-contrib-tfjs-coco-ssd para la detección de personas.
- [ ] Alerta de Detección: Publicar un mensaje MQTT y activar indicador en el dashboard al detectar un humano.
- [ ] Visualización: Mostrar la imagen capturada en tiempo real dentro del dashboard.

## 4. Dashboard en Node-RED (15% de la nota)
- [ ] Visualización de Variables: Indicadores para temperatura, humedad, gas y sensor diferencial.
- [ ] Estado del Sistema: Indicadores para presencia de personas, movimiento y estado de alertas.
- [ ] Controles Manuales: Botones para activar/desactivar actuadores y solicitar captura de imagen manual.
- [ ] Gráfico Histórico: Gráfica de línea para al menos una variable física (ej. temperatura o gas).

## 5. Lógica y Funciones Avanzadas (20% de la nota)
- [ ] Control Automático (Mínimo 2 reglas): Implementar lógica autónoma en Node-RED basada en umbrales (ej. si Gas > X, activar Buzzer).
- [ ] Notificaciones Externas: Configurar el envío de alertas vía Telegram o Email ante eventos críticos.
- [ ] Registro Histórico: Guardar datos (timestamp, variables y alertas) en un archivo CSV o base de datos (SQLite/InfluxDB).

## 6. Entregables Finales (15% de la nota)
- [ ] Código Fuente: Carpeta con el código de Arduino MKR, ESP32-CAM y el archivo .json del flujo de Node-RED.
- [ ] Informe Técnico: Documento de 10-15 páginas con arquitectura, tópicos, capturas del dashboard y conclusiones.
- [ ] Preparación de Defensa: Presentación y demo funcional de 15 minutos.
