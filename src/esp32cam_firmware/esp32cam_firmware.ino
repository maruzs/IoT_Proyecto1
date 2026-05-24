#include "src/config.h"
#include "src/secrets.h"
#include "src/camera_server.h"
#include "src/mqtt_bridge.h"
#include <WiFi.h>

WiFiClient wifiClient;

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char msg[32] = {0};
    unsigned int n = length < 31 ? length : 31;
    memcpy(msg, payload, n);
    msg[n] = '\0';
    Serial.print("CMD: "); Serial.println(msg);
}

void setup() {
    Serial.begin(115200);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi OK");
    if (!initCamera()) { Serial.println("Camara fallo"); return; }
    startCameraServer();
    initCameraMQTT(wifiClient, MQTT_SERVER);
    ensureCameraMQTTConnected();
    subscribeToCameraControl(mqttCallback);
    publishCameraEvent("stream_started");
}

void loop() {
    if (!isCameraMQTTConnected()) ensureCameraMQTTConnected();
    mqttLoop();
    delay(MQTT_LOOP_DELAY_MS);
}
