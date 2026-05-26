# Tasks: Modularización Firmware IoT (MKR1000 + ESP32-CAM)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~700–900 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation → PR 2: MKR1000 → PR 3: ESP32-CAM |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation: `.gitignore`, `config.h` + `secrets.h.example` for both firmwares | PR 1 | Base branch: feature/tracker. Tests: verify git status. |
| 2 | MKR1000: `sensor_reader`, `mqtt_manager`, `message_builder`, `alert_system`, `.ino` | PR 2 | Base: PR 1 branch. Tests: compile-check + topic expansion. |
| 3 | ESP32-CAM: `camera_server`, `mqtt_bridge`, `.ino` + delete old `codigo_base_mkr1000/mkr1000.ino` | PR 3 | Base: PR 2 branch. Tests: compile-check + MQTT event. |

## Phase 1: Foundation / Infrastructure

- [x] 1.1 Create `.gitignore` with `**/secrets.h`
- [x] 1.2 Create `src/mkr1000_firmware/src/config.h` — pins, thresholds, EQUIPO_ID, topic macros
- [x] 1.3 Create `src/mkr1000_firmware/src/secrets.h.example` — WiFi/MQTT template
- [x] 1.4 Create `src/esp32cam_firmware/src/config.h` — camera pins, resolution, EQUIPO_ID, topics
- [x] 1.5 Create `src/esp32cam_firmware/src/secrets.h.example` — WiFi template

## Phase 2: MKR1000 Core Modules

- [x] 2.1 Create `src/mkr1000_firmware/src/sensor_reader.h` — `SensorData` struct + declarations
- [x] 2.2 Create `src/mkr1000_firmware/src/sensor_reader.cpp` — `initSensors()`, `readAllSensors()`
- [x] 2.3 Create `src/mkr1000_firmware/src/mqtt_manager.h` — function declarations
- [x] 2.4 Create `src/mkr1000_firmware/src/mqtt_manager.cpp` — `initMQTT()`, `ensureConnected()`, `mqttPublish()`, callback
- [x] 2.5 Create `src/mkr1000_firmware/src/message_builder.h` — declarations
- [x] 2.6 Create `src/mkr1000_firmware/src/message_builder.cpp` — `buildSensorJSON()` with null handling per ArduinoJson 6.x
- [x] 2.7 Create `src/mkr1000_firmware/src/alert_system.h` — declarations
- [x] 2.8 Create `src/mkr1000_firmware/src/alert_system.cpp` — `evaluateAndActuate()` with threshold checks

## Phase 3: MKR1000 Wiring

- [x] 3.1 Create `src/mkr1000_firmware/mkr1000_firmware.ino` — `setup()` + `loop()` only, ≤35 lines
- [x] 3.2 Verify MKR1000 firmware compiles in Arduino IDE 2.x

## Phase 4: ESP32-CAM Modules + Wiring

- [x] 4.1 Create `src/esp32cam_firmware/src/camera_server.h` — declarations
- [x] 4.2 Create `src/esp32cam_firmware/src/camera_server.cpp` — `initCamera()`, `startCameraServer()`
- [x] 4.3 Create `src/esp32cam_firmware/src/mqtt_bridge.h` — declarations
- [x] 4.4 Create `src/esp32cam_firmware/src/mqtt_bridge.cpp` — `initCameraMQTT()`, `publishCameraEvent()`, control callback
- [x] 4.5 Create `src/esp32cam_firmware/esp32cam_firmware.ino` — `setup()` + `loop()`, ≤40 lines

## Phase 5: Cleanup

- [x] 5.1 Delete `src/codigo_base_mkr1000/mkr1000.ino`
- [x] 5.2 Verify both firmwares compile in Arduino IDE 2.x
