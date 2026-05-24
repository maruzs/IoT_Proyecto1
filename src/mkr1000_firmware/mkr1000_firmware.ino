#include "src/config.h"
#include "src/secrets.h"
#include "src/sensor_reader.h"
#include "src/mqtt_manager.h"
#include "src/alert_system.h"
#include "src/message_builder.h"
#include <WiFi101.h>

WiFiClient wifiClient;

void setup() {
  Serial.begin(9600);
  initSensors();
  initMQTT(wifiClient, MQTT_SERVER);
  ensureConnected();
}

void loop() {
  ensureConnected();                 // Reconecta al broker si es necesario
  mqttLoop();                        // Procesa mensajes MQTT entrantes
  SensorData data = readAllSensors();
  const char* alert = evaluateAndActuate(data);
  char json[256];
  buildSensorJSON(data, json, sizeof(json), alert);
  publishData(json);
  if (alert != nullptr) {
    publishAlert(alert);
  }
  delay(PUBLISH_INTERVAL_MS);
}
