# Spec: Modularización Firmware IoT — MKR1000 + ESP32-CAM

## Contexto

El proyecto IoT Smart Home tiene dos dispositivos físicos separados:
- **Arduino MKR1000**: gestiona sensores (SHT30, MQ, MAX4466) y actuadores (LEDs, buzzer)
- **ESP32-CAM**: streaming MJPEG y snapshots

Ambos dispositivos deben publicar datos al mismo broker MQTT bajo una jerarquía de tópicos compartida. El código actual tiene todo la lógica del MKR1000 en un solo archivo de 81 líneas con credenciales hardcodeadas, umbrales quemados, y un bug de `equipoXX` inconsistente entre variables y tópicos.

## Problema

El firmware actual no es mantenible ni escalable:
1. Todo el código del MKR1000 está en un solo archivo `.ino` monolítico
2. Las credenciales WiFi y MQTT están commiteadas en el repositorio
3. El `equipoID` se usa como variable en algunos lugares pero hardcodeado como string en otros (bug real en `client.subscribe("smarthome/equipoXX/control/led")`)
4. Los umbrales de alerta están quemados en la lógica del loop
5. No hay validación real de errores de sensores — datos inválidos se publican silenciosamente
6. El ESP32-CAM tiene credenciales WiFi expuestas y no tiene integración MQTT
7. Agregar un nuevo sensor o cambiar un pin requiere modificar el archivo principal

## Requisitos Funcionales

### RF-1: MKR1000 — Lectura modular de sensores
- Cada sensor (SHT30, MQ, MAX4466) debe tener su propia función de lectura independiente
- Las lecturas deben incluir un flag de validez (no publicar datos de sensores que fallaron)
- El struct `SensorData` debe agrupar todas las lecturas juntas

### RF-2: MKR1000 — Publicación MQTT con datos válidos
- Publicar JSON al tópico `smarthome/{equipoID}/datos` cada 2 segundos
- El JSON debe incluir: equipo, temperatura, humedad, gas, sensor_extra, alerta
- Si un sensor falla, su valor debe ser `null` en el JSON (no 0.0)
- El campo `alerta` solo debe aparecer cuando hay una condición anómala

### RF-3: MKR1000 — Suscripción a control
- Suscribirse a `smarthome/{equipoID}/control/led` y `smarthome/{equipoID}/control/buzzer`
- El `equipoID` debe usarse consistentemente en TODOS los tópicos (no hardcodeado)
- Los callbacks de MQTT deben activar/desactivar los actuadores correspondientes

### RF-4: MKR1000 — Alertas automáticas locales
- Evaluar umbrales de gas, temperatura y sonido contra constantes configurables
- Activar LED de alerta cuando se superen los umbrales
- Los umbrales deben estar definidos en un solo archivo de configuración

### RF-5: ESP32-CAM — Integración MQTT
- El ESP32-CAM debe conectarse al broker MQTT además de servir el stream HTTP
- Publicar evento `smarthome/{equipoID}/camara/evento` cuando se inicie el stream
- Suscribirse a `smarthome/{equipoID}/camara/control` para recibir comandos (ej: captura manual)
- Las credenciales WiFi deben estar en un archivo separado del código

### RF-6: Jerarquía de tópicos consistente
- Ambos dispositivos usan la misma base: `smarthome/{equipoID}/`
- Los tópicos del MKR1000: `/datos`, `/control/led`, `/control/buzzer`, `/alerta`
- Los tópicos del ESP32-CAM: `/camara/evento`, `/camara/control`

## Requisitos No Funcionales

### RNF-1: Estructura de archivos
```
src/
├── mkr1000_firmware/
│   ├── mkr1000_firmware.ino       # setup() + loop() solo — orquestador
│   ├── src/
│   │   ├── config.h               # Constantes, umbrales, pins, equipoID, tópicos
│   │   ├── secrets.h              # WiFi + MQTT creds (en .gitignore)
│   │   ├── secrets.h.example      # Template con valores dummy (commiteado)
│   │   ├── sensor_reader.h        # Struct SensorData, initSensors(), readAllSensors()
│   │   ├── sensor_reader.cpp
│   │   ├── mqtt_manager.h         # initMQTT(), ensureConnected(), publish(), subscribe()
│   │   ├── mqtt_manager.cpp
│   │   ├── alert_system.h         # evaluateAlerts(), setActuatorState()
│   │   ├── alert_system.cpp
│   │   └── message_builder.h      # buildSensorJSON(), buildAlertJSON()
│   │   └── message_builder.cpp
│
├── esp32cam_firmware/
│   ├── esp32cam_firmware.ino      # setup() + loop() — orquestador
│   ├── src/
│   │   ├── config.h               # Pines de cámara, resolución, calidad
│   │   ├── secrets.h              # WiFi creds (en .gitignore)
│   │   ├── secrets.h.example      # Template (commiteado)
│   │   ├── camera_server.h        # initCamera(), startCameraServer()
│   │   ├── camera_server.cpp
│   │   └── mqtt_bridge.h          # initCameraMQTT(), publishCameraEvent()
│   │   └── mqtt_bridge.cpp
```

### RNF-2: `.gitignore`
- Agregar `**/secrets.h` al `.gitignore` del repositorio
- El archivo `secrets.h.example` SÍ se commitea como referencia

### RNF-3: Configuración centralizada
- Todos los umbrales de alerta en `config.h` como `#define`
- Todos los pines en `config.h` como `#define`
- El `EQUIPO_ID` se define UNA vez y se usa via macro concatenación para construir tópicos

### RNF-4: Legibilidad del archivo principal
- `mkr1000_firmware.ino` no debe superar 35 líneas
- `esp32cam_firmware.ino` no debe superar 40 líneas
- `setup()` y `loop()` deben ser legibles como pseudocódigo

### RNF-5: Compatibilidad
- El código debe compilar con Arduino IDE 2.x
- Las librerías usadas deben ser las mismas que ya están en el proyecto (WiFi101, PubSubClient, ArduinoJson, WEMOS_SHT3X)
- El ESP32-CAM debe seguir usando `esp_camera` y `esp_http_server`

## Escenarios de Aceptación

### Escenario 1: MKR1000 publica datos normales
```
DADO que todos los sensores están conectados y funcionando
CUANDO pasan 2 segundos
ENTONCES se publica un JSON válido en `smarthome/equipoXX/datos`
Y el JSON contiene temperatura, humedad, gas, sensor_extra con valores reales
Y NO contiene el campo "alerta"
```

### Escenario 2: MKR1000 detecta condición anómala
```
DADO que el umbral de gas es 400
CUANDO el sensor MQ lee un valor de 500
ENTONCES el JSON publicado contiene "alerta": "Condicion anomala detectada"
Y el LED del pin 6 se enciende
```

### Escenario 3: Sensor falla silenciosamente
```
DADO que el SHT30 desconectado o fallando
CUANDO se leen los sensores
ENTONCES temperatura y humedad son null en el JSON
Y el resto de los sensores se publican normalmente
Y el sistema NO se bloquea
```

### Escenario 4: Control remoto de LED por MQTT
```
DADO que el MKR1000 está conectado al broker
CUANDO se publica "ON" en `smarthome/equipoXX/control/led`
ENTONCES el LED del pin 6 se enciende
```

### Escenario 5: ESP32-CAM publica evento al broker
```
DADO que el ESP32-CAM arrancó y está conectado a WiFi y MQTT
CUANDO el servidor de cámara inicia
ENTONCES se publica un evento en `smarthome/equipoXX/camara/evento`
Y el evento indica que el stream está activo
```

### Escenario 6: Credenciales no commiteadas
```
DADO un repositorio limpio
CUANDO se hace `git add .` y `git commit`
ENTONCES ningún archivo `secrets.h` real es incluido
Y `secrets.h.example` SÍ está disponible como template
```

### Escenario 7: Cambio de equipoID sin bugs
```
DADO que cambio EQUIPO_ID en config.h de "equipoXX" a "equipo05"
CUANDO el firmware compila y arranca
ENTONCES TODOS los tópicos usan "equipo05" (datos, control, camara)
Y no hay ningún tópico hardcodeado con el valor anterior
```

## Criterios de Éxito

1. [ ] El firmware del MKR1000 compila sin errores en Arduino IDE
2. [ ] El firmware del ESP32-CAM compila sin errores en Arduino IDE
3. [ ] `mkr1000_firmware.ino` tiene menos de 35 líneas
4. [ ] `esp32cam_firmware.ino` tiene menos de 40 líneas
5. [ ] `secrets.h` está en `.gitignore`
6. [ ] `secrets.h.example` existe en ambos directorios de firmware
7. [ ] El bug de `equipoXX` hardcodeado está resuelto (un solo punto de definición)
8. [ ] Los umbrales de alerta son constantes en `config.h`
9. [ ] El ESP32-CAM publica al menos un evento MQTT al iniciar
10. [ ] El JSON publicado usa `null` para sensores fallidos (no 0.0)

## Notas de Implementación

- **No cambiar librerías**: usar las mismas que ya funcionan. La modularidad es de estructura, no de dependencias.
- **Arduino .cpp en subcarpeta `src/`**: Arduino IDE 2.x soporta `.cpp` y `.h` en `src/` dentro del directorio del `.ino`. Verificar que compila.
- **ESP32-CAM + MQTT**: la librería `PubSubClient` funciona en ESP32. Usar `WiFi.h` del ESP32 (no WiFi101).
- **No romper lo que funciona**: las pruebas individuales (`prueba_sht30`, `prueba_MQ`, `max4466`) se mantienen como están — son referencias de que los sensores funcionan. No se tocan.
