/**
 * mqtt_bridge.h — ESP32-CAM MQTT Integration
 *
 * Declara funciones para conectar el ESP32-CAM al broker MQTT,
 * publicar eventos de cámara y suscribirse a comandos de control.
 */

#ifndef MQTT_BRIDGE_H
#define MQTT_BRIDGE_H

// DEBE definirse antes de incluir PubSubClient
// uint16_t bufferSize: max 65535. Usamos 60000 (suficiente para JPEGs de ~30KB)
#ifndef MQTT_MAX_PACKET_SIZE
#define MQTT_MAX_PACKET_SIZE 60000
#endif

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

void initCameraMQTT(WiFiClientSecure& client, const char* server,
                    uint16_t port, const char* username,
                    const char* password, const char* caCert);
bool ensureCameraMQTTConnected();
bool isCameraMQTTConnected();
bool publishCameraEvent(const char* event);
bool publishToTopic(const char* topic, const char* payload);
bool publishCameraImage(const uint8_t* data, size_t len);
void subscribeToCameraControl(void (*callback)(char*, byte*, unsigned int));
void mqttLoop();

#endif
