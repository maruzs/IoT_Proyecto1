// MQTT_MAX_PACKET_SIZE debe definirse antes que cualquier include de PubSubClient
#define MQTT_MAX_PACKET_SIZE 65536
#include "src/config.h"
#include "src/secrets.h"
#include "src/camera_server.h"
#include "src/mqtt_bridge.h"
#include "src/burst_capture.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include "Arduino.h"

WiFiClientSecure secureClient;

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char msg[128] = {0};
    unsigned int n = length < 127 ? length : 127;
    memcpy(msg, payload, n);
    msg[n] = '\0';
    Serial.print("CMD: "); Serial.println(msg);

    if (strcmp(topic, TOPIC_CAMARA_CAPTURA) == 0) {
        handleBurstCommand(msg);
    }
}

void setup() {
    Serial.begin(115200);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi OK");
    Serial.print("Camara lista! IP: http://");
    Serial.println(WiFi.localIP());
    if (!initCamera()) { Serial.println("Camara fallo"); return; }
    // Modo snapshot: sin stream MJPEG. Imágenes solo bajo demanda vía MQTT.
    delay(500);  // Pequeña pausa post-WiFi para estabilizar
    initCameraMQTT(secureClient, MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, CA_CERT);
    Serial.print("Conectando MQTT a "); Serial.print(MQTT_SERVER); Serial.print("... ");
    if (ensureCameraMQTTConnected()) {
        Serial.println("OK");
    } else {
        Serial.println("FALLO");
    }
    subscribeToCameraControl(mqttCallback);
    publishCameraEvent("camara_lista");
}

void loop() {
    if (!isCameraMQTTConnected()) ensureCameraMQTTConnected();
    mqttLoop();
    checkBurstTimeout();
    delay(MQTT_LOOP_DELAY_MS);
}
