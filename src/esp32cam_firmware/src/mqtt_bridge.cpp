/**
 * mqtt_bridge.cpp — ESP32-CAM MQTT Implementation
 *
 * Gestiona la conexión MQTT del ESP32-CAM usando PubSubClient.
 * Publica eventos e imágenes. Suscribe solo a TOPIC_CAMARA_CAPTURA.
 */

// MQTT_MAX_PACKET_SIZE must be BEFORE ANY PubSubClient include
#define MQTT_MAX_PACKET_SIZE 65536
#include "mqtt_bridge.h"
#include "config.h"

static PubSubClient cameraClient;

void initCameraMQTT(WiFiClient& wifiClient, const char* server) {
    cameraClient.setClient(wifiClient);
    cameraClient.setServer(server, 1883);
    cameraClient.setBufferSize(60000);  // Necesario para imágenes JPEG (~15-30 KB)
}

bool ensureCameraMQTTConnected() {
    if (!cameraClient.connected()) {
        if (!cameraClient.connect(EQUIPO_ID "-cam")) return false;
        // Re-suscribir después de reconexión
        cameraClient.subscribe(TOPIC_CAMARA_CAPTURA);
        Serial.println("MQTT reconectado + resuscrito");
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

bool publishCameraImage(const uint8_t* data, size_t len) {
    if (!cameraClient.connected()) {
        Serial.println("MQTT desconectado al publicar imagen");
        return false;
    }
    if (!cameraClient.publish(TOPIC_CAMARA_IMAGEN, data, len)) {
        Serial.print("publish() falló. Imagen: "); Serial.print(len);
        Serial.print(" bytes. Buffer size: "); Serial.println(cameraClient.getBufferSize());
        return false;
    }
    return true;
}

void subscribeToCameraControl(void (*callback)(char*, byte*, unsigned int)) {
    cameraClient.setCallback(callback);
    cameraClient.subscribe(TOPIC_CAMARA_CAPTURA);
}

void mqttLoop() {
    cameraClient.loop();
}
