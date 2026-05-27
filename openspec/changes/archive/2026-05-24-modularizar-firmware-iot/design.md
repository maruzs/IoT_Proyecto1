# Design: Modularización Firmware IoT (MKR1000 + ESP32-CAM)

## Technical Approach

Split each monolithic `.ino` into a hexagonal-style structure: the `.ino` becomes a thin orchestrator (`setup()`/`loop()` under 35–40 lines), while sensor reading, MQTT, alerts, message building, and camera streaming live in dedicated `.cpp`/`.h` pairs under `src/`. Arduino IDE 2.x natively resolves `src/` includes, so no build flags are needed.

Two parallel firmware targets share a common MQTT topic hierarchy (`smarthome/{EQUIPO_ID}/…`) but differ in hardware: MKR1000 uses `WiFi101`, ESP32-CAM uses `WiFi.h` + `esp_camera` + `esp_http_server`.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| **Topic building** | C preprocessor string-literal concatenation: `#define TOPIC_DATOS "smarthome/" EQUIPO_ID "/datos"` | `snprintf()` at runtime | Compile-time resolution — zero SRAM cost on 32KB SAM D21; adjacent literals merge in C automatically |
| **Sensor validity model** | `bool` flags per sensor in `SensorData` struct (`sht30_valid`, `mq_valid`, `max_valid`) | NaN sentinels on `float` | `bool` is 1 byte, explicit, debuggable; NaN not portable across Arduino float ABIs |
| **Null JSON for failed sensors** | ArduinoJson `doc["temp"] = (char*)0` or `doc["temp"].set(nullptr)` | Omit the key entirely | Spec requires `null` to distinguish "failed read" from "read returned 0.0" |
| **JSON document size** | `StaticJsonDocument<256>` | Dynamic or 512 bytes | Typical payload with alert field is ~220 bytes; 256B fits with margin. Static avoids heap fragmentation on SAM D21 |
| **ESP32-CAM MQTT loop** | `client.loop()` called from `loop()`, co-existing with FreeRTOS HTTP tasks | Dedicated FreeRTOS task for MQTT | Simpler: FreeRTOS already handles HTTP; MQTT is poll-based and non-blocking in main loop. No task synchronization needed |
| **Secrets isolation** | `#define` macros in `src/secrets.h`, `.gitignore: **/secrets.h`, template in `secrets.h.example` | `EEPROM` or `SPIFFS` config | KISS: compile-time injection; `.gitignore` prevents accidental commit. Templates committed for reference |
| **Alert thresholds** | `#define` in `config.h` | Runtime-configurable via MQTT retention | Phase 1: static constants; future: override topic. Reduces SRAM and complexity |

## Data Flow — MKR1000

```
loop()
  ├─ mqttLoop()              // ensureConnected + client.loop()
  ├─ readAllSensors()        // sensor_reader.cpp → returns SensorData
  │    ├─ sht30.get()        // → sets .sht30_valid, .temp, .hum
  │    ├─ analogRead(pinGas) // → sets .mq_valid (always true for analog), .gas
  │    └─ analogRead(pinSon) // → .max_valid, .sonido
  ├─ buildSensorJSON(data)   // message_builder.cpp → char[] buffer
  │    └─ null fields where !valid
  ├─ mqttPublish(TOPIC_DATOS, buffer)
  ├─ evaluateAndActuate(data)// alert_system.cpp → digitalWrite LED/buzzer
  └─ delay(2000)
```

## Data Flow — ESP32-CAM

```
setup()
  ├─ initCamera()            // camera_server.cpp
  ├─ initWiFi()              // WiFi.h (ESP32 native)
  ├─ initCameraMQTT()        // mqtt_bridge.cpp → PubSubClient connect + subscribe
  ├─ startCameraServer()     // HTTP stream on port 80 (FreeRTOS)
  └─ publishCameraEvent()    // → smarthome/{ID}/camara/evento {"status":"stream_active"}

loop()
  ├─ client.loop()           // MQTT keepalive + process incoming camera commands
  ├─ ── (HTTP served by FreeRTOS, no loop involvement) ──
  └─ delay(10)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/mkr1000_firmware/mkr1000_firmware.ino` | Create | Orchestrator: `setup()` + `loop()` only, ≤35 lines |
| `src/mkr1000_firmware/src/config.h` | Create | Pins, thresholds (`UMBRAL_GAS`, `UMBRAL_TEMP`), `EQUIPO_ID`, topic macros |
| `src/mkr1000_firmware/src/secrets.h.example` | Create | Template with `WIFI_SSID`, `WIFI_PASS`, `MQTT_SERVER` as `#define` |
| `src/mkr1000_firmware/src/sensor_reader.{h,cpp}` | Create | `SensorData` struct, `initSensors()`, `readAllSensors()` |
| `src/mkr1000_firmware/src/mqtt_manager.{h,cpp}` | Create | `initMQTT()`, `ensureConnected()`, `mqttPublish()`, `mqttCallback()` |
| `src/mkr1000_firmware/src/alert_system.{h,cpp}` | Create | `evaluateAndActuate(SensorData)` — LED + buzzer control |
| `src/mkr1000_firmware/src/message_builder.{h,cpp}` | Create | `buildSensorJSON(SensorData, char* buf, size_t len)` — null handling |
| `src/esp32cam_firmware/esp32cam_firmware.ino` | Create | Orchestrator: `setup()` + `loop()`, ≤40 lines |
| `src/esp32cam_firmware/src/config.h` | Create | Camera pins, resolution, JPEG quality, `EQUIPO_ID`, MQTT topic macros |
| `src/esp32cam_firmware/src/secrets.h.example` | Create | Template with `WIFI_SSID`, `WIFI_PASS`, `MQTT_SERVER` |
| `src/esp32cam_firmware/src/camera_server.{h,cpp}` | Create | `initCamera()`, `startCameraServer()` — extracted from current `.ino` |
| `src/esp32cam_firmware/src/mqtt_bridge.{h,cpp}` | Create | `initCameraMQTT()`, `publishCameraEvent()`, camera control callback |
| `src/codigo_base_mkr1000/mkr1000.ino` | **Delete** | Replaced by modular structure |
| `.gitignore` | Create | Add `**/secrets.h` |

## Interfaces / Contracts

**SensorData struct** (sensor_reader.h):
```cpp
struct SensorData {
  float temperatura, humedad;
  bool sht30_valid;
  int gas, sonido;
  bool mq_valid, max_valid;
};
```

**Topic macro pattern** (config.h):
```cpp
#define EQUIPO_ID "equipo05"
#define TOPIC_BASE    "smarthome/" EQUIPO_ID
#define TOPIC_DATOS   TOPIC_BASE "/datos"
#define TOPIC_LED     TOPIC_BASE "/control/led"
#define TOPIC_BUZZER  TOPIC_BASE "/control/buzzer"
#define TOPIC_ALERTA  TOPIC_BASE "/alerta"
```

**Null JSON handling** (message_builder.cpp):
```cpp
// ArduinoJson 6.x: cast to (char*)0 produces JSON null
tempData.sht30_valid
  ? doc["temperatura"] = tempData.temperatura
  : doc["temperatura"] = (char*)0;
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Compile | Both `.ino` targets | Manual Arduino IDE 2.x compile check (no CLI available) |
| Unit (static) | Topic macro expansion, struct field count | Visual verification of macro output via `Serial.println(TOPIC_DATOS)` |
| Integration | MQTT publish/subscribe round-trip | Flash to real hardware, verify with MQTT Explorer / Node-RED |
| Acceptance | All 7 scenarios from spec | Manual execution against real broker |

No automated test framework exists for Arduino firmware; all verification is manual/hardware-in-the-loop.

## Migration / Rollout

No data migration required. The existing `codigo_base_mkr1000/` is preserved for reference during the transition. Rollback: restore old `.ino` from git history.

## Open Questions

- None. All decisions are resolved at design time.
