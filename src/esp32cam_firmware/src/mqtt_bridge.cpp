/**
 * mqtt_bridge.cpp — ESP32-CAM MQTT Implementation
 *
 * Gestiona la conexión MQTT del ESP32-CAM usando PubSubClient.
 * Publica eventos en TOPIC_CAMARA_EVENTO y suscribe a TOPIC_CAMARA_CONTROL.
 */

#include "mqtt_bridge.h"
#include "config.h"

static PubSubClient cameraClient;

void initCameraMQTT(WiFiClient& wifiClient, const char* server) {
    cameraClient.setClient(wifiClient);
    cameraClient.setServer(server, 1883);
}

bool ensureCameraMQTTConnected() {
    if (!cameraClient.connected()) {
        return cameraClient.connect(EQUIPO_ID);
    }
    return true;
}

bool isCameraMQTTConnected() {
    return cameraClient.connected();
}

bool publishCameraEvent(const char* event) {
    if (!cameraClient.connected()) return false;
    char payload[128];
    snprintf(payload, sizeof(payload), "{\"status\":\"%s\"}", event);
    return cameraClient.publish(TOPIC_CAMARA_EVENTO, payload);
}

bool publishToTopic(const char* topic, const char* payload) {
    if (!cameraClient.connected()) return false;
    return cameraClient.publish(topic, payload);
}

void subscribeToCameraControl(void (*callback)(char*, byte*, unsigned int)) {
    cameraClient.setCallback(callback);
    cameraClient.subscribe(TOPIC_CAMARA_CONTROL);
    cameraClient.subscribe(TOPIC_CAMARA_CAPTURA);
}

void mqttLoop() {
    cameraClient.loop();
}
