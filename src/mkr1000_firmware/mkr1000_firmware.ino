#include "src/config.h"
#include "src/secrets.h"
#include "src/sensor_reader.h"
#include "src/mqtt_manager.h"
#include "src/message_builder.h"
#include <WiFi101.h>

WiFiClient wifiClient;
unsigned long lastPublishTime = 0;

void setup() {
  Serial.begin(9600);
  initSensors();
  initActuators();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
  initMQTT(wifiClient, MQTT_SERVER);
}

void loop() {
  if (!ensureConnected()) { delay(1000); return; }
  mqttLoop();
  checkDoorLedTimeout();
  if (millis() - lastPublishTime >= PUBLISH_INTERVAL_MS) {
    lastPublishTime = millis();
    SensorData data = readAllSensors();
    char jsonBuffer[256];
    buildSensorJSON(data, jsonBuffer, sizeof(jsonBuffer));
    if (publishData(jsonBuffer)) {
      Serial.println(jsonBuffer);
    }
  }
}
