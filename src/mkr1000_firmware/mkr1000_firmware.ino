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
      int s = WiFi.status();
      Serial.print("\nWiFi TIMEOUT (status="); Serial.print(s); Serial.println(")");
      Serial.print("Retry begin..."); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      wifiStart = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 30000) {
        delay(500); Serial.print(".");
      }
      break;
    }
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK");
    uint32_t lip = WiFi.localIP(), gip = WiFi.gatewayIP();
    Serial.print("IP: ");
    Serial.print((lip >> 24) & 0xFF); Serial.print('.');
    Serial.print((lip >> 16) & 0xFF); Serial.print('.');
    Serial.print((lip >> 8) & 0xFF); Serial.print('.');
    Serial.println(lip & 0xFF);
    Serial.print("GW: ");
    Serial.print((gip >> 24) & 0xFF); Serial.print('.');
    Serial.print((gip >> 16) & 0xFF); Serial.print('.');
    Serial.print((gip >> 8) & 0xFF); Serial.print('.');
    Serial.println(gip & 0xFF);
    Serial.print("MQTT: "); Serial.println(MQTT_SERVER);
    initMQTT(mkrClient, MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
  }
}

void loop() {
  if (!ensureConnected()) { delay(1000); Serial.println("MQTT retry..."); return; }
  mqttLoop();
  checkDoorLedTimeout();
  if (millis() - lastPublishTime >= PUBLISH_INTERVAL_MS) {
    lastPublishTime = millis();
    SensorData data = readAllSensors();
    char jsonBuffer[256];
    buildSensorJSON(data, jsonBuffer, sizeof(jsonBuffer));
    if (publishData(jsonBuffer)) {
      Serial.println(jsonBuffer);
    } else {
      Serial.println("PUB FAIL");
    }
  }
}
