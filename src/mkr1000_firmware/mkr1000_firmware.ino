#include "src/config.h"
#include "src/sensor_reader.h"
#include "src/presence_sensor.h"
#include "src/mqtt_manager.h"
#include "src/alert_system.h"
#include "src/message_builder.h"
#include "src/secrets.h"
#include <WiFi101.h>
#include <Arduino.h>

static WiFiClient wifiClient;
static bool lastPresenceState = false;

void setup() {
  Serial.begin(9600);
  while (!Serial) { }
  initSensors();
  initActuators();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  initMQTT(wifiClient, MQTT_SERVER);
  Serial.println("MKR1000 ready");
}

void loop() {
  SensorData data = readAllSensors();
  const char* alert = evaluateAndActuate(data);
  if (ensureConnected()) {
    char buf[256];
    buildSensorJSON(data, buf, sizeof(buf), alert);
    publishData(buf);
    if (alert) publishAlert(alert);
    bool presence = readPresence();
    if (presence != lastPresenceState) {
      publishPresence(presence ? 1 : 0);
      lastPresenceState = presence;
    }
  }
  mqttLoop();
  delay(PUBLISH_INTERVAL_MS);
}
