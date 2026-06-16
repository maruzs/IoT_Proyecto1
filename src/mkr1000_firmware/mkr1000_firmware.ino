#include "src/config.h"
#include "src/secrets.h"
#include "src/sensor_reader.h"
#include "src/mqtt_manager.h"
#include "src/message_builder.h"
#include <WiFi101.h>
#include <WiFiClient.h>

WiFiClient mkrClient;
unsigned long lastPublishTime = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial) delay(10);
  Serial.println("MKR1000 boot");

  initSensors();
  initActuators();

  Serial.print("WiFi: "); Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (millis() - wifiStart > 15000) {
      Serial.println("\nWiFi TIMEOUT");
      break;
    }
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK");
    // NTP no necesario: MKR1000 usa puerto 1884 non-TLS
    Serial.print("MQTT: "); Serial.println(MQTT_SERVER);
    initMQTT(mkrClient, MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
  }
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
